from fastapi import FastAPI, APIRouter, HTTPException, Depends, UploadFile, File, Form, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import StreamingResponse
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict, EmailStr
from typing import List, Optional
import uuid
from datetime import datetime, timezone, timedelta
import bcrypt
import jwt
from emergentintegrations.llm.chat import LlmChat, UserMessage, ImageContent
import io
from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, PatternFill
import json

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection - lazy initialization for production reliability
mongo_url = os.environ.get('MONGO_URL', 'mongodb://localhost:27017')
db_name = os.environ.get('DB_NAME', 'test_database')

# Initialize client with appropriate timeouts for production
# Motor/PyMongo connects lazily - actual connection happens on first operation
client = AsyncIOMotorClient(
    mongo_url,
    serverSelectionTimeoutMS=10000,  # 10 second timeout for server selection
    connectTimeoutMS=10000,          # 10 second connection timeout
    socketTimeoutMS=30000,           # 30 second socket timeout
    maxPoolSize=10,                  # Connection pool size
    retryWrites=True                 # Enable retry for write operations
)
db = client[db_name]

# JWT Config
JWT_SECRET = os.environ.get('JWT_SECRET', 'fatura-yonetim-secret-key-2024')
JWT_ALGORITHM = 'HS256'

# Admin Config
ADMIN_SECRET_KEY = os.environ.get('ADMIN_SECRET_KEY', 'imeridis-2025')

# Emergent LLM Key
EMERGENT_LLM_KEY = os.environ.get('EMERGENT_LLM_KEY', '')

app = FastAPI()
api_router = APIRouter(prefix="/api")
security = HTTPBearer()

# Models
class UserRegister(BaseModel):
    email: EmailStr
    password: str
    full_name: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class User(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    email: str
    full_name: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class TaxpayerSession(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    taxpayer_name: str
    year: int
    month: int
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class TaxpayerSessionCreate(BaseModel):
    taxpayer_name: str
    year: int
    month: int

# Subscription Plans - Limits represent TOTAL quota for 12 months (not monthly)
SUBSCRIPTION_PLANS = {
    "trial": {"name": "Deneme", "monthly_limit": 20, "price": 0},  # 20 total, 7 days
    "starter": {"name": "Başlangıç", "monthly_limit": 1000, "price": 699},  # 1000 total for 12 months
    "professional": {"name": "Profesyonel", "monthly_limit": 2500, "price": 1399},  # 2500 total for 12 months
    "business": {"name": "İşletme", "monthly_limit": 5000, "price": 2399},  # 5000 total for 12 months
    "enterprise": {"name": "Kurumsal", "monthly_limit": 10000, "price": 3999},  # 10000 total for 12 months
    "unlimited": {"name": "Sınırsız", "monthly_limit": -1, "price": -1},  # -1 = unlimited/contact
}

# Package model for multiple subscriptions per user
class UserPackage(BaseModel):
    """Represents a single package/subscription for a user"""
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    plan: str  # starter, professional, business, enterprise, unlimited
    plan_name: str  # Display name
    total_quota: int  # Total quota for this package
    used_quota: int = 0  # Used quota for this package
    start_date: str  # ISO format
    end_date: str  # ISO format
    is_active: bool = True
    wix_order_id: Optional[str] = None  # Wix order reference
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

class UserSubscription(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str  # visitor_id or wix_member_id
    wix_member_id: Optional[str] = None
    plan: str = "trial"  # trial, starter, professional, business, enterprise, unlimited
    monthly_uploads: int = 0
    month_reset: str = ""  # YYYY-MM format to track when to reset
    trial_used: bool = False
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

# KDV Detail model for VAT breakdown
class VatDetail(BaseModel):
    model_config = ConfigDict(extra="ignore")
    vat_rate: float  # 1, 10, 20
    base_amount: float  # Matrah
    vat_amount: float  # KDV tutarı
    withholding: bool = False  # Tevkifat var mı
    withholding_rate: Optional[float] = None  # Tevkifat oranı (örn: 5/10, 9/10)

class Invoice(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    session_id: Optional[str] = ""  # Reference to taxpayer session
    category: str  # "income" or "expense"
    invoice_number: str
    date: str
    issuer_name: str
    issuer_tax_id: str
    issuer_tax_office: str
    customer_name: str
    customer_tax_id: str
    customer_tax_office: str
    description: str
    amount: float
    vat: float
    total: float
    file_name: str
    file_type: str
    # KDV detayları
    vat_details: Optional[List[dict]] = []  # List of VatDetail dicts
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class InvoiceCreate(BaseModel):
    category: str
    invoice_number: str
    date: str
    issuer_name: str
    issuer_tax_id: str
    issuer_tax_office: str
    customer_name: str
    customer_tax_id: str
    customer_tax_office: str
    description: str
    amount: float
    vat: float
    total: float

class InvoiceUpdate(BaseModel):
    category: Optional[str] = None
    invoice_number: Optional[str] = None
    date: Optional[str] = None
    issuer_name: Optional[str] = None
    issuer_tax_id: Optional[str] = None
    issuer_tax_office: Optional[str] = None
    customer_name: Optional[str] = None
    customer_tax_id: Optional[str] = None
    customer_tax_office: Optional[str] = None
    description: Optional[str] = None
    amount: Optional[float] = None
    vat: Optional[float] = None
    total: Optional[float] = None

# Helper Functions
def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))

def create_token(user_id: str, email: str) -> str:
    payload = {
        'user_id': user_id,
        'email': email,
        'exp': datetime.now(timezone.utc) + timedelta(days=7)
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

# Subscription Helper Functions
async def get_or_create_subscription(user_id: str, wix_member_id: str = None):
    """Get existing subscription or create trial"""
    query = {"user_id": user_id}
    if wix_member_id:
        query = {"$or": [{"user_id": user_id}, {"wix_member_id": wix_member_id}]}
    
    sub = await db.subscriptions.find_one(query, {"_id": 0})
    
    if not sub:
        # Create new trial subscription with 7 days expiry
        trial_expires = (datetime.now(timezone.utc) + timedelta(days=7)).isoformat()
        sub = {
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "wix_member_id": wix_member_id,
            "plan": "trial",
            "monthly_uploads": 0,
            "trial_used": False,
            "expires_at": trial_expires,
            "packages": [],  # New: list of packages
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
        await db.subscriptions.insert_one(sub)
    
    # No monthly reset for any plan - quotas are total for the subscription period
    return sub

async def get_user_packages(wix_member_id: str):
    """Get all packages for a user"""
    sub = await db.subscriptions.find_one({"wix_member_id": wix_member_id}, {"_id": 0})
    if not sub:
        return []
    return sub.get("packages", [])

async def add_package_to_user(wix_member_id: str, plan: str, wix_order_id: str = None):
    """Add a new package to user's subscription"""
    plan_info = SUBSCRIPTION_PLANS.get(plan)
    if not plan_info:
        return None
    
    now = datetime.now(timezone.utc)
    
    # Determine duration based on plan type
    if plan == "trial":
        end_date = now + timedelta(days=7)
    else:
        end_date = now + timedelta(days=365)  # 12 months
    
    new_package = {
        "id": str(uuid.uuid4()),
        "plan": plan,
        "plan_name": plan_info["name"],
        "total_quota": plan_info["monthly_limit"],
        "used_quota": 0,
        "start_date": now.isoformat(),
        "end_date": end_date.isoformat(),
        "is_active": True,
        "wix_order_id": wix_order_id,
        "created_at": now.isoformat()
    }
    
    # Add package to user's packages array
    result = await db.subscriptions.update_one(
        {"wix_member_id": wix_member_id},
        {
            "$push": {"packages": new_package},
            "$set": {
                "updated_at": now.isoformat(),
                "had_paid_plan": True if plan != "trial" else False
            }
        }
    )
    
    return new_package if result.modified_count > 0 else None

async def get_active_packages(wix_member_id: str):
    """Get all active (not expired, has quota) packages for a user, sorted by end_date (oldest first)"""
    sub = await db.subscriptions.find_one({"wix_member_id": wix_member_id}, {"_id": 0})
    if not sub:
        return []
    
    packages = sub.get("packages", [])
    now = datetime.now(timezone.utc)
    
    active_packages = []
    for pkg in packages:
        if not pkg.get("is_active", True):
            continue
        
        # Check expiry
        end_date_str = pkg.get("end_date")
        if end_date_str:
            try:
                end_date = datetime.fromisoformat(end_date_str.replace('Z', '+00:00'))
                if now > end_date:
                    continue  # Expired
            except:
                pass
        
        # Check quota (skip unlimited plans for quota check)
        total = pkg.get("total_quota", 0)
        used = pkg.get("used_quota", 0)
        if total != -1 and used >= total:
            continue  # Quota exhausted
        
        active_packages.append(pkg)
    
    # Sort by end_date (oldest first) to use older packages first
    active_packages.sort(key=lambda x: x.get("end_date", ""))
    
    return active_packages

async def calculate_total_remaining_quota(wix_member_id: str):
    """Calculate total remaining quota across all active packages"""
    active_packages = await get_active_packages(wix_member_id)
    
    total_remaining = 0
    has_unlimited = False
    
    for pkg in active_packages:
        total = pkg.get("total_quota", 0)
        used = pkg.get("used_quota", 0)
        
        if total == -1:
            has_unlimited = True
        else:
            total_remaining += (total - used)
    
    return -1 if has_unlimited else total_remaining

async def use_quota_from_packages(wix_member_id: str, count: int = 1):
    """Use quota from user's packages (oldest active package first)"""
    active_packages = await get_active_packages(wix_member_id)
    
    if not active_packages:
        return False, "Aktif paketiniz bulunmuyor."
    
    remaining_to_use = count
    updates = []
    
    for pkg in active_packages:
        if remaining_to_use <= 0:
            break
        
        total = pkg.get("total_quota", 0)
        used = pkg.get("used_quota", 0)
        
        # Unlimited package
        if total == -1:
            return True, None
        
        available = total - used
        use_from_this = min(available, remaining_to_use)
        
        if use_from_this > 0:
            updates.append({
                "package_id": pkg["id"],
                "new_used": used + use_from_this
            })
            remaining_to_use -= use_from_this
    
    if remaining_to_use > 0:
        return False, f"Yetersiz kota. Gerekli: {count}, Mevcut: {count - remaining_to_use}"
    
    # Apply updates to packages
    for update in updates:
        await db.subscriptions.update_one(
            {"wix_member_id": wix_member_id, "packages.id": update["package_id"]},
            {"$set": {"packages.$.used_quota": update["new_used"]}}
        )
    
    return True, None

async def check_upload_limit(user_id: str, file_count: int = 1):
    """Check if user can upload more files. Returns (can_upload, message, remaining)"""
    sub = await get_or_create_subscription(user_id)
    wix_member_id = sub.get("wix_member_id")
    
    # Check for multi-package system first (if user has packages)
    packages = sub.get("packages", [])
    if packages and wix_member_id:
        active_packages = await get_active_packages(wix_member_id)
        
        if not active_packages:
            # No active packages - check legacy single plan
            pass
        else:
            # Use multi-package system
            total_remaining = await calculate_total_remaining_quota(wix_member_id)
            
            if total_remaining == -1:  # Unlimited
                return True, None, -1
            
            if total_remaining <= 0:
                return False, "Fatura kotanız doldu. Devam etmek için yeni bir plan satın alın.", 0
            
            if file_count > total_remaining:
                return False, f"Kota yetersiz. Kalan: {total_remaining}, İstenen: {file_count}", total_remaining
            
            return True, None, total_remaining - file_count
    
    # Legacy single plan system
    plan = sub.get("plan", "trial")
    plan_info = SUBSCRIPTION_PLANS.get(plan, SUBSCRIPTION_PLANS["trial"])
    limit = plan_info["monthly_limit"]  # Now represents total limit for 12 months
    current = sub.get("monthly_uploads", 0)
    
    # Check if subscription expired
    expires_at = sub.get("expires_at")
    if expires_at:
        try:
            exp_date = datetime.fromisoformat(expires_at.replace('Z', '+00:00'))
            if datetime.now(timezone.utc) > exp_date:
                if plan == "trial":
                    return False, "Deneme süreniz doldu. Devam etmek için bir plan satın alın.", 0
                else:
                    return False, "Abonelik süreniz doldu. Devam etmek için yeni bir plan satın alın.", 0
        except:
            pass
    
    # Check if user had paid plan before and now downgraded to trial
    # If they ever had a paid plan, they can't use trial anymore
    if plan == "trial" and sub.get("had_paid_plan", False):
        return False, "Üyeliğiniz sona erdi. Devam etmek için bir plan satın alın.", 0
    
    # Unlimited plan
    if limit == -1:
        return True, None, -1
    
    # Check quota (same logic for trial and paid plans - total quota, no monthly reset)
    remaining = limit - current
    if current >= limit:
        if plan == "trial":
            return False, "Deneme hakkınız doldu. Devam etmek için bir plan satın alın.", 0
        else:
            return False, "Fatura kotanız doldu. Devam etmek için yeni bir plan satın alın.", 0
    if current + file_count > limit:
        return False, f"Kota yetersiz. Kalan: {remaining}, İstenen: {file_count}", remaining
    
    return True, None, remaining - file_count

async def increment_upload_count(user_id: str, count: int = 1):
    """Increment the upload counter - supports both legacy and multi-package systems"""
    sub = await get_or_create_subscription(user_id)
    wix_member_id = sub.get("wix_member_id")
    packages = sub.get("packages", [])
    
    # Use multi-package system if available
    if packages and wix_member_id:
        active_packages = await get_active_packages(wix_member_id)
        if active_packages:
            success, msg = await use_quota_from_packages(wix_member_id, count)
            return success
    
    # Legacy single plan system
    new_count = sub.get("monthly_uploads", 0) + count
    
    update_data = {
        "monthly_uploads": new_count,
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
    
    # Mark trial as used if it's trial plan
    if sub.get("plan") == "trial":
        update_data["trial_used"] = True
    
    # Update by wix_member_id if exists, otherwise by user_id
    if wix_member_id:
        await db.subscriptions.update_one(
            {"wix_member_id": wix_member_id},
            {"$set": update_data}
        )
    else:
        await db.subscriptions.update_one(
            {"user_id": user_id},
            {"$set": update_data}
        )
    
    return True

async def get_current_user(
    x_visitor_id: Optional[str] = Header(None),
    x_wix_member_id: Optional[str] = Header(None),
    x_wix_plan: Optional[str] = Header(None),
    x_wix_expires: Optional[str] = Header(None)
):
    """Get user identifier - prefer Wix Member ID if available"""
    # If Wix Member ID is provided, sync subscription from Wix
    if x_wix_member_id:
        existing_sub = await db.subscriptions.find_one({"wix_member_id": x_wix_member_id}, {"_id": 0})
        
        # Map Wix plan to our plan
        plan_mapping = {
            "trial": "trial",
            "starter": "starter", 
            "professional": "professional",
            "business": "business",
            "enterprise": "enterprise",
            "unlimited": "unlimited"
        }
        
        new_plan = plan_mapping.get(x_wix_plan, None) if x_wix_plan else None
        
        if existing_sub:
            user_id = existing_sub.get("user_id", x_visitor_id)
            old_plan = existing_sub.get("plan")
            
            # ALWAYS update plan from Wix (Wix is the source of truth)
            if new_plan:
                update_data = {
                    "plan": new_plan,
                    "updated_at": datetime.now(timezone.utc).isoformat()
                }
                
                # For trial plan, set expiry from Wix (7 days)
                if new_plan == "trial":
                    if x_wix_expires:
                        update_data["expires_at"] = x_wix_expires
                    elif not existing_sub.get("expires_at"):
                        update_data["expires_at"] = (datetime.now(timezone.utc) + timedelta(days=7)).isoformat()
                # For paid plans: 12 months validity, total quota (no monthly reset)
                else:
                    # Mark that user had a paid plan (can't go back to trial)
                    update_data["had_paid_plan"] = True
                    
                    # Only set new expiry and reset quota if plan changed from different plan
                    # This means user purchased a new package
                    if old_plan != new_plan:
                        # New plan purchased - set 12 month expiry and reset quota
                        update_data["expires_at"] = (datetime.now(timezone.utc) + timedelta(days=365)).isoformat()
                        update_data["monthly_uploads"] = 0  # Reset usage for new plan
                        update_data["plan_start_date"] = datetime.now(timezone.utc).isoformat()
                    # If same plan, keep existing expiry (don't reset)
                
                await db.subscriptions.update_one(
                    {"wix_member_id": x_wix_member_id},
                    {"$set": update_data}
                )
            
            return user_id
        else:
            # Create new subscription for this Wix member (use upsert to prevent duplicates)
            user_id = f"wix_{x_wix_member_id}"
            
            # Determine expiry
            if new_plan == "trial" and x_wix_expires:
                expires_at = x_wix_expires
            elif new_plan == "trial" or not new_plan:
                expires_at = (datetime.now(timezone.utc) + timedelta(days=7)).isoformat()
            else:
                # Paid plans: 12 months validity
                expires_at = (datetime.now(timezone.utc) + timedelta(days=365)).isoformat()
            
            new_sub = {
                "id": str(uuid.uuid4()),
                "user_id": user_id,
                "wix_member_id": x_wix_member_id,
                "plan": new_plan or "trial",
                "monthly_uploads": 0,
                "trial_used": False,
                "had_paid_plan": new_plan and new_plan != "trial",  # Mark if starting with paid plan
                "expires_at": expires_at,
                "plan_start_date": datetime.now(timezone.utc).isoformat() if new_plan and new_plan != "trial" else None,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat()
            }
            # Use upsert to prevent duplicate entries
            await db.subscriptions.update_one(
                {"wix_member_id": x_wix_member_id},
                {"$setOnInsert": new_sub},
                upsert=True
            )
            return user_id
    
    if x_visitor_id:
        return x_visitor_id
    return "anonymous-user"
    
async def get_current_user_old(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        token = credentials.credentials
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        user_id = payload.get('user_id')
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token")
        return user_id
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

# Auth Routes
@api_router.post("/auth/register")
async def register(user_data: UserRegister):
    existing_user = await db.users.find_one({"email": user_data.email}, {"_id": 0})
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    user = User(
        email=user_data.email,
        full_name=user_data.full_name
    )
    
    user_dict = user.model_dump()
    user_dict['password'] = hash_password(user_data.password)
    user_dict['created_at'] = user_dict['created_at'].isoformat()
    
    await db.users.insert_one(user_dict)
    
    token = create_token(user.id, user.email)
    return {"token": token, "user": user}

@api_router.post("/auth/login")
async def login(login_data: UserLogin):
    user_dict = await db.users.find_one({"email": login_data.email}, {"_id": 0})
    if not user_dict:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    if not verify_password(login_data.password, user_dict['password']):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    user = User(**{k: v for k, v in user_dict.items() if k != 'password'})
    if isinstance(user.created_at, str):
        user.created_at = datetime.fromisoformat(user.created_at)
    
    token = create_token(user.id, user.email)
    return {"token": token, "user": user}

@api_router.get("/auth/me", response_model=User)
async def get_me(user_id: str = Depends(get_current_user)):
    user_dict = await db.users.find_one({"id": user_id}, {"_id": 0, "password": 0})
    if not user_dict:
        raise HTTPException(status_code=404, detail="User not found")
    
    if isinstance(user_dict['created_at'], str):
        user_dict['created_at'] = datetime.fromisoformat(user_dict['created_at'])
    
    return User(**user_dict)

# Taxpayer Session Routes
@api_router.post("/sessions")
async def create_session(session_data: TaxpayerSessionCreate, user_id: str = Depends(get_current_user)):
    # Delete any existing session for this user
    await db.taxpayer_sessions.delete_many({"user_id": user_id})
    # Also delete all invoices for this user (new session = fresh start)
    await db.invoices.delete_many({"user_id": user_id})
    
    session = TaxpayerSession(
        user_id=user_id,
        taxpayer_name=session_data.taxpayer_name,
        year=session_data.year,
        month=session_data.month
    )
    
    session_dict = session.model_dump()
    session_dict['created_at'] = session_dict['created_at'].isoformat()
    
    await db.taxpayer_sessions.insert_one(session_dict)
    return session

@api_router.get("/sessions/current")
async def get_current_session(user_id: str = Depends(get_current_user)):
    session = await db.taxpayer_sessions.find_one({"user_id": user_id}, {"_id": 0})
    if not session:
        return None
    return session

@api_router.delete("/sessions")
async def delete_session(user_id: str = Depends(get_current_user)):
    await db.taxpayer_sessions.delete_many({"user_id": user_id})
    await db.invoices.delete_many({"user_id": user_id})
    return {"message": "Session and invoices deleted"}

# Subscription API Routes
@api_router.get("/subscription/plans")
async def get_subscription_plans():
    """Get all available subscription plans"""
    plans = []
    for plan_id, plan_data in SUBSCRIPTION_PLANS.items():
        plans.append({
            "id": plan_id,
            "name": plan_data["name"],
            "monthly_limit": plan_data["monthly_limit"],
            "price": plan_data["price"],
            "is_contact": plan_id == "unlimited"
        })
    return {"plans": plans}

@api_router.get("/subscription/status")
async def get_subscription_status(user_id: str = Depends(get_current_user)):
    """Get current user's subscription status and remaining quota"""
    sub = await get_or_create_subscription(user_id)
    wix_member_id = sub.get("wix_member_id")
    packages = sub.get("packages", [])
    
    # Check for multi-package system
    if packages and wix_member_id:
        active_packages = await get_active_packages(wix_member_id)
        
        if active_packages:
            # Multi-package system
            total_remaining = await calculate_total_remaining_quota(wix_member_id)
            
            # Format packages for frontend
            packages_info = []
            now = datetime.now(timezone.utc)
            
            for pkg in packages:
                pkg_total = pkg.get("total_quota", 0)
                pkg_used = pkg.get("used_quota", 0)
                pkg_remaining = -1 if pkg_total == -1 else max(0, pkg_total - pkg_used)
                
                # Check if expired
                end_date_str = pkg.get("end_date")
                pkg_expired = False
                pkg_days_remaining = None
                if end_date_str:
                    try:
                        end_date = datetime.fromisoformat(end_date_str.replace('Z', '+00:00'))
                        pkg_expired = now > end_date
                        if not pkg_expired:
                            pkg_days_remaining = (end_date - now).days
                    except:
                        pass
                
                packages_info.append({
                    "id": pkg.get("id"),
                    "plan": pkg.get("plan"),
                    "plan_name": pkg.get("plan_name"),
                    "total_quota": pkg_total,
                    "used_quota": pkg_used,
                    "remaining_quota": pkg_remaining,
                    "start_date": pkg.get("start_date"),
                    "end_date": pkg.get("end_date"),
                    "is_expired": pkg_expired,
                    "is_exhausted": pkg_remaining == 0 and pkg_total != -1,
                    "days_remaining": pkg_days_remaining,
                    "is_active": not pkg_expired and (pkg_remaining > 0 or pkg_total == -1)
                })
            
            # Get the primary active package (first non-expired with quota)
            primary_pkg = active_packages[0] if active_packages else packages[0]
            
            return {
                "has_multi_packages": True,
                "packages": packages_info,
                "total_remaining": total_remaining,
                "is_unlimited": total_remaining == -1,
                "is_quota_exhausted": total_remaining == 0,
                # Primary package info for header display
                "plan": primary_pkg.get("plan", "trial"),
                "plan_name": primary_pkg.get("plan_name", "Deneme"),
                "wix_member_id": wix_member_id,
                # Legacy compatibility
                "remaining": total_remaining,
                "is_trial": primary_pkg.get("plan") == "trial",
                "is_expired": len(active_packages) == 0
            }
    
    # Legacy single plan system
    plan = sub.get("plan", "trial")
    plan_info = SUBSCRIPTION_PLANS.get(plan, SUBSCRIPTION_PLANS["trial"])
    
    total_uploads = sub.get("monthly_uploads", 0)  # Now represents total usage
    limit = plan_info["monthly_limit"]  # Total limit for the subscription period
    
    # Calculate remaining
    if limit == -1:
        remaining = -1  # Unlimited
    else:
        remaining = max(0, limit - total_uploads)
    
    # Check expiration
    expires_at = sub.get("expires_at")
    is_expired = False
    days_remaining = None
    is_annual_plan = plan != "trial" and plan != "unlimited"
    
    if expires_at:
        try:
            exp_date = datetime.fromisoformat(expires_at.replace('Z', '+00:00'))
            now = datetime.now(timezone.utc)
            is_expired = now > exp_date
            if not is_expired:
                days_remaining = (exp_date - now).days
        except:
            pass
    
    # Check if quota is exhausted
    is_quota_exhausted = remaining == 0 and limit != -1
    
    return {
        "has_multi_packages": False,
        "packages": [],
        "plan": plan,
        "plan_name": plan_info["name"],
        "total_limit": limit,  # Renamed from monthly_limit
        "total_uploads": total_uploads,  # Renamed from monthly_uploads
        "remaining": remaining,
        "is_trial": plan == "trial",
        "trial_used": sub.get("trial_used", False),
        "is_unlimited": limit == -1,
        "is_annual_plan": is_annual_plan,
        "wix_member_id": sub.get("wix_member_id"),
        "plan_start_date": sub.get("plan_start_date"),
        "expires_at": expires_at,
        "is_expired": is_expired,
        "is_quota_exhausted": is_quota_exhausted,
        "days_remaining": days_remaining,
        # Legacy fields for backward compatibility
        "monthly_limit": limit,
        "monthly_uploads": total_uploads
    }

@api_router.post("/subscription/upgrade")
async def upgrade_subscription(
    plan_id: str = Form(...),
    wix_member_id: str = Form(None),
    user_id: str = Depends(get_current_user)
):
    """Upgrade user subscription (called after Wix payment confirmation)"""
    if plan_id not in SUBSCRIPTION_PLANS:
        raise HTTPException(status_code=400, detail="Geçersiz plan")
    
    if plan_id == "trial":
        raise HTTPException(status_code=400, detail="Deneme planına geçiş yapılamaz")
    
    current_month = datetime.now(timezone.utc).strftime("%Y-%m")
    
    update_data = {
        "plan": plan_id,
        "monthly_uploads": 0,  # Reset counter on upgrade
        "month_reset": current_month,
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
    
    if wix_member_id:
        update_data["wix_member_id"] = wix_member_id
    
    result = await db.subscriptions.update_one(
        {"user_id": user_id},
        {"$set": update_data}
    )
    
    if result.matched_count == 0:
        # Create new subscription
        sub = {
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "wix_member_id": wix_member_id,
            "plan": plan_id,
            "monthly_uploads": 0,
            "month_reset": current_month,
            "trial_used": True,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
        await db.subscriptions.insert_one(sub)
    
    plan_info = SUBSCRIPTION_PLANS[plan_id]
    return {
        "success": True,
        "message": f"{plan_info['name']} planına geçiş yapıldı",
        "plan": plan_id,
        "monthly_limit": plan_info["monthly_limit"]
    }

@api_router.post("/subscription/link-wix")
async def link_wix_member(
    wix_member_id: str = Form(...),
    user_id: str = Depends(get_current_user)
):
    """Link Wix Member ID to subscription for cross-device sync"""
    # Check if wix_member_id already exists
    existing = await db.subscriptions.find_one({"wix_member_id": wix_member_id}, {"_id": 0})
    
    if existing and existing.get("user_id") != user_id:
        # Wix member already has a subscription - merge data
        # Transfer subscription to current session
        await db.subscriptions.update_one(
            {"user_id": user_id},
            {"$set": {
                "plan": existing.get("plan", "trial"),
                "monthly_uploads": existing.get("monthly_uploads", 0),
                "month_reset": existing.get("month_reset", ""),
                "trial_used": existing.get("trial_used", False),
                "wix_member_id": wix_member_id,
                "updated_at": datetime.now(timezone.utc).isoformat()
            }}
        )
        # Remove old subscription
        await db.subscriptions.delete_one({"id": existing.get("id")})
    else:
        # Just link wix_member_id
        await db.subscriptions.update_one(
            {"user_id": user_id},
            {"$set": {
                "wix_member_id": wix_member_id,
                "updated_at": datetime.now(timezone.utc).isoformat()
            }}
        )
    
    return {"success": True, "message": "Wix hesabı bağlandı"}

# Admin API Key for secure operations
ADMIN_API_KEY = os.environ.get('ADMIN_API_KEY', 'documander-admin-key-2025')

@api_router.post("/admin/activate-subscription")
async def admin_activate_subscription(
    wix_member_id: str = Form(...),
    plan: str = Form(...),
    admin_key: str = Form(...),
    duration_days: int = Form(365)  # Default 365 days (12 months) for paid plans
):
    """
    Admin endpoint to activate subscription after Wix payment.
    Called manually or via Wix Webhook when payment is confirmed.
    
    duration_days: Subscription duration in days (7=trial, 365=1 year for paid plans)
    """
    # Verify admin key
    if admin_key != ADMIN_API_KEY:
        raise HTTPException(status_code=403, detail="Geçersiz admin anahtarı")
    
    # Validate plan
    if plan not in SUBSCRIPTION_PLANS or plan == "trial":
        raise HTTPException(status_code=400, detail="Geçersiz plan")
    
    # Calculate expiration date
    expires_at = (datetime.now(timezone.utc) + timedelta(days=duration_days)).isoformat()
    
    # Find subscription by Wix Member ID
    existing = await db.subscriptions.find_one({"wix_member_id": wix_member_id}, {"_id": 0})
    
    current_month = datetime.now(timezone.utc).strftime("%Y-%m")
    
    if existing:
        # Update existing subscription
        await db.subscriptions.update_one(
            {"wix_member_id": wix_member_id},
            {"$set": {
                "plan": plan,
                "monthly_uploads": 0,
                "month_reset": current_month,
                "trial_used": True,
                "expires_at": expires_at,
                "updated_at": datetime.now(timezone.utc).isoformat()
            }}
        )
    else:
        # Create new subscription for this Wix member
        new_sub = {
            "id": str(uuid.uuid4()),
            "user_id": f"wix_{wix_member_id}",
            "wix_member_id": wix_member_id,
            "plan": plan,
            "monthly_uploads": 0,
            "month_reset": current_month,
            "trial_used": True,
            "expires_at": expires_at,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
        await db.subscriptions.insert_one(new_sub)
    
    plan_info = SUBSCRIPTION_PLANS[plan]
    return {
        "success": True,
        "message": f"Abonelik aktive edildi: {plan_info['name']}",
        "wix_member_id": wix_member_id,
        "plan": plan,
        "monthly_limit": plan_info["monthly_limit"],
        "expires_at": expires_at
    }

@api_router.get("/admin/subscriptions")
async def admin_list_subscriptions(
    admin_key: str
):
    """Admin endpoint to list all subscriptions"""
    if admin_key != ADMIN_API_KEY:
        raise HTTPException(status_code=403, detail="Geçersiz admin anahtarı")
    
    subs = await db.subscriptions.find({}, {"_id": 0}).to_list(1000)
    
    # Add plan details
    for sub in subs:
        plan = sub.get("plan", "trial")
        plan_info = SUBSCRIPTION_PLANS.get(plan, SUBSCRIPTION_PLANS["trial"])
        sub["plan_name"] = plan_info["name"]
        sub["monthly_limit"] = plan_info["monthly_limit"]
    
    return {"subscriptions": subs, "total": len(subs)}

@api_router.post("/admin/deactivate-subscription")
async def admin_deactivate_subscription(
    wix_member_id: str = Form(...),
    admin_key: str = Form(...)
):
    """Admin endpoint to deactivate/downgrade subscription to trial"""
    if admin_key != ADMIN_API_KEY:
        raise HTTPException(status_code=403, detail="Geçersiz admin anahtarı")
    
    result = await db.subscriptions.update_one(
        {"wix_member_id": wix_member_id},
        {"$set": {
            "plan": "trial",
            "updated_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Abonelik bulunamadı")
    
    return {"success": True, "message": "Abonelik iptal edildi"}

# Invoice AI Processing
async def extract_invoice_data_with_ai(file_content: bytes, file_name: str, mime_type: str) -> dict:
    import base64
    from io import BytesIO
    try:
        # Initialize LLM Chat with OpenAI GPT-4o Vision
        chat = LlmChat(
            api_key=EMERGENT_LLM_KEY,
            session_id=f"invoice-extraction-{uuid.uuid4()}",
            system_message="You are an invoice data extraction assistant. Extract invoice information accurately from Turkish invoices and receipts."
        ).with_model("openai", "gpt-4o")
        
        from emergentintegrations.llm.chat import ImageContent
        
        # Handle PDF files - convert to images first
        if mime_type == 'application/pdf' or file_name.lower().endswith('.pdf'):
            try:
                from pdf2image import convert_from_bytes
                from PIL import Image
                
                # First try to extract text directly from PDF using pdfplumber
                try:
                    import pdfplumber
                    pdf_text = ""
                    with pdfplumber.open(BytesIO(file_content)) as pdf:
                        for page in pdf.pages[:3]:  # First 3 pages
                            page_text = page.extract_text()
                            if page_text:
                                pdf_text += page_text + "\n"
                    
                    # If we got substantial text, use text-based extraction
                    if pdf_text and len(pdf_text.strip()) > 100:
                        logger.info(f"PDF text extraction successful, length: {len(pdf_text)}")
                        # Log first 1000 chars of extracted text for debugging
                        logger.info(f"PDF text preview: {pdf_text[:1000]}")
                        result = await _extract_from_text(chat, pdf_text)
                        if result and not isinstance(result, dict) or "error" not in result:
                            return {"invoices": result if isinstance(result, list) else [result]}
                        logger.info("Text extraction failed, falling back to image conversion")
                except Exception as text_err:
                    logger.info(f"PDF text extraction failed: {text_err}, using image conversion")
                
                # Fall back to image conversion with higher DPI for better quality
                # Use 300 DPI for scanned documents for better OCR accuracy
                images = convert_from_bytes(file_content, dpi=300, first_page=1, last_page=3)
                
                if not images:
                    return {"error": "PDF dosyası okunamadı"}
                
                # Process each page
                all_invoices = []
                for page_num, img in enumerate(images):
                    # Convert PIL image to base64 with high quality
                    img_buffer = BytesIO()
                    # Use PNG for lossless quality - better for OCR
                    img = img.convert('RGB')
                    img.save(img_buffer, format='PNG', optimize=False)
                    img_buffer.seek(0)
                    image_base64 = base64.b64encode(img_buffer.read()).decode('utf-8')
                    
                    # Create image content
                    image_obj = ImageContent(image_base64=image_base64)
                    
                    # Extract data from this page
                    page_result = await _extract_from_image(chat, image_obj)
                    # _extract_from_image returns a list of invoices directly
                    if isinstance(page_result, list):
                        all_invoices.extend(page_result)
                    elif isinstance(page_result, dict) and "invoices" in page_result:
                        all_invoices.extend(page_result["invoices"])
                    elif isinstance(page_result, dict) and "error" not in page_result:
                        all_invoices.append(page_result)
                
                if all_invoices:
                    return {"invoices": all_invoices}
                else:
                    return {"error": "PDF'den fatura verisi çıkarılamadı"}
                    
            except Exception as pdf_error:
                logger.error(f"PDF conversion error: {pdf_error}")
                return {"error": f"PDF dönüştürme hatası: {str(pdf_error)}"}
        
        # Handle image files directly
        image_base64 = base64.b64encode(file_content).decode('utf-8')
        image_obj = ImageContent(image_base64=image_base64)
        
        return await _extract_from_image(chat, image_obj)
        
    except Exception as e:
        logger.error(f"AI extraction error: {e}")
        return {"error": str(e)}

async def _extract_from_text(chat, text: str) -> list:
    """Helper function to extract invoice data from PDF text"""
    from emergentintegrations.llm.chat import UserMessage
    
    prompt = f"""Bu metin bir e-fatura PDF'inden çıkarılmıştır. Fatura bilgilerini DİKKATLİCE çıkar.

FATURA METNİ:
{text}

FATURA NUMARASI BULMA KURALLARI (ÇOK ÖNEMLİ):
1. "ETTN" veya "Fatura No" veya "Belge No" etiketinin yanındaki değeri bul
2. GIB ile başlayan 16 haneli numara fatura numarasıdır (örn: GIB2025000000051)
3. Eğer birden fazla numara varsa, GIB ile başlayanı tercih et
4. Metinde tam olarak yazan değeri kullan, tahmin yapma

Çıkarılacak bilgiler:
- invoice_number: ETTN veya Fatura No değeri (GIB ile başlayan 16 haneli numara)
- date: Fatura tarihi (GG/AA/YYYY formatında)
- issuer_name: Satıcı/düzenleyen firma adı
- issuer_tax_id: Satıcı vergi numarası (10-11 haneli rakam)
- issuer_tax_office: Satıcı vergi dairesi (BÜYÜK HARFLERLE)
- customer_name: Alıcı/müşteri adı
- customer_tax_id: Alıcı vergi numarası
- customer_tax_office: Alıcı vergi dairesi
- description: Mal/hizmet açıklaması (3-5 kelime özet)
- amount: Mal Hizmet Toplam Tutarı (KDV hariç)
- vat: Hesaplanan KDV tutarı
- total: Ödenecek Tutar (KDV dahil)
- vat_details: KDV oranları ve tutarları listesi

SADECE JSON formatında yanıt ver:
{{"invoices": [{{"invoice_number": "GIB...", "date": "...", ...}}]}}"""

    try:
        message = UserMessage(text=prompt)
        response = await chat.send_message(message)
        
        response_text = response.strip() if response else ""
        if response_text.startswith("```json"):
            response_text = response_text[7:]
        if response_text.startswith("```"):
            response_text = response_text[3:]
        if response_text.endswith("```"):
            response_text = response_text[:-3]
        response_text = response_text.strip()
        
        if not response_text:
            return {"error": "Empty response from LLM"}
        
        data = json.loads(response_text)
        if "invoices" in data:
            return data["invoices"]
        return [data]
    except Exception as e:
        logger.error(f"Text extraction error: {e}")
        return {"error": str(e)}

async def _extract_from_image(chat, image_obj) -> dict:
    """Helper function to extract invoice data from an image"""
    prompt = """Bu görseli analiz et. Eğer birden fazla fiş/fatura varsa HER BİRİNİ AYRI AYRI çıkar.

TARANMIŞ/BULANIK GÖRÜNTÜ İÇİN ÖNEMLİ:
- Karakterleri dikkatli oku, OCR hataları olabilir
- Fatura numarası genellikle "GIB" ile başlar ve 16 haneli olur (örn: GIB2025000000050)
- Fatura numarasında sadece harf ve rakam bulunur, özel karakter (!, ?, @) OLMAZ
- Eğer belirsiz karakterler varsa, mantıklı olanı seç (örn: "0" ve "O", "1" ve "I")

Her fiş/fatura için şu bilgileri çıkar:
- invoice_number: Fatura/fiş numarası (GIB ile başlayan 16 haneli veya farklı format - özel karakter OLMADAN)
- date: Fatura tarihi (GG/AA/YYYY formatında)
- issuer_name: Faturayı düzenleyen firma/kişi adı
- issuer_tax_id: Vergi kimlik numarası (TCKN 11 hane, VKN 10 hane - sadece rakam)
- issuer_tax_office: Vergi dairesi (SADECE isim, BÜYÜK HARFLERLE, "VERGİ DAİRESİ", "V.D." gibi ekler OLMADAN)
- customer_name: Müşteri adı (varsa)
- customer_tax_id: Müşteri vergi numarası (varsa)
- customer_tax_office: Müşteri vergi dairesi (varsa)
- description: Fatura içeriğinin KISA özeti (3-5 kelime)
- amount: Net tutar (sadece sayı)
- vat: KDV tutarı (sadece sayı)
- total: Toplam tutar (sadece sayı)
- vat_details: KDV DETAYLARI - Türkiye KDV oranlarına göre (%1, %10, %20) ayrıştır. Her KDV oranı için:
  - vat_rate: KDV oranı (1, 10 veya 20)
  - base_amount: O orana ait matrah (KDV hariç tutar)
  - vat_amount: O orana ait KDV tutarı
  - withholding: Tevkifat var mı (true/false)
  - withholding_rate: Tevkifat oranı varsa (örn: "5/10", "9/10", null yoksa)

ÖNEMLİ KDV KURALLARI:
- Faturada farklı KDV oranları varsa her birini ayrı ayrı listele
- KDV oranı belirtilmemişse, tutardan hesapla (örn: KDV/Matrah oranına bak)
- Tevkifatlı faturalarda tevkifat oranını belirt
- Eğer KDV detayı bulunamıyorsa, toplam KDV'yi tek satır olarak göster

SADECE JSON formatında yanıt ver. 
- Tek fiş varsa: {"invoices": [{ ... fiş bilgileri ... }]}
- Birden fazla fiş varsa: {"invoices": [{ fiş1 }, { fiş2 }, ...]}

Örnek:
{"invoices": [{"invoice_number": "FIS-001", "date": "15/01/2024", "issuer_name": "ABC Market", "issuer_tax_id": "1234567890", "issuer_tax_office": "KADIKÖY", "customer_name": "", "customer_tax_id": "", "customer_tax_office": "", "description": "Market alışverişi", "amount": 100.0, "vat": 20.0, "total": 120.0, "vat_details": [{"vat_rate": 20, "base_amount": 100.0, "vat_amount": 20.0, "withholding": false, "withholding_rate": null}]}]}

Birden fazla KDV oranı örneği:
{"invoices": [{"invoice_number": "FTR-002", "date": "20/01/2024", "issuer_name": "XYZ Ltd", "issuer_tax_id": "9876543210", "issuer_tax_office": "BEYOĞLU", "customer_name": "Müşteri A.Ş.", "customer_tax_id": "1111111111", "customer_tax_office": "ŞİŞLİ", "description": "Muhtelif ürünler", "amount": 250.0, "vat": 35.0, "total": 285.0, "vat_details": [{"vat_rate": 10, "base_amount": 150.0, "vat_amount": 15.0, "withholding": false, "withholding_rate": null}, {"vat_rate": 20, "base_amount": 100.0, "vat_amount": 20.0, "withholding": false, "withholding_rate": null}]}]}"""
    
    message = UserMessage(
        text=prompt,
        file_contents=[image_obj]
    )
    
    response = await chat.send_message(message)
    
    # Parse response
    logger.info(f"Raw LLM response: '{response}'")
    logger.info(f"Response type: {type(response)}")
    logger.info(f"Response length: {len(response) if response else 0}")
    
    response_text = response.strip() if response else ""
    logger.info(f"After strip: '{response_text}'")
    
    if response_text.startswith("```json"):
        response_text = response_text[7:]
    if response_text.startswith("```"):
        response_text = response_text[3:]
    if response_text.endswith("```"):
        response_text = response_text[:-3]
    response_text = response_text.strip()
    
    logger.info(f"Final response text for JSON parsing: '{response_text}'")
    
    if not response_text:
        logger.error("Empty response from LLM after processing")
        return {"error": "LLM returned empty response"}
    
    try:
        data = json.loads(response_text)
    except json.JSONDecodeError as e:
        logger.error(f"JSON parsing failed: {e}")
        logger.error(f"Problematic text: '{response_text}'")
        return {"error": f"JSON parsing failed: {e}"}
    
    # Normalize response to always return a list of invoices
    if "invoices" in data:
        return data["invoices"]
    else:
        # Single invoice in old format - wrap in list
        return [data]

# Helper function for safe float conversion
def safe_float(value, default=0.0):
    try:
        if value is None:
            return default
        return float(value)
    except (ValueError, TypeError):
        return default

# Helper to validate invoice date against session
def validate_invoice_date(invoice_date: str, session_year: int, session_month: int) -> tuple:
    """Returns (is_valid, error_message)"""
    try:
        # Parse DD/MM/YYYY format
        parts = invoice_date.split('/')
        if len(parts) == 3:
            day, month, year = int(parts[0]), int(parts[1]), int(parts[2])
            if month == session_month and year == session_year:
                return True, None
            else:
                return False, f"Fatura tarihi ({invoice_date}) seçili dönemle uyuşmuyor ({session_month:02d}/{session_year})"
    except:
        pass
    return True, None  # If we can't parse, allow it

# Invoice Routes
@api_router.post("/invoices/upload")
async def upload_invoice(
    files: List[UploadFile] = File(...),
    category: str = Form(...),
    user_id: str = Depends(get_current_user)
):
    if category not in ['income', 'expense']:
        raise HTTPException(status_code=400, detail="Category must be 'income' or 'expense'")
    
    # Get current session
    session = await db.taxpayer_sessions.find_one({"user_id": user_id}, {"_id": 0})
    if not session:
        raise HTTPException(status_code=400, detail="Önce mükellef bilgilerini girin")
    
    allowed_types = ['application/pdf', 'image/jpeg', 'image/jpg', 'image/png', 'text/xml', 'application/xml', 'text/html']
    uploaded_invoices = []
    errors = []
    date_mismatches = []
    total_receipts_found = 0
    
    for file in files:
        try:
            # Validate file type
            if file.content_type not in allowed_types:
                errors.append(f"{file.filename}: Geçersiz dosya türü")
                continue
            
            # Read file
            file_content = await file.read()
            
            # Extract data with AI - now returns a list of invoices
            mime_type = file.content_type
            if mime_type == 'image/jpg':
                mime_type = 'image/jpeg'
            
            logger.info(f"Processing file: {file.filename}, mime: {mime_type}")
            ai_result = await extract_invoice_data_with_ai(file_content, file.filename, mime_type)
            logger.info(f"AI result type: {type(ai_result)}, content: {str(ai_result)[:500]}")
            
            # Handle error responses
            if isinstance(ai_result, dict) and "error" in ai_result:
                errors.append(f"{file.filename}: {ai_result['error']}")
                continue
            
            # Extract invoices from result - handle both dict and list formats
            if isinstance(ai_result, dict) and "invoices" in ai_result:
                extracted_invoices = ai_result["invoices"]
            elif isinstance(ai_result, list):
                extracted_invoices = ai_result
            else:
                extracted_invoices = [ai_result] if ai_result else []
            
            logger.info(f"Extracted {len(extracted_invoices)} invoices from {file.filename}")
            
            if not extracted_invoices:
                errors.append(f"{file.filename}: Fatura verisi çıkarılamadı")
                continue
            
            # Process each receipt found in the image
            receipts_in_file = len(extracted_invoices)
            total_receipts_found += receipts_in_file
            
            # Check quota BEFORE processing this file's receipts
            can_upload, limit_msg, remaining = await check_upload_limit(user_id, receipts_in_file)
            if not can_upload:
                errors.append(f"{file.filename}: {limit_msg} (Bu dosyada {receipts_in_file} fiş bulundu)")
                continue
            
            file_invoices_added = 0
            file_date_mismatches = []
            
            for idx, extracted_data in enumerate(extracted_invoices):
                # Validate invoice date against session period
                invoice_date = extracted_data.get('date', '') or ''
                is_valid, error_msg = validate_invoice_date(invoice_date, session['year'], session['month'])
                
                if not is_valid:
                    receipt_label = f"Fiş {idx + 1}" if len(extracted_invoices) > 1 else "Fiş"
                    file_date_mismatches.append(f"{receipt_label}: {error_msg}")
                    continue
                
                # Process VAT details - normalize different AI response formats
                raw_vat_details = extracted_data.get('vat_details', [])
                vat_details = []
                
                if raw_vat_details:
                    for vd in raw_vat_details:
                        # Handle different field names from AI
                        rate = vd.get('vat_rate') or vd.get('rate') or vd.get('percentage') or 0
                        # Clean rate if it's a string like "20%" 
                        if isinstance(rate, str):
                            rate = rate.replace('%', '').replace(' ', '')
                            try:
                                rate = float(rate)
                            except:
                                rate = 0
                        
                        base = vd.get('base_amount') or vd.get('base') or 0
                        amount = vd.get('vat_amount') or vd.get('amount') or vd.get('tax_amount') or 0
                        
                        # Clean amounts if strings
                        base = safe_float(base)
                        amount = safe_float(amount)
                        
                        vat_details.append({
                            "vat_rate": float(rate),
                            "base_amount": base,
                            "vat_amount": amount,
                            "withholding": vd.get('withholding', False),
                            "withholding_rate": vd.get('withholding_rate')
                        })
                
                # If still no vat_details, create default from total VAT
                if not vat_details:
                    total_vat = safe_float(extracted_data.get('vat'))
                    total_amount = safe_float(extracted_data.get('amount'))
                    if total_vat > 0 and total_amount > 0:
                        # Try to determine VAT rate
                        vat_rate_calc = round((total_vat / total_amount) * 100)
                        # Round to nearest standard rate (1, 10, 20)
                        if vat_rate_calc <= 5:
                            vat_rate = 1
                        elif vat_rate_calc <= 15:
                            vat_rate = 10
                        else:
                            vat_rate = 20
                        vat_details = [{
                            "vat_rate": vat_rate,
                            "base_amount": total_amount,
                            "vat_amount": total_vat,
                            "withholding": False,
                            "withholding_rate": None
                        }]
                
                # Create invoice
                invoice = Invoice(
                    user_id=user_id,
                    session_id=session['id'],
                    category=category,
                    invoice_number=extracted_data.get('invoice_number', 'N/A') or 'N/A',
                    date=invoice_date,
                    issuer_name=extracted_data.get('issuer_name', 'N/A') or 'N/A',
                    issuer_tax_id=extracted_data.get('issuer_tax_id', 'N/A') or 'N/A',
                    issuer_tax_office=extracted_data.get('issuer_tax_office', 'N/A') or 'N/A',
                    customer_name=extracted_data.get('customer_name', 'N/A') or 'N/A',
                    customer_tax_id=extracted_data.get('customer_tax_id', 'N/A') or 'N/A',
                    customer_tax_office=extracted_data.get('customer_tax_office', 'N/A') or 'N/A',
                    description=extracted_data.get('description', 'N/A') or 'N/A',
                    amount=safe_float(extracted_data.get('amount')),
                    vat=safe_float(extracted_data.get('vat')),
                    total=safe_float(extracted_data.get('total')),
                    file_name=file.filename,
                    file_type=file.content_type,
                    vat_details=vat_details
                )
                
                invoice_dict = invoice.model_dump()
                invoice_dict['created_at'] = invoice_dict['created_at'].isoformat()
                
                await db.invoices.insert_one(invoice_dict)
                uploaded_invoices.append(invoice)
                file_invoices_added += 1
            
            # Add date mismatch warnings for this file
            if file_date_mismatches:
                if len(extracted_invoices) > 1:
                    date_mismatches.append(f"{file.filename} ({len(extracted_invoices)} fiş bulundu): " + "; ".join(file_date_mismatches))
                else:
                    date_mismatches.append(f"{file.filename}: {file_date_mismatches[0]}")
            
            # Increment quota for successfully added invoices from this file
            if file_invoices_added > 0:
                await increment_upload_count(user_id, file_invoices_added)
            
        except Exception as e:
            errors.append(f"{file.filename}: {str(e)}")
    
    # Get updated quota info
    _, _, new_remaining = await check_upload_limit(user_id)
    
    # Prepare quota warning
    quota_warning = None
    if new_remaining != -1 and new_remaining <= 5:
        quota_warning = f"Dikkat: Kalan fiş hakkınız: {new_remaining}"
    
    response_data = {
        "success": len(uploaded_invoices),
        "failed": len(errors) + len(date_mismatches),
        "total_receipts_found": total_receipts_found,
        "invoices": uploaded_invoices,
        "errors": errors,
        "date_mismatches": date_mismatches,
        "remaining_quota": new_remaining
    }
    
    if quota_warning:
        response_data["quota_warning"] = quota_warning
    
    return response_data

@api_router.get("/invoices", response_model=List[Invoice])
async def get_invoices(
    category: Optional[str] = None,
    user_id: str = Depends(get_current_user)
):
    # Get current session
    session = await db.taxpayer_sessions.find_one({"user_id": user_id}, {"_id": 0})
    
    query = {"user_id": user_id}
    if session:
        query["session_id"] = session['id']
    if category:
        query["category"] = category
    
    invoices = await db.invoices.find(query, {"_id": 0}).to_list(1000)
    
    for invoice in invoices:
        if isinstance(invoice['created_at'], str):
            invoice['created_at'] = datetime.fromisoformat(invoice['created_at'])
        
        # Add missing fields for backward compatibility
        if 'category' not in invoice:
            invoice['category'] = 'income'
        if 'session_id' not in invoice:
            invoice['session_id'] = ''
        if 'issuer_name' not in invoice:
            invoice['issuer_name'] = 'N/A'
        if 'issuer_tax_id' not in invoice:
            invoice['issuer_tax_id'] = 'N/A'
        if 'issuer_tax_office' not in invoice:
            invoice['issuer_tax_office'] = 'N/A'
        if 'customer_tax_id' not in invoice:
            invoice['customer_tax_id'] = invoice.get('tax_id', 'N/A')
        if 'customer_tax_office' not in invoice:
            invoice['customer_tax_office'] = invoice.get('tax_office', 'N/A')
        if 'description' not in invoice:
            invoice['description'] = 'N/A'
        if 'vat_details' not in invoice:
            invoice['vat_details'] = []
    
    # Sort by date (newest first)
    def parse_date(date_str):
        try:
            parts = date_str.split('/')
            if len(parts) == 3:
                return datetime(int(parts[2]), int(parts[1]), int(parts[0]))
        except:
            pass
        return datetime.min
    
    invoices.sort(key=lambda x: parse_date(x.get('date', '')), reverse=False)  # Oldest first
    
    return invoices

@api_router.get("/invoices/vat-report")
async def get_vat_report(user_id: str = Depends(get_current_user)):
    """Get VAT report with breakdown by rates for current session"""
    session = await db.taxpayer_sessions.find_one(
        {"user_id": user_id},
        {"_id": 0}
    )
    
    if not session:
        raise HTTPException(status_code=404, detail="Aktif oturum bulunamadı")
    
    # Get all invoices for this session
    invoices = await db.invoices.find(
        {"user_id": user_id, "session_id": session['id']},
        {"_id": 0}
    ).to_list(1000)
    
    # Process VAT details for each invoice
    vat_report_items = []
    vat_summary = {
        1: {"base_total": 0, "vat_total": 0},
        10: {"base_total": 0, "vat_total": 0},
        20: {"base_total": 0, "vat_total": 0}
    }
    
    for invoice in invoices:
        vat_details = invoice.get('vat_details', [])
        
        # If no vat_details, create from total
        if not vat_details:
            vat = float(invoice.get('vat', 0) or 0)
            amount = float(invoice.get('amount', 0) or 0)
            if vat > 0:
                # Estimate VAT rate
                if amount > 0:
                    rate_calc = round((vat / amount) * 100)
                    if rate_calc <= 5:
                        vat_rate = 1
                    elif rate_calc <= 15:
                        vat_rate = 10
                    else:
                        vat_rate = 20
                else:
                    vat_rate = 20  # Default
                vat_details = [{
                    "vat_rate": vat_rate,
                    "base_amount": amount,
                    "vat_amount": vat,
                    "withholding": False,
                    "withholding_rate": None
                }]
        
        # Add each VAT detail as a separate report item
        for detail in vat_details:
            vat_rate = int(detail.get('vat_rate', 20))
            base_amount = float(detail.get('base_amount', 0) or 0)
            vat_amount = float(detail.get('vat_amount', 0) or 0)
            
            report_item = {
                "invoice_id": invoice.get('id'),
                "invoice_number": invoice.get('invoice_number', 'N/A'),
                "date": invoice.get('date', ''),
                "category": invoice.get('category', 'income'),
                # Issuer info (for expense invoices)
                "issuer_name": invoice.get('issuer_name', 'N/A'),
                "issuer_tax_id": invoice.get('issuer_tax_id', 'N/A'),
                "issuer_tax_office": invoice.get('issuer_tax_office', 'N/A'),
                # Customer info (for income invoices)
                "customer_name": invoice.get('customer_name', 'N/A'),
                "customer_tax_id": invoice.get('customer_tax_id', 'N/A'),
                "customer_tax_office": invoice.get('customer_tax_office', 'N/A'),
                "description": invoice.get('description', 'N/A'),
                "vat_rate": vat_rate,
                "base_amount": base_amount,
                "vat_amount": vat_amount,
                "withholding": detail.get('withholding', False),
                "withholding_rate": detail.get('withholding_rate')
            }
            vat_report_items.append(report_item)
            
            # Add to summary
            if vat_rate in vat_summary:
                vat_summary[vat_rate]["base_total"] += base_amount
                vat_summary[vat_rate]["vat_total"] += vat_amount
    
    # Sort by date
    def parse_date(date_str):
        try:
            parts = date_str.split('/')
            if len(parts) == 3:
                return datetime(int(parts[2]), int(parts[1]), int(parts[0]))
        except:
            pass
        return datetime.min
    
    vat_report_items.sort(key=lambda x: parse_date(x.get('date', '')))
    
    # Calculate grand total
    grand_total_base = sum(s["base_total"] for s in vat_summary.values())
    grand_total_vat = sum(s["vat_total"] for s in vat_summary.values())
    
    return {
        "items": vat_report_items,
        "summary": [
            {"vat_rate": 1, "base_total": vat_summary[1]["base_total"], "vat_total": vat_summary[1]["vat_total"]},
            {"vat_rate": 10, "base_total": vat_summary[10]["base_total"], "vat_total": vat_summary[10]["vat_total"]},
            {"vat_rate": 20, "base_total": vat_summary[20]["base_total"], "vat_total": vat_summary[20]["vat_total"]}
        ],
        "grand_total": {
            "base": grand_total_base,
            "vat": grand_total_vat
        }
    }

@api_router.get("/invoices/vat-report/excel")
async def export_vat_report_to_excel(
    category: Optional[str] = None,
    user_id: str = Depends(get_current_user)
):
    """Export VAT report to Excel"""
    # Get current session
    session = await db.taxpayer_sessions.find_one({"user_id": user_id}, {"_id": 0})
    if not session:
        raise HTTPException(status_code=404, detail="Aktif oturum bulunamadı")
    
    # Build query
    query = {
        "user_id": user_id,
        "session_id": session['id']
    }
    # Filter by category for detail exports, but get all for summary exports
    if category and category in ['income', 'expense']:
        query["category"] = category
    
    invoices = await db.invoices.find(query, {"_id": 0}).to_list(1000)
    
    # For summary exports, we need data even if no detail invoices
    if not invoices and category not in ['summary-income', 'summary-expense', 'summary-net']:
        raise HTTPException(status_code=404, detail="KDV verisi bulunamadı")
    
    # Collect VAT items
    vat_items = []
    for invoice in invoices:
        vat_details = invoice.get('vat_details', [])
        if not vat_details:
            # Create single entry from total VAT
            vat_amount = float(invoice.get('vat', 0) or 0)
            net_amount = float(invoice.get('amount', 0) or 0)
            if vat_amount > 0 and net_amount > 0:
                vat_rate = round((vat_amount / net_amount) * 100)
                if vat_rate not in [1, 10, 20]:
                    vat_rate = 20
                vat_details = [{"vat_rate": vat_rate, "base_amount": net_amount, "vat_amount": vat_amount}]
        
        for detail in vat_details:
            vat_items.append({
                "invoice_number": invoice.get('invoice_number', 'N/A'),
                "date": invoice.get('date', ''),
                "category": invoice.get('category', 'income'),
                "issuer_name": invoice.get('issuer_name', ''),
                "issuer_tax_id": invoice.get('issuer_tax_id', ''),
                "issuer_tax_office": invoice.get('issuer_tax_office', ''),
                "customer_name": invoice.get('customer_name', ''),
                "customer_tax_id": invoice.get('customer_tax_id', ''),
                "customer_tax_office": invoice.get('customer_tax_office', ''),
                "description": invoice.get('description', ''),
                "vat_rate": int(detail.get('vat_rate', 20)),
                "base_amount": float(detail.get('base_amount', 0) or 0),
                "vat_amount": float(detail.get('vat_amount', 0) or 0)
            })
    
    # Turkish month names
    month_names = {
        1: 'Ocak', 2: 'Şubat', 3: 'Mart', 4: 'Nisan', 5: 'Mayıs', 6: 'Haziran',
        7: 'Temmuz', 8: 'Ağustos', 9: 'Eylül', 10: 'Ekim', 11: 'Kasım', 12: 'Aralık'
    }
    
    # Create workbook
    wb = Workbook()
    ws = wb.active
    ws.title = "KDV Raporu"
    
    header_fill = PatternFill(start_color="004D40", end_color="004D40", fill_type="solid")
    header_font = Font(bold=True, color="FFFFFF")
    number_format = '#,##0.00'
    
    current_row = 1
    taxpayer_name = session.get('taxpayer_name', '')
    year = session.get('year', '')
    month = session.get('month', '')
    month_name = month_names.get(month, '')
    
    # Separate by category
    income_items = [i for i in vat_items if i['category'] == 'income']
    expense_items = [i for i in vat_items if i['category'] == 'expense']
    
    # Calculate totals for summary
    def calc_summary(items):
        summary = {1: {'base': 0, 'vat': 0}, 10: {'base': 0, 'vat': 0}, 20: {'base': 0, 'vat': 0}}
        for item in items:
            rate = item['vat_rate']
            if rate in summary:
                summary[rate]['base'] += item['base_amount']
                summary[rate]['vat'] += item['vat_amount']
        return summary
    
    income_summary = calc_summary(income_items)
    expense_summary = calc_summary(expense_items)
    
    # Auto-adjust column function
    def auto_adjust_columns(worksheet):
        for column_cells in worksheet.columns:
            max_length = 0
            column_letter = None
            for cell in column_cells:
                try:
                    if hasattr(cell, 'column_letter'):
                        column_letter = cell.column_letter
                    if cell.value:
                        cell_length = len(str(cell.value))
                        if cell_length > max_length:
                            max_length = cell_length
                except:
                    pass
            if column_letter and max_length > 0:
                adjusted_width = min(max_length + 3, 50)
                worksheet.column_dimensions[column_letter].width = adjusted_width
    
    # Handle summary exports
    if category == 'summary-income':
        # KDV Özet - Gelir only
        ws.title = "KDV Özet - Gelir"
        ws[f'A{current_row}'] = f"{taxpayer_name} - {month_name} {year} - KDV Özet (Gelir)"
        ws[f'A{current_row}'].font = Font(bold=True, size=16, color="004D40")
        ws.merge_cells(start_row=current_row, start_column=1, end_row=current_row, end_column=3)
        current_row += 2
        
        headers = ["KDV Oranı", "Matrah", "KDV Tutarı"]
        for col, header in enumerate(headers, 1):
            cell = ws.cell(row=current_row, column=col, value=header)
            cell.fill = header_fill
            cell.font = header_font
        current_row += 1
        
        total_base = 0
        total_vat = 0
        for rate in [1, 10, 20]:
            ws.cell(row=current_row, column=1, value=f"%{rate}")
            ws.cell(row=current_row, column=2, value=income_summary[rate]['base']).number_format = number_format
            ws.cell(row=current_row, column=3, value=income_summary[rate]['vat']).number_format = number_format
            total_base += income_summary[rate]['base']
            total_vat += income_summary[rate]['vat']
            current_row += 1
        
        ws.cell(row=current_row, column=1, value="TOPLAM").font = Font(bold=True)
        ws.cell(row=current_row, column=2, value=total_base).number_format = number_format
        ws.cell(row=current_row, column=2).font = Font(bold=True)
        ws.cell(row=current_row, column=3, value=total_vat).number_format = number_format
        ws.cell(row=current_row, column=3).font = Font(bold=True)
        
        auto_adjust_columns(ws)
        cat_suffix = "_ozet_gelir"
        
    elif category == 'summary-expense':
        # KDV Özet - Gider only
        ws.title = "KDV Özet - Gider"
        ws[f'A{current_row}'] = f"{taxpayer_name} - {month_name} {year} - KDV Özet (Gider)"
        ws[f'A{current_row}'].font = Font(bold=True, size=16, color="004D40")
        ws.merge_cells(start_row=current_row, start_column=1, end_row=current_row, end_column=3)
        current_row += 2
        
        headers = ["KDV Oranı", "Matrah", "KDV Tutarı"]
        for col, header in enumerate(headers, 1):
            cell = ws.cell(row=current_row, column=col, value=header)
            cell.fill = header_fill
            cell.font = header_font
        current_row += 1
        
        total_base = 0
        total_vat = 0
        for rate in [1, 10, 20]:
            ws.cell(row=current_row, column=1, value=f"%{rate}")
            ws.cell(row=current_row, column=2, value=expense_summary[rate]['base']).number_format = number_format
            ws.cell(row=current_row, column=3, value=expense_summary[rate]['vat']).number_format = number_format
            total_base += expense_summary[rate]['base']
            total_vat += expense_summary[rate]['vat']
            current_row += 1
        
        ws.cell(row=current_row, column=1, value="TOPLAM").font = Font(bold=True)
        ws.cell(row=current_row, column=2, value=total_base).number_format = number_format
        ws.cell(row=current_row, column=2).font = Font(bold=True)
        ws.cell(row=current_row, column=3, value=total_vat).number_format = number_format
        ws.cell(row=current_row, column=3).font = Font(bold=True)
        
        auto_adjust_columns(ws)
        cat_suffix = "_ozet_gider"
        
    elif category == 'summary-net':
        # KDV Özet - Net only
        ws.title = "KDV Özet - Net"
        ws[f'A{current_row}'] = f"{taxpayer_name} - {month_name} {year} Dönemi - Net KDV"
        ws[f'A{current_row}'].font = Font(bold=True, size=16, color="004D40")
        ws.merge_cells(start_row=current_row, start_column=1, end_row=current_row, end_column=4)
        current_row += 2
        
        headers = ["KDV Oranı", "Hesaplanan KDV (Gelir)", "İndirilecek KDV (Gider)", "Net KDV"]
        for col, header in enumerate(headers, 1):
            cell = ws.cell(row=current_row, column=col, value=header)
            cell.fill = header_fill
            cell.font = header_font
        current_row += 1
        
        total_income_vat = 0
        total_expense_vat = 0
        for rate in [1, 10, 20]:
            i_vat = income_summary[rate]['vat']
            e_vat = expense_summary[rate]['vat']
            net = i_vat - e_vat
            ws.cell(row=current_row, column=1, value=f"%{rate}")
            ws.cell(row=current_row, column=2, value=i_vat).number_format = number_format
            ws.cell(row=current_row, column=3, value=e_vat).number_format = number_format
            ws.cell(row=current_row, column=4, value=net).number_format = number_format
            total_income_vat += i_vat
            total_expense_vat += e_vat
            current_row += 1
        
        net_total = total_income_vat - total_expense_vat
        ws.cell(row=current_row, column=1, value="TOPLAM").font = Font(bold=True)
        ws.cell(row=current_row, column=2, value=total_income_vat).number_format = number_format
        ws.cell(row=current_row, column=2).font = Font(bold=True)
        ws.cell(row=current_row, column=3, value=total_expense_vat).number_format = number_format
        ws.cell(row=current_row, column=3).font = Font(bold=True)
        ws.cell(row=current_row, column=4, value=net_total).number_format = number_format
        ws.cell(row=current_row, column=4).font = Font(bold=True)
        
        current_row += 2
        result_text = "ÖDENECEK KDV" if net_total >= 0 else "SONRAKI AYA DEVREDEN KDV"
        ws.cell(row=current_row, column=1, value=result_text).font = Font(bold=True, size=14)
        ws.cell(row=current_row, column=2, value=abs(net_total)).number_format = number_format
        ws.cell(row=current_row, column=2).font = Font(bold=True, size=14)
        
        auto_adjust_columns(ws)
        cat_suffix = "_ozet_net"
        
    else:
        # Detail exports (income, expense, or all)
        title = f"{taxpayer_name} - {month_name} {year} KDV Raporu"
        if category == 'income':
            title += " (Gelir)"
        elif category == 'expense':
            title += " (Gider)"
        ws[f'A{current_row}'] = title
        ws[f'A{current_row}'].font = Font(bold=True, size=16, color="004D40")
        ws.merge_cells(start_row=current_row, start_column=1, end_row=current_row, end_column=9)
        current_row += 2
        
        def add_vat_table(items, table_title, is_income=True):
            nonlocal current_row
            
            if not items:
                return
            
            ws[f'A{current_row}'] = table_title
            ws[f'A{current_row}'].font = Font(bold=True, size=14, color="004D40")
            current_row += 1
            
            if is_income:
                headers = ["Fatura No", "Tarih", "Müşteri", "M. VKN", "M. V.Dairesi", "Açıklama", "KDV %", "Matrah", "KDV Tutarı"]
            else:
                headers = ["Fatura No", "Tarih", "Düzenleyen", "D. VKN", "D. V.Dairesi", "Açıklama", "KDV %", "Matrah", "KDV Tutarı"]
            
            for col, header in enumerate(headers, 1):
                cell = ws.cell(row=current_row, column=col, value=header)
                cell.fill = header_fill
                cell.font = header_font
            current_row += 1
            
            total_base = 0
            total_vat = 0
            for item in items:
                if is_income:
                    name = item['customer_name'] or '-'
                    tax_id = item['customer_tax_id'] or '-'
                    tax_office = item['customer_tax_office'] or '-'
                else:
                    name = item['issuer_name'] or '-'
                    tax_id = item['issuer_tax_id'] or '-'
                    tax_office = item['issuer_tax_office'] or '-'
                
                row_data = [
                    item['invoice_number'], item['date'], name, tax_id, tax_office,
                    item['description'], f"%{item['vat_rate']}", item['base_amount'], item['vat_amount']
                ]
                for col, value in enumerate(row_data, 1):
                    cell = ws.cell(row=current_row, column=col, value=value)
                    if col in [8, 9]:
                        cell.number_format = number_format
                total_base += item['base_amount']
                total_vat += item['vat_amount']
                current_row += 1
            
            ws.cell(row=current_row, column=7, value="TOPLAM:").font = Font(bold=True)
            ws.cell(row=current_row, column=8, value=total_base).number_format = number_format
            ws.cell(row=current_row, column=8).font = Font(bold=True)
            ws.cell(row=current_row, column=9, value=total_vat).number_format = number_format
            ws.cell(row=current_row, column=9).font = Font(bold=True)
            current_row += 2
        
        if not category or category == 'income':
            add_vat_table(income_items, "KDV DETAY - GELİR", is_income=True)
        if not category or category == 'expense':
            add_vat_table(expense_items, "KDV DETAY - GİDER", is_income=False)
        
        auto_adjust_columns(ws)
        cat_suffix = f"_{category}" if category else ""
    
    # Save to bytes
    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    
    # Generate filename
    safe_name = taxpayer_name.replace(' ', '_')
    filename = f"{safe_name}_{month_name}_{year}_KDV{cat_suffix}.xlsx"
    
    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": f"attachment; filename*=UTF-8''{filename}"
        }
    )

@api_router.put("/invoices/{invoice_id}")
async def update_invoice(
    invoice_id: str,
    invoice_data: InvoiceUpdate,
    user_id: str = Depends(get_current_user)
):
    existing = await db.invoices.find_one({"id": invoice_id, "user_id": user_id}, {"_id": 0})
    if not existing:
        raise HTTPException(status_code=404, detail="Invoice not found")
    
    update_data = {k: v for k, v in invoice_data.model_dump().items() if v is not None}
    
    if update_data:
        await db.invoices.update_one(
            {"id": invoice_id, "user_id": user_id},
            {"$set": update_data}
        )
    
    updated = await db.invoices.find_one({"id": invoice_id}, {"_id": 0})
    if isinstance(updated['created_at'], str):
        updated['created_at'] = datetime.fromisoformat(updated['created_at'])
    
    return Invoice(**updated)

@api_router.delete("/invoices/{invoice_id}")
async def delete_invoice(invoice_id: str, user_id: str = Depends(get_current_user)):
    result = await db.invoices.delete_one({"id": invoice_id, "user_id": user_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Invoice not found")
    return {"message": "Invoice deleted successfully"}

@api_router.delete("/invoices")
async def delete_all_invoices(
    category: Optional[str] = None,
    user_id: str = Depends(get_current_user)
):
    """Delete all invoices for the current user, optionally filtered by category"""
    query = {"user_id": user_id}
    if category and category in ['income', 'expense']:
        query["category"] = category
    
    result = await db.invoices.delete_many(query)
    return {
        "message": "Invoices deleted successfully",
        "deleted_count": result.deleted_count
    }

@api_router.get("/invoices/export/excel")
async def export_to_excel(
    category: Optional[str] = None,
    user_id: str = Depends(get_current_user)
):
    """Export all data to Excel with separate sheets for each table"""
    # Get current session for filename
    session = await db.taxpayer_sessions.find_one({"user_id": user_id}, {"_id": 0})
    
    # Build query
    query = {"user_id": user_id}
    if session:
        query["session_id"] = session['id']
    if category and category in ['income', 'expense']:
        query["category"] = category
    
    invoices = await db.invoices.find(query, {"_id": 0}).to_list(1000)
    
    if not invoices:
        raise HTTPException(status_code=404, detail="No invoices found")
    
    # Add missing category field for old records
    for invoice in invoices:
        if 'category' not in invoice:
            invoice['category'] = 'income'
    
    # Sort by date
    def parse_date(date_str):
        try:
            parts = date_str.split('/')
            if len(parts) == 3:
                return datetime(int(parts[2]), int(parts[1]), int(parts[0]))
        except:
            pass
        return datetime.min
    
    # Separate income and expense invoices
    income_invoices = [inv for inv in invoices if inv.get('category') == 'income']
    expense_invoices = [inv for inv in invoices if inv.get('category') == 'expense']
    
    income_invoices.sort(key=lambda x: parse_date(x.get('date', '')), reverse=False)
    expense_invoices.sort(key=lambda x: parse_date(x.get('date', '')), reverse=False)
    
    # Turkish month names
    month_names = {
        1: 'Ocak', 2: 'Şubat', 3: 'Mart', 4: 'Nisan', 5: 'Mayıs', 6: 'Haziran',
        7: 'Temmuz', 8: 'Ağustos', 9: 'Eylül', 10: 'Ekim', 11: 'Kasım', 12: 'Aralık'
    }
    
    # Session info
    taxpayer_name = session.get('taxpayer_name', '') if session else ''
    year = session.get('year', '') if session else ''
    month = session.get('month', '') if session else ''
    month_name = month_names.get(month, '') if month else ''
    
    # Create Excel workbook
    wb = Workbook()
    
    # Common styles
    header_fill = PatternFill(start_color="004D40", end_color="004D40", fill_type="solid")
    header_font = Font(bold=True, color="FFFFFF")
    green_fill = PatternFill(start_color="E8F5E9", end_color="E8F5E9", fill_type="solid")
    red_fill = PatternFill(start_color="FFEBEE", end_color="FFEBEE", fill_type="solid")
    number_format = '#,##0.00'
    
    # ============================================
    # SHEET 1: Gelir Faturaları
    # ============================================
    ws_income = wb.active
    ws_income.title = "Gelir Faturaları"
    
    row = 1
    if session:
        ws_income[f'A{row}'] = f"{taxpayer_name} - {month_name} {year} - Gelir Faturaları"
        ws_income[f'A{row}'].font = Font(bold=True, size=16, color="004D40")
        ws_income.merge_cells(start_row=row, start_column=1, end_row=row, end_column=9)
        row += 2
    
    if income_invoices:
        headers = ["Fatura No", "Tarih", "Müşteri", "Müşteri VKN", "Müşteri V.Dairesi", "Açıklama", "Net Tutar", "KDV", "Toplam"]
        for col, header in enumerate(headers, 1):
            cell = ws_income.cell(row=row, column=col, value=header)
            cell.fill = header_fill
            cell.font = header_font
        row += 1
        
        income_total_net = 0
        income_total_vat = 0
        income_total = 0
        for inv in income_invoices:
            net = float(inv.get('amount', 0) or 0)
            vat = float(inv.get('vat', 0) or 0)
            total = float(inv.get('total', 0) or 0)
            income_total_net += net
            income_total_vat += vat
            income_total += total
            
            row_data = [
                inv.get('invoice_number', ''), inv.get('date', ''),
                inv.get('customer_name', ''), inv.get('customer_tax_id', ''),
                inv.get('customer_tax_office', ''), inv.get('description', ''),
                net, vat, total
            ]
            for col, value in enumerate(row_data, 1):
                cell = ws_income.cell(row=row, column=col, value=value)
                if col in [7, 8, 9]:
                    cell.number_format = number_format
            row += 1
        
        # Totals row
        ws_income.cell(row=row, column=6, value="TOPLAM:").font = Font(bold=True)
        ws_income.cell(row=row, column=7, value=income_total_net).number_format = number_format
        ws_income.cell(row=row, column=7).font = Font(bold=True)
        ws_income.cell(row=row, column=8, value=income_total_vat).number_format = number_format
        ws_income.cell(row=row, column=8).font = Font(bold=True)
        ws_income.cell(row=row, column=9, value=income_total).number_format = number_format
        ws_income.cell(row=row, column=9).font = Font(bold=True)
    else:
        ws_income.cell(row=row, column=1, value="Bu dönemde gelir faturası bulunmuyor.")
    
    # Adjust column widths
    for col in range(1, 10):
        ws_income.column_dimensions[chr(64 + col)].width = 15
    
    # ============================================
    # SHEET 2: Gider Faturaları
    # ============================================
    ws_expense = wb.create_sheet(title="Gider Faturaları")
    
    row = 1
    if session:
        ws_expense[f'A{row}'] = f"{taxpayer_name} - {month_name} {year} - Gider Faturaları"
        ws_expense[f'A{row}'].font = Font(bold=True, size=16, color="004D40")
        ws_expense.merge_cells(start_row=row, start_column=1, end_row=row, end_column=9)
        row += 2
    
    if expense_invoices:
        headers = ["Fatura No", "Tarih", "Düzenleyen", "Düzenleyen VKN", "D. V.Dairesi", "Açıklama", "Net Tutar", "KDV", "Toplam"]
        for col, header in enumerate(headers, 1):
            cell = ws_expense.cell(row=row, column=col, value=header)
            cell.fill = header_fill
            cell.font = header_font
        row += 1
        
        expense_total_net = 0
        expense_total_vat = 0
        expense_total = 0
        for inv in expense_invoices:
            net = float(inv.get('amount', 0) or 0)
            vat = float(inv.get('vat', 0) or 0)
            total = float(inv.get('total', 0) or 0)
            expense_total_net += net
            expense_total_vat += vat
            expense_total += total
            
            row_data = [
                inv.get('invoice_number', ''), inv.get('date', ''),
                inv.get('issuer_name', ''), inv.get('issuer_tax_id', ''),
                inv.get('issuer_tax_office', ''), inv.get('description', ''),
                net, vat, total
            ]
            for col, value in enumerate(row_data, 1):
                cell = ws_expense.cell(row=row, column=col, value=value)
                if col in [7, 8, 9]:
                    cell.number_format = number_format
            row += 1
        
        # Totals row
        ws_expense.cell(row=row, column=6, value="TOPLAM:").font = Font(bold=True)
        ws_expense.cell(row=row, column=7, value=expense_total_net).number_format = number_format
        ws_expense.cell(row=row, column=7).font = Font(bold=True)
        ws_expense.cell(row=row, column=8, value=expense_total_vat).number_format = number_format
        ws_expense.cell(row=row, column=8).font = Font(bold=True)
        ws_expense.cell(row=row, column=9, value=expense_total).number_format = number_format
        ws_expense.cell(row=row, column=9).font = Font(bold=True)
    else:
        ws_expense.cell(row=row, column=1, value="Bu dönemde gider faturası bulunmuyor.")
    
    for col in range(1, 10):
        ws_expense.column_dimensions[chr(64 + col)].width = 15
    
    # ============================================
    # Collect VAT items for KDV sheets
    # ============================================
    vat_items = []
    for invoice in invoices:
        vat_details = invoice.get('vat_details', [])
        if not vat_details:
            vat_amount = float(invoice.get('vat', 0) or 0)
            net_amount = float(invoice.get('amount', 0) or 0)
            if vat_amount > 0 and net_amount > 0:
                vat_rate = round((vat_amount / net_amount) * 100)
                if vat_rate not in [1, 10, 20]:
                    vat_rate = 20
                vat_details = [{"vat_rate": vat_rate, "base_amount": net_amount, "vat_amount": vat_amount}]
        
        for detail in vat_details:
            vat_items.append({
                "invoice_number": invoice.get('invoice_number', 'N/A'),
                "date": invoice.get('date', ''),
                "category": invoice.get('category', 'income'),
                "issuer_name": invoice.get('issuer_name', ''),
                "issuer_tax_id": invoice.get('issuer_tax_id', ''),
                "issuer_tax_office": invoice.get('issuer_tax_office', ''),
                "customer_name": invoice.get('customer_name', ''),
                "customer_tax_id": invoice.get('customer_tax_id', ''),
                "customer_tax_office": invoice.get('customer_tax_office', ''),
                "description": invoice.get('description', ''),
                "vat_rate": int(detail.get('vat_rate', 20)),
                "base_amount": float(detail.get('base_amount', 0) or 0),
                "vat_amount": float(detail.get('vat_amount', 0) or 0)
            })
    
    income_vat_items = [i for i in vat_items if i['category'] == 'income']
    expense_vat_items = [i for i in vat_items if i['category'] == 'expense']
    
    # ============================================
    # SHEET 3: KDV Detay - Gelir
    # ============================================
    ws_kdv_income = wb.create_sheet(title="KDV Detay - Gelir")
    
    row = 1
    if session:
        ws_kdv_income[f'A{row}'] = f"{taxpayer_name} - {month_name} {year} - KDV Detay (Gelir)"
        ws_kdv_income[f'A{row}'].font = Font(bold=True, size=16, color="004D40")
        ws_kdv_income.merge_cells(start_row=row, start_column=1, end_row=row, end_column=9)
        row += 2
    
    if income_vat_items:
        headers = ["Fatura No", "Tarih", "Müşteri", "M. VKN", "M. V.Dairesi", "Açıklama", "KDV %", "Matrah", "KDV Tutarı"]
        for col, header in enumerate(headers, 1):
            cell = ws_kdv_income.cell(row=row, column=col, value=header)
            cell.fill = header_fill
            cell.font = header_font
        row += 1
        
        total_base = 0
        total_vat = 0
        for item in income_vat_items:
            row_data = [
                item['invoice_number'], item['date'], item['customer_name'] or '-',
                item['customer_tax_id'] or '-', item['customer_tax_office'] or '-',
                item['description'], f"%{item['vat_rate']}", item['base_amount'], item['vat_amount']
            ]
            for col, value in enumerate(row_data, 1):
                cell = ws_kdv_income.cell(row=row, column=col, value=value)
                if col in [8, 9]:
                    cell.number_format = number_format
            total_base += item['base_amount']
            total_vat += item['vat_amount']
            row += 1
        
        ws_kdv_income.cell(row=row, column=7, value="TOPLAM:").font = Font(bold=True)
        ws_kdv_income.cell(row=row, column=8, value=total_base).number_format = number_format
        ws_kdv_income.cell(row=row, column=8).font = Font(bold=True)
        ws_kdv_income.cell(row=row, column=9, value=total_vat).number_format = number_format
        ws_kdv_income.cell(row=row, column=9).font = Font(bold=True)
    else:
        ws_kdv_income.cell(row=row, column=1, value="Bu dönemde gelir KDV kaydı bulunmuyor.")
    
    for col in range(1, 10):
        ws_kdv_income.column_dimensions[chr(64 + col)].width = 15
    
    # ============================================
    # SHEET 4: KDV Detay - Gider
    # ============================================
    ws_kdv_expense = wb.create_sheet(title="KDV Detay - Gider")
    
    row = 1
    if session:
        ws_kdv_expense[f'A{row}'] = f"{taxpayer_name} - {month_name} {year} - KDV Detay (Gider)"
        ws_kdv_expense[f'A{row}'].font = Font(bold=True, size=16, color="004D40")
        ws_kdv_expense.merge_cells(start_row=row, start_column=1, end_row=row, end_column=9)
        row += 2
    
    if expense_vat_items:
        headers = ["Fatura No", "Tarih", "Düzenleyen", "D. VKN", "D. V.Dairesi", "Açıklama", "KDV %", "Matrah", "KDV Tutarı"]
        for col, header in enumerate(headers, 1):
            cell = ws_kdv_expense.cell(row=row, column=col, value=header)
            cell.fill = header_fill
            cell.font = header_font
        row += 1
        
        total_base = 0
        total_vat = 0
        for item in expense_vat_items:
            row_data = [
                item['invoice_number'], item['date'], item['issuer_name'] or '-',
                item['issuer_tax_id'] or '-', item['issuer_tax_office'] or '-',
                item['description'], f"%{item['vat_rate']}", item['base_amount'], item['vat_amount']
            ]
            for col, value in enumerate(row_data, 1):
                cell = ws_kdv_expense.cell(row=row, column=col, value=value)
                if col in [8, 9]:
                    cell.number_format = number_format
            total_base += item['base_amount']
            total_vat += item['vat_amount']
            row += 1
        
        ws_kdv_expense.cell(row=row, column=7, value="TOPLAM:").font = Font(bold=True)
        ws_kdv_expense.cell(row=row, column=8, value=total_base).number_format = number_format
        ws_kdv_expense.cell(row=row, column=8).font = Font(bold=True)
        ws_kdv_expense.cell(row=row, column=9, value=total_vat).number_format = number_format
        ws_kdv_expense.cell(row=row, column=9).font = Font(bold=True)
    else:
        ws_kdv_expense.cell(row=row, column=1, value="Bu dönemde gider KDV kaydı bulunmuyor.")
    
    # Calculate totals for summary sheets
    grand_income_base = 0
    grand_income_vat = 0
    grand_expense_base = 0
    grand_expense_vat = 0
    
    for rate in [1, 10, 20]:
        grand_income_base += sum(i['base_amount'] for i in income_vat_items if i['vat_rate'] == rate)
        grand_income_vat += sum(i['vat_amount'] for i in income_vat_items if i['vat_rate'] == rate)
        grand_expense_base += sum(i['base_amount'] for i in expense_vat_items if i['vat_rate'] == rate)
        grand_expense_vat += sum(i['vat_amount'] for i in expense_vat_items if i['vat_rate'] == rate)
    
    # ============================================
    # SHEET 5: KDV Özet - Gelir
    # ============================================
    ws_kdv_sum_income = wb.create_sheet(title="KDV Özet - Gelir")
    
    row = 1
    if session:
        ws_kdv_sum_income[f'A{row}'] = f"{taxpayer_name} - {month_name} {year} - KDV Özet (Gelir)"
        ws_kdv_sum_income[f'A{row}'].font = Font(bold=True, size=16, color="004D40")
        ws_kdv_sum_income.merge_cells(start_row=row, start_column=1, end_row=row, end_column=3)
        row += 2
    
    headers = ["KDV Oranı", "Matrah", "KDV Tutarı"]
    for col, header in enumerate(headers, 1):
        cell = ws_kdv_sum_income.cell(row=row, column=col, value=header)
        cell.fill = header_fill
        cell.font = header_font
    row += 1
    
    for rate in [1, 10, 20]:
        i_base = sum(i['base_amount'] for i in income_vat_items if i['vat_rate'] == rate)
        i_vat = sum(i['vat_amount'] for i in income_vat_items if i['vat_rate'] == rate)
        ws_kdv_sum_income.cell(row=row, column=1, value=f"%{rate}")
        ws_kdv_sum_income.cell(row=row, column=2, value=i_base).number_format = number_format
        ws_kdv_sum_income.cell(row=row, column=3, value=i_vat).number_format = number_format
        row += 1
    
    ws_kdv_sum_income.cell(row=row, column=1, value="TOPLAM").font = Font(bold=True)
    ws_kdv_sum_income.cell(row=row, column=2, value=grand_income_base).number_format = number_format
    ws_kdv_sum_income.cell(row=row, column=2).font = Font(bold=True)
    ws_kdv_sum_income.cell(row=row, column=3, value=grand_income_vat).number_format = number_format
    ws_kdv_sum_income.cell(row=row, column=3).font = Font(bold=True)
    
    # ============================================
    # SHEET 6: KDV Özet - Gider
    # ============================================
    ws_kdv_sum_expense = wb.create_sheet(title="KDV Özet - Gider")
    
    row = 1
    if session:
        ws_kdv_sum_expense[f'A{row}'] = f"{taxpayer_name} - {month_name} {year} - KDV Özet (Gider)"
        ws_kdv_sum_expense[f'A{row}'].font = Font(bold=True, size=16, color="004D40")
        ws_kdv_sum_expense.merge_cells(start_row=row, start_column=1, end_row=row, end_column=3)
        row += 2
    
    headers = ["KDV Oranı", "Matrah", "KDV Tutarı"]
    for col, header in enumerate(headers, 1):
        cell = ws_kdv_sum_expense.cell(row=row, column=col, value=header)
        cell.fill = header_fill
        cell.font = header_font
    row += 1
    
    for rate in [1, 10, 20]:
        e_base = sum(i['base_amount'] for i in expense_vat_items if i['vat_rate'] == rate)
        e_vat = sum(i['vat_amount'] for i in expense_vat_items if i['vat_rate'] == rate)
        ws_kdv_sum_expense.cell(row=row, column=1, value=f"%{rate}")
        ws_kdv_sum_expense.cell(row=row, column=2, value=e_base).number_format = number_format
        ws_kdv_sum_expense.cell(row=row, column=3, value=e_vat).number_format = number_format
        row += 1
    
    ws_kdv_sum_expense.cell(row=row, column=1, value="TOPLAM").font = Font(bold=True)
    ws_kdv_sum_expense.cell(row=row, column=2, value=grand_expense_base).number_format = number_format
    ws_kdv_sum_expense.cell(row=row, column=2).font = Font(bold=True)
    ws_kdv_sum_expense.cell(row=row, column=3, value=grand_expense_vat).number_format = number_format
    ws_kdv_sum_expense.cell(row=row, column=3).font = Font(bold=True)
    
    # ============================================
    # SHEET 7: KDV Özet - Net
    # ============================================
    ws_kdv_sum_net = wb.create_sheet(title="KDV Özet - Net")
    
    row = 1
    if session:
        ws_kdv_sum_net[f'A{row}'] = f"{taxpayer_name} - {month_name} {year} Dönemi - Net KDV"
        ws_kdv_sum_net[f'A{row}'].font = Font(bold=True, size=16, color="004D40")
        ws_kdv_sum_net.merge_cells(start_row=row, start_column=1, end_row=row, end_column=4)
        row += 2
    
    headers = ["KDV Oranı", "Hesaplanan KDV (Gelir)", "İndirilecek KDV (Gider)", "Net KDV"]
    for col, header in enumerate(headers, 1):
        cell = ws_kdv_sum_net.cell(row=row, column=col, value=header)
        cell.fill = header_fill
        cell.font = header_font
    row += 1
    
    for rate in [1, 10, 20]:
        i_vat = sum(i['vat_amount'] for i in income_vat_items if i['vat_rate'] == rate)
        e_vat = sum(i['vat_amount'] for i in expense_vat_items if i['vat_rate'] == rate)
        net = i_vat - e_vat
        ws_kdv_sum_net.cell(row=row, column=1, value=f"%{rate}")
        ws_kdv_sum_net.cell(row=row, column=2, value=i_vat).number_format = number_format
        ws_kdv_sum_net.cell(row=row, column=3, value=e_vat).number_format = number_format
        ws_kdv_sum_net.cell(row=row, column=4, value=net).number_format = number_format
        row += 1
    
    net_total = grand_income_vat - grand_expense_vat
    ws_kdv_sum_net.cell(row=row, column=1, value="TOPLAM").font = Font(bold=True)
    ws_kdv_sum_net.cell(row=row, column=2, value=grand_income_vat).number_format = number_format
    ws_kdv_sum_net.cell(row=row, column=2).font = Font(bold=True)
    ws_kdv_sum_net.cell(row=row, column=3, value=grand_expense_vat).number_format = number_format
    ws_kdv_sum_net.cell(row=row, column=3).font = Font(bold=True)
    ws_kdv_sum_net.cell(row=row, column=4, value=net_total).number_format = number_format
    ws_kdv_sum_net.cell(row=row, column=4).font = Font(bold=True)
    
    row += 2
    # Add result text
    result_text = "ÖDENECEK KDV" if net_total >= 0 else "SONRAKI AYA DEVREDEN KDV"
    ws_kdv_sum_net.cell(row=row, column=1, value=result_text).font = Font(bold=True, size=14)
    ws_kdv_sum_net.cell(row=row, column=2, value=abs(net_total)).number_format = number_format
    ws_kdv_sum_net.cell(row=row, column=2).font = Font(bold=True, size=14)
    
    # ============================================
    # Auto-adjust column widths for all sheets
    # ============================================
    def auto_adjust_columns(worksheet):
        for column_cells in worksheet.columns:
            max_length = 0
            column_letter = None
            for cell in column_cells:
                try:
                    if hasattr(cell, 'column_letter'):
                        column_letter = cell.column_letter
                    if cell.value:
                        cell_length = len(str(cell.value))
                        if cell_length > max_length:
                            max_length = cell_length
                except:
                    pass
            if column_letter and max_length > 0:
                adjusted_width = min(max_length + 3, 50)
                worksheet.column_dimensions[column_letter].width = adjusted_width
    
    # Apply auto-adjust to all sheets
    for sheet in wb.worksheets:
        auto_adjust_columns(sheet)
    
    # Save to BytesIO
    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    
    # Generate filename
    if session:
        turkish_map = str.maketrans('İıĞğÜüŞşÖöÇç', 'IiGgUuSsOoCc')
        safe_name = taxpayer_name.translate(turkish_map)
        safe_name = "".join(c for c in safe_name if c.isalnum() or c in (' ', '-', '_')).strip()
        safe_name = safe_name.replace(' ', '_')
        filename = f"{safe_name}_{year}_{month:02d}_tum_raporlar.xlsx"
    else:
        filename = "tum_raporlar.xlsx"
    
    from urllib.parse import quote
    encoded_filename = quote(filename)
    
    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{encoded_filename}"}
    )

# ============================================
# ADMIN API ENDPOINTS
# ============================================

@api_router.get("/admin/users")
async def admin_get_users(
    key: str,
    filter: Optional[str] = None  # all, active, expired, quota_exhausted
):
    """Admin endpoint to list all users with their subscription details"""
    if key != ADMIN_SECRET_KEY:
        raise HTTPException(status_code=403, detail="Geçersiz admin anahtarı")
    
    # Get all subscriptions
    subscriptions = await db.subscriptions.find({}, {"_id": 0}).to_list(1000)
    
    users_data = []
    now = datetime.now(timezone.utc)
    
    for sub in subscriptions:
        wix_member_id = sub.get("wix_member_id", "")
        packages = sub.get("packages", [])
        
        # Process packages
        packages_info = []
        total_remaining = 0
        has_unlimited = False
        any_active = False
        
        for pkg in packages:
            pkg_total = pkg.get("total_quota", 0)
            pkg_used = pkg.get("used_quota", 0)
            pkg_remaining = -1 if pkg_total == -1 else max(0, pkg_total - pkg_used)
            
            if pkg_total == -1:
                has_unlimited = True
            else:
                total_remaining += pkg_remaining
            
            # Check expiry
            end_date_str = pkg.get("end_date", "")
            pkg_expired = False
            if end_date_str:
                try:
                    end_date = datetime.fromisoformat(end_date_str.replace('Z', '+00:00'))
                    pkg_expired = now > end_date
                except:
                    pass
            
            is_active = not pkg_expired and (pkg_remaining > 0 or pkg_total == -1)
            if is_active:
                any_active = True
            
            packages_info.append({
                "plan_name": pkg.get("plan_name", ""),
                "total_quota": pkg_total,
                "used_quota": pkg_used,
                "remaining_quota": pkg_remaining,
                "end_date": pkg.get("end_date", ""),
                "is_expired": pkg_expired,
                "is_exhausted": pkg_remaining == 0 and pkg_total != -1,
                "is_active": is_active
            })
        
        # Legacy single plan info
        if not packages:
            plan = sub.get("plan", "trial")
            plan_info = SUBSCRIPTION_PLANS.get(plan, SUBSCRIPTION_PLANS["trial"])
            limit = plan_info["monthly_limit"]
            used = sub.get("monthly_uploads", 0)
            remaining = -1 if limit == -1 else max(0, limit - used)
            
            expires_at = sub.get("expires_at", "")
            is_expired = False
            if expires_at:
                try:
                    exp_date = datetime.fromisoformat(expires_at.replace('Z', '+00:00'))
                    is_expired = now > exp_date
                except:
                    pass
            
            any_active = not is_expired and (remaining > 0 or limit == -1)
            total_remaining = remaining
            has_unlimited = limit == -1
            
            packages_info.append({
                "plan_name": plan_info["name"],
                "total_quota": limit,
                "used_quota": used,
                "remaining_quota": remaining,
                "end_date": expires_at,
                "is_expired": is_expired,
                "is_exhausted": remaining == 0 and limit != -1,
                "is_active": any_active
            })
        
        user_data = {
            "wix_member_id": wix_member_id,
            "user_id": sub.get("user_id", ""),
            "email": sub.get("email", ""),
            "full_name": sub.get("full_name", ""),
            "packages": packages_info,
            "total_remaining": -1 if has_unlimited else total_remaining,
            "is_active": any_active,
            "is_quota_exhausted": total_remaining == 0 and not has_unlimited,
            "created_at": sub.get("created_at", ""),
            "updated_at": sub.get("updated_at", "")
        }
        
        # Apply filter
        if filter == "active" and not any_active:
            continue
        elif filter == "expired" and any_active:
            continue
        elif filter == "quota_exhausted" and (total_remaining > 0 or has_unlimited):
            continue
        
        users_data.append(user_data)
    
    return {
        "total_users": len(users_data),
        "users": users_data
    }

@api_router.delete("/admin/user/{wix_member_id}")
async def admin_delete_user(wix_member_id: str, key: str):
    """Admin endpoint to delete a specific user"""
    if key != ADMIN_SECRET_KEY:
        raise HTTPException(status_code=403, detail="Geçersiz admin anahtarı")
    
    result = await db.subscriptions.delete_one({"wix_member_id": wix_member_id})
    
    if result.deleted_count > 0:
        return {"success": True, "message": "Kullanıcı silindi"}
    else:
        raise HTTPException(status_code=404, detail="Kullanıcı bulunamadı")

@api_router.delete("/admin/users/all")
async def admin_delete_all_users(key: str):
    """Admin endpoint to delete ALL users - use with caution!"""
    if key != ADMIN_SECRET_KEY:
        raise HTTPException(status_code=403, detail="Geçersiz admin anahtarı")
    
    result = await db.subscriptions.delete_many({})
    
    return {
        "success": True, 
        "message": f"{result.deleted_count} kullanıcı silindi"
    }

@api_router.post("/admin/add-package")
async def admin_add_package(
    key: str = Form(...),
    wix_member_id: str = Form(...),
    plan: str = Form(...),
    wix_order_id: Optional[str] = Form(None)
):
    """Admin endpoint to manually add a package to a user"""
    if key != ADMIN_SECRET_KEY:
        raise HTTPException(status_code=403, detail="Geçersiz admin anahtarı")
    
    if plan not in SUBSCRIPTION_PLANS:
        raise HTTPException(status_code=400, detail="Geçersiz plan")
    
    # Check if user exists
    sub = await db.subscriptions.find_one({"wix_member_id": wix_member_id}, {"_id": 0})
    if not sub:
        raise HTTPException(status_code=404, detail="Kullanıcı bulunamadı")
    
    # Add package
    new_package = await add_package_to_user(wix_member_id, plan, wix_order_id)
    
    if new_package:
        return {"success": True, "package": new_package}
    else:
        raise HTTPException(status_code=500, detail="Paket eklenemedi")

@api_router.get("/admin/user/{wix_member_id}")
async def admin_get_user_detail(wix_member_id: str, key: str):
    """Admin endpoint to get detailed info about a specific user"""
    if key != ADMIN_SECRET_KEY:
        raise HTTPException(status_code=403, detail="Geçersiz admin anahtarı")
    
    sub = await db.subscriptions.find_one({"wix_member_id": wix_member_id}, {"_id": 0})
    if not sub:
        raise HTTPException(status_code=404, detail="Kullanıcı bulunamadı")
    
    # Get invoice count
    invoice_count = await db.invoices.count_documents({"user_id": sub.get("user_id", "")})
    
    return {
        "subscription": sub,
        "invoice_count": invoice_count
    }

# ============================================
# WIX WEBHOOK ENDPOINT
# ============================================

@api_router.post("/webhook/wix/new-order")
async def wix_new_order_webhook(
    wix_member_id: str = Form(...),
    plan: str = Form(...),
    wix_order_id: Optional[str] = Form(None),
    secret_key: str = Form(...),
    email: Optional[str] = Form(None),
    full_name: Optional[str] = Form(None)
):
    """
    Webhook endpoint called by Wix when a new subscription is purchased.
    This adds a NEW package to the user (doesn't replace existing ones).
    """
    if secret_key != ADMIN_SECRET_KEY:
        raise HTTPException(status_code=403, detail="Geçersiz anahtar")
    
    if plan not in SUBSCRIPTION_PLANS:
        raise HTTPException(status_code=400, detail="Geçersiz plan")
    
    # Check if user exists, if not create
    sub = await db.subscriptions.find_one({"wix_member_id": wix_member_id}, {"_id": 0})
    
    if not sub:
        # Create new user with this package
        user_id = f"wix_{wix_member_id}"
        new_sub = {
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "wix_member_id": wix_member_id,
            "email": email,
            "full_name": full_name,
            "plan": plan,
            "monthly_uploads": 0,
            "packages": [],
            "had_paid_plan": plan != "trial",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
        await db.subscriptions.insert_one(new_sub)
    else:
        # Update user info if provided
        update_fields = {"updated_at": datetime.now(timezone.utc).isoformat()}
        if email:
            update_fields["email"] = email
        if full_name:
            update_fields["full_name"] = full_name
        
        await db.subscriptions.update_one(
            {"wix_member_id": wix_member_id},
            {"$set": update_fields}
        )
    
    # Add new package
    new_package = await add_package_to_user(wix_member_id, plan, wix_order_id)
    
    if new_package:
        logger.info(f"New package added for {wix_member_id}: {plan}")
        return {
            "success": True,
            "message": f"Paket başarıyla eklendi: {SUBSCRIPTION_PLANS[plan]['name']}",
            "package": new_package
        }
    else:
        raise HTTPException(status_code=500, detail="Paket eklenemedi")

# Include router AFTER all endpoints are defined
app.include_router(api_router)

# CORS - read from env or use defaults
_cors_origins = os.environ.get('CORS_ORIGINS', '*')
if _cors_origins == '*':
    ALLOWED_ORIGINS = ["*"]
else:
    ALLOWED_ORIGINS = [
        "https://www.documander.com",
        "https://documander.com",
        "http://www.documander.com",
        "http://documander.com",
        "http://localhost:3000",
    ]
    # Add any custom origins from env
    for origin in _cors_origins.split(','):
        if origin.strip() and origin.strip() not in ALLOWED_ORIGINS:
            ALLOWED_ORIGINS.append(origin.strip())

app.add_middleware(
    CORSMiddleware,
    allow_credentials=False,
    allow_origins=ALLOWED_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Content-Disposition"]
)

# Middleware for security - iframe and referer check
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

# Read allowed domains from env or use defaults
_env_domains = os.environ.get('ALLOWED_DOMAINS', 'documander.com,www.documander.com')
ALLOWED_DOMAINS = [d.strip() for d in _env_domains.split(',')] + [
    "localhost:3000", 
    "localhost",
    "emergent.host",
    "finance-assist-28.emergent.host",
    "preview.emergentagent.com",
    # Wix domains
    "wix.com",
    "wixsite.com",
    "editorx.io",
    "editor.wix.com",
    "manage.wix.com"
]
# Add any emergent.host subdomain dynamically
ALLOWED_DOMAINS = list(set(ALLOWED_DOMAINS))

class SecurityMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        # Allow health check endpoints without restrictions
        if request.url.path in ["/health", "/api/health", "/api/health/db", "/"]:
            return await call_next(request)
        
        # Allow admin endpoints (they have their own key-based authentication)
        if request.url.path.startswith("/api/admin") or request.url.path.startswith("/api/webhook"):
            response = await call_next(request)
            return response
        
        # Domain check disabled - frontend iframe check is sufficient
        # API endpoints should work from anywhere when called from allowed frontend
        pass
        
        response = await call_next(request)
        # Only allow iframe from documander.com
        response.headers["X-Frame-Options"] = "ALLOW-FROM https://www.documander.com"
        response.headers["Content-Security-Policy"] = "frame-ancestors https://www.documander.com https://documander.com"
        return response

app.add_middleware(SecurityMiddleware)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Root endpoint for basic connectivity check
@app.get("/")
async def root():
    """Root endpoint"""
    return {"service": "documander-api", "status": "running"}

# Health check endpoint for deployment - MUST NOT require database
@app.get("/health")
async def health_check():
    """Health check endpoint for Kubernetes deployment - no DB dependency"""
    return {"status": "healthy", "service": "documander-api"}

@app.get("/api/health")
async def api_health_check():
    """API health check endpoint - no DB dependency for basic health"""
    return {"status": "healthy", "service": "documander-api"}

@app.get("/api/health/db")
async def api_db_health_check():
    """Database health check endpoint"""
    try:
        await db.command("ping")
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        return {"status": "unhealthy", "database": "disconnected", "error": str(e)}

@app.on_event("startup")
async def startup_event():
    """Startup event - log that app is ready"""
    logger.info("Documander API starting up...")
    logger.info("Health check available at /api/health")

@app.on_event("shutdown")
async def shutdown_db_client():
    logger.info("Documander API shutting down...")
    client.close()
