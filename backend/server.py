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
from emergentintegrations.llm.chat import LlmChat, UserMessage, FileContentWithMimeType
import io
from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, PatternFill
import json

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ.get('MONGO_URL', 'mongodb://localhost:27017')
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ.get('DB_NAME', 'test_database')]

# JWT Config
JWT_SECRET = os.environ.get('JWT_SECRET', 'fatura-yonetim-secret-key-2024')
JWT_ALGORITHM = 'HS256'

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

# Subscription Plans
SUBSCRIPTION_PLANS = {
    "trial": {"name": "Deneme", "monthly_limit": 20, "price": 0},
    "starter": {"name": "Başlangıç", "monthly_limit": 1000, "price": 699},
    "professional": {"name": "Profesyonel", "monthly_limit": 2500, "price": 1399},
    "business": {"name": "İşletme", "monthly_limit": 5000, "price": 2399},
    "enterprise": {"name": "Kurumsal", "monthly_limit": 10000, "price": 3999},
    "unlimited": {"name": "Sınırsız", "monthly_limit": -1, "price": -1},  # -1 = unlimited/contact
}

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
            "month_reset": datetime.now(timezone.utc).strftime("%Y-%m"),
            "trial_used": False,
            "expires_at": trial_expires,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
        await db.subscriptions.insert_one(sub)
    
    # Check if month changed - reset counter
    current_month = datetime.now(timezone.utc).strftime("%Y-%m")
    if sub.get("month_reset") != current_month and sub.get("plan") != "trial":
        await db.subscriptions.update_one(
            {"user_id": user_id},
            {"$set": {"monthly_uploads": 0, "month_reset": current_month, "updated_at": datetime.now(timezone.utc).isoformat()}}
        )
        sub["monthly_uploads"] = 0
        sub["month_reset"] = current_month
    
    return sub

async def check_upload_limit(user_id: str, file_count: int = 1):
    """Check if user can upload more files. Returns (can_upload, message, remaining)"""
    sub = await get_or_create_subscription(user_id)
    plan = sub.get("plan", "trial")
    plan_info = SUBSCRIPTION_PLANS.get(plan, SUBSCRIPTION_PLANS["trial"])
    limit = plan_info["monthly_limit"]
    current = sub.get("monthly_uploads", 0)
    
    # Check if subscription expired (for trial)
    expires_at = sub.get("expires_at")
    if expires_at:
        try:
            exp_date = datetime.fromisoformat(expires_at.replace('Z', '+00:00'))
            if datetime.now(timezone.utc) > exp_date:
                return False, "Abonelik süreniz doldu. Devam etmek için bir plan satın alın.", 0
        except:
            pass
    
    # Check if user had paid plan before and now downgraded to trial
    # If they ever had a paid plan, they can't use trial anymore
    if plan == "trial" and sub.get("had_paid_plan", False):
        return False, "Üyeliğiniz sona erdi. Devam etmek için bir plan satın alın.", 0
    
    # Unlimited plan
    if limit == -1:
        return True, None, -1
    
    # Check trial
    if plan == "trial":
        remaining = limit - current
        if current >= limit:
            return False, "Deneme hakkınız doldu. Devam etmek için bir plan satın alın.", 0
        if current + file_count > limit:
            return False, f"Deneme hakkınız yetersiz. Kalan: {remaining}, İstenen: {file_count}", remaining
        return True, None, remaining - file_count
    
    # Check paid plans
    remaining = limit - current
    if current + file_count > limit:
        return False, f"Aylık fatura limitinize ({limit}) ulaştınız. Planınızı yükseltebilirsiniz.", remaining
    
    return True, None, remaining - file_count

async def increment_upload_count(user_id: str, count: int = 1):
    """Increment the upload counter"""
    sub = await get_or_create_subscription(user_id)
    new_count = sub.get("monthly_uploads", 0) + count
    
    update_data = {
        "monthly_uploads": new_count,
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
    
    # Mark trial as used if it's trial plan
    if sub.get("plan") == "trial":
        update_data["trial_used"] = True
    
    # Update by wix_member_id if exists, otherwise by user_id
    wix_member_id = sub.get("wix_member_id")
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
        current_month = datetime.now(timezone.utc).strftime("%Y-%m")
        
        if existing_sub:
            user_id = existing_sub.get("user_id", x_visitor_id)
            
            # ALWAYS update plan from Wix (Wix is the source of truth)
            if new_plan:
                update_data = {
                    "plan": new_plan,
                    "updated_at": datetime.now(timezone.utc).isoformat()
                }
                
                # For trial plan, set expiry from Wix
                if new_plan == "trial":
                    if x_wix_expires:
                        update_data["expires_at"] = x_wix_expires
                    elif not existing_sub.get("expires_at"):
                        update_data["expires_at"] = (datetime.now(timezone.utc) + timedelta(days=7)).isoformat()
                # For paid monthly plans, no fixed expiry
                else:
                    update_data["expires_at"] = None
                    # Mark that user had a paid plan (can't go back to trial)
                    update_data["had_paid_plan"] = True
                
                # Reset monthly counter if month changed (only for active paid plans)
                if new_plan != "trial" and existing_sub.get("month_reset") != current_month:
                    update_data["monthly_uploads"] = 0
                    update_data["month_reset"] = current_month
                
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
                expires_at = None  # No expiry for monthly paid plans
            
            new_sub = {
                "id": str(uuid.uuid4()),
                "user_id": user_id,
                "wix_member_id": x_wix_member_id,
                "plan": new_plan or "trial",
                "monthly_uploads": 0,
                "month_reset": current_month,
                "trial_used": False,
                "had_paid_plan": new_plan and new_plan != "trial",  # Mark if starting with paid plan
                "expires_at": expires_at,
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
    plan = sub.get("plan", "trial")
    plan_info = SUBSCRIPTION_PLANS.get(plan, SUBSCRIPTION_PLANS["trial"])
    
    monthly_uploads = sub.get("monthly_uploads", 0)
    limit = plan_info["monthly_limit"]
    
    # Calculate remaining
    if limit == -1:
        remaining = -1  # Unlimited
    else:
        remaining = max(0, limit - monthly_uploads)
    
    # Check expiration (only for trial plans - monthly plans have no expiry)
    expires_at = sub.get("expires_at")
    is_expired = False
    days_remaining = None
    is_monthly_plan = plan != "trial" and expires_at is None
    
    if expires_at:
        try:
            exp_date = datetime.fromisoformat(expires_at.replace('Z', '+00:00'))
            now = datetime.now(timezone.utc)
            is_expired = now > exp_date
            if not is_expired:
                days_remaining = (exp_date - now).days
        except:
            pass
    
    # For monthly plans, calculate days until quota reset
    next_reset_date = None
    if is_monthly_plan:
        created_at = sub.get("created_at")
        if created_at:
            try:
                start_date = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                now = datetime.now(timezone.utc)
                # Find next monthly anniversary
                months_passed = (now.year - start_date.year) * 12 + (now.month - start_date.month)
                next_reset = start_date.replace(year=start_date.year + (start_date.month + months_passed) // 12,
                                                 month=(start_date.month + months_passed) % 12 + 1)
                if next_reset <= now:
                    next_reset = start_date.replace(year=start_date.year + (start_date.month + months_passed + 1) // 12,
                                                     month=(start_date.month + months_passed + 1) % 12 + 1)
                next_reset_date = next_reset.isoformat()
                days_remaining = (next_reset - now).days
            except:
                pass
    
    return {
        "plan": plan,
        "plan_name": plan_info["name"],
        "monthly_limit": limit,
        "monthly_uploads": monthly_uploads,
        "remaining": remaining,
        "is_trial": plan == "trial",
        "trial_used": sub.get("trial_used", False),
        "is_unlimited": limit == -1,
        "is_monthly_plan": is_monthly_plan,
        "month_reset": sub.get("month_reset", ""),
        "wix_member_id": sub.get("wix_member_id"),
        "started_at": sub.get("created_at"),
        "expires_at": expires_at,
        "next_reset_date": next_reset_date,
        "is_expired": is_expired,
        "days_remaining": days_remaining
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
    duration_days: int = Form(30)  # Default 30 days (1 month)
):
    """
    Admin endpoint to activate subscription after Wix payment.
    Called manually or via Wix Webhook when payment is confirmed.
    
    duration_days: Subscription duration in days (30=1 month, 365=1 year)
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
    try:
        # Save temporary file
        temp_dir = Path("/tmp/invoices")
        temp_dir.mkdir(exist_ok=True)
        temp_file_path = temp_dir / file_name
        
        with open(temp_file_path, "wb") as f:
            f.write(file_content)
        
        # Initialize LLM Chat with Gemini (supports file attachments)
        chat = LlmChat(
            api_key=EMERGENT_LLM_KEY,
            session_id=f"invoice-extraction-{uuid.uuid4()}",
            system_message="You are an invoice data extraction assistant. Extract invoice information accurately."
        ).with_model("gemini", "gemini-2.5-flash")
        
        # Create file content object
        file_obj = FileContentWithMimeType(
            file_path=str(temp_file_path),
            mime_type=mime_type
        )
        
        # Extract data
        prompt = """Bu faturadan şu bilgileri çıkar ve JSON formatında döndür:
- invoice_number: Fatura numarası
- date: Fatura tarihi (GG/AA/YYYY formatında)
- issuer_name: Faturayı düzenleyen firma/kişi adı
- issuer_tax_id: Faturayı düzenleyen firmanın vergi kimlik numarası (TCKN veya VKN)
- issuer_tax_office: Faturayı düzenleyen firmanın vergi dairesi (SADECE vergi dairesi adı, BÜYÜK HARFLERLE, "VERGİ DAİRESİ", "V.D.", "MÜD." gibi ekler OLMADAN. Örnek: "ERENKÖY VERGİ DAİRESİ MÜD." yerine sadece "ERENKÖY" yaz)
- customer_name: Müşteri adı (faturanın kesildiği kişi/firma)
- customer_tax_id: Müşterinin vergi kimlik numarası (TCKN veya VKN)
- customer_tax_office: Müşterinin vergi dairesi (SADECE vergi dairesi adı, BÜYÜK HARFLERLE, "VERGİ DAİRESİ", "V.D.", "MÜD." gibi ekler OLMADAN. Örnek: "KADIKÖY VERGİ DAİRESİ" yerine sadece "KADIKÖY" yaz)
- description: Fatura içeriğinin ÇOK KISA özeti (maksimum 3-5 kelime, sadece ana konu)
- amount: Net tutar (sadece sayı)
- vat: KDV tutarı (sadece sayı)
- total: Toplam tutar (sadece sayı)

Sadece JSON formatında yanıt ver, başka açıklama ekleme.
Örnek: {"invoice_number": "INV-2024-001", "date": "15/01/2024", "issuer_name": "ABC Ltd.", "issuer_tax_id": "1234567890", "issuer_tax_office": "KADIKÖY", "customer_name": "XYZ A.Ş.", "customer_tax_id": "9876543210", "customer_tax_office": "BEŞİKTAŞ", "description": "Yazılım danışmanlık", "amount": 1000.0, "vat": 180.0, "total": 1180.0}"""
        
        message = UserMessage(
            text=prompt,
            file_contents=[file_obj]
        )
        
        response = await chat.send_message(message)
        
        # Clean up temp file
        temp_file_path.unlink(missing_ok=True)
        
        # Parse response
        response_text = response.strip()
        if response_text.startswith("```json"):
            response_text = response_text[7:]
        if response_text.startswith("```"):
            response_text = response_text[3:]
        if response_text.endswith("```"):
            response_text = response_text[:-3]
        response_text = response_text.strip()
        
        data = json.loads(response_text)
        return data
    except Exception as e:
        logging.error(f"AI extraction error: {str(e)}")
        raise HTTPException(status_code=500, detail="Fatura verisi okunamadı. Lütfen tekrar deneyin.")

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
    
    # Check subscription limit BEFORE processing files
    can_upload, limit_msg, remaining = await check_upload_limit(user_id, len(files))
    if not can_upload:
        raise HTTPException(status_code=403, detail=limit_msg)
    
    # Warn if remaining is low
    quota_warning = None
    if remaining != -1 and remaining <= 5:
        quota_warning = f"Dikkat: Kalan fatura hakkınız: {remaining}"
    
    allowed_types = ['application/pdf', 'image/jpeg', 'image/jpg', 'image/png', 'text/xml', 'application/xml', 'text/html']
    uploaded_invoices = []
    errors = []
    date_mismatches = []
    
    for file in files:
        try:
            # Validate file type
            if file.content_type not in allowed_types:
                errors.append(f"{file.filename}: Invalid file type")
                continue
            
            # Read file
            file_content = await file.read()
            
            # Extract data with AI
            mime_type = file.content_type
            if mime_type == 'image/jpg':
                mime_type = 'image/jpeg'
            
            extracted_data = await extract_invoice_data_with_ai(file_content, file.filename, mime_type)
            
            # Validate invoice date against session period
            invoice_date = extracted_data.get('date', '') or ''
            is_valid, error_msg = validate_invoice_date(invoice_date, session['year'], session['month'])
            
            if not is_valid:
                date_mismatches.append(f"{file.filename}: {error_msg}")
                continue
            
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
                file_type=file.content_type
            )
            
            invoice_dict = invoice.model_dump()
            invoice_dict['created_at'] = invoice_dict['created_at'].isoformat()
            
            await db.invoices.insert_one(invoice_dict)
            uploaded_invoices.append(invoice)
            
        except Exception as e:
            errors.append(f"{file.filename}: {str(e)}")
    
    # Increment upload counter for successfully processed invoices
    if len(uploaded_invoices) > 0:
        await increment_upload_count(user_id, len(uploaded_invoices))
    
    # Get updated quota info
    _, _, new_remaining = await check_upload_limit(user_id)
    
    response_data = {
        "success": len(uploaded_invoices),
        "failed": len(errors) + len(date_mismatches),
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
    
    income_invoices.sort(key=lambda x: parse_date(x.get('date', '')), reverse=False)  # Oldest first
    expense_invoices.sort(key=lambda x: parse_date(x.get('date', '')), reverse=False)  # Oldest first
    
    # Turkish month names
    month_names = {
        1: 'Ocak', 2: 'Şubat', 3: 'Mart', 4: 'Nisan', 5: 'Mayıs', 6: 'Haziran',
        7: 'Temmuz', 8: 'Ağustos', 9: 'Eylül', 10: 'Ekim', 11: 'Kasım', 12: 'Aralık'
    }
    
    # Create Excel workbook
    wb = Workbook()
    ws = wb.active
    ws.title = "Faturalar"
    
    current_row = 1
    
    # Define common styles for headers
    header_fill = PatternFill(start_color="004D40", end_color="004D40", fill_type="solid")
    header_font = Font(bold=True, color="FFFFFF")
    
    # Numbers are now formatted using Excel's built-in number format
    # Number format for Turkish locale (will show as 1.234,56 in Turkish Excel)
    number_format = '#,##0.00'
    
    # Add main title with taxpayer info if session exists
    if session:
        taxpayer_name = session.get('taxpayer_name', '')
        year = session.get('year', '')
        month = session.get('month', '')
        month_name = month_names.get(month, '')
        main_title = f"{taxpayer_name} - {month_name} {year}"
        ws[f'A{current_row}'] = main_title
        ws[f'A{current_row}'].font = Font(bold=True, size=16, color="004D40")
        ws.merge_cells(start_row=current_row, start_column=1, end_row=current_row, end_column=9)
        current_row += 2
    
    # INCOME INVOICES SECTION
    if income_invoices:
        # Section title
        ws[f'A{current_row}'] = 'GELİR FATURALARI'
        ws[f'A{current_row}'].font = Font(bold=True, size=14, color="004D40")
        current_row += 1
        
        # Headers for income
        income_headers = [
            "Fatura No", "Tarih", "Müşteri", "Müşteri VKN", "Müşteri V.Dairesi",
            "Açıklama", "Net Tutar", "KDV", "Toplam"
        ]
        ws.append(income_headers)
        header_row = current_row
        current_row += 1
        
        # Style headers
        for col_idx, _ in enumerate(income_headers, 1):
            cell = ws.cell(row=header_row, column=col_idx)
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = Alignment(horizontal="center")
        
        # Add income data
        for invoice in income_invoices:
            ws.append([
                invoice.get('invoice_number', ''),
                invoice.get('date', ''),
                invoice.get('customer_name', ''),
                invoice.get('customer_tax_id', ''),
                invoice.get('customer_tax_office', ''),
                invoice.get('description', ''),
                float(invoice.get('amount', 0) or 0),
                float(invoice.get('vat', 0) or 0),
                float(invoice.get('total', 0) or 0)
            ])
            # Apply number format and alignment
            ws[f'G{current_row}'].number_format = number_format
            ws[f'H{current_row}'].number_format = number_format
            ws[f'I{current_row}'].number_format = number_format
            ws[f'G{current_row}'].alignment = Alignment(horizontal="right")
            ws[f'H{current_row}'].alignment = Alignment(horizontal="right")
            ws[f'I{current_row}'].alignment = Alignment(horizontal="right")
            current_row += 1
        
        # Add subtotal row for income
        income_amount_total = sum(float(inv.get('amount', 0) or 0) for inv in income_invoices)
        income_vat_total = sum(float(inv.get('vat', 0) or 0) for inv in income_invoices)
        income_total_total = sum(float(inv.get('total', 0) or 0) for inv in income_invoices)
        
        ws.append(['', '', '', '', '', 'TOPLAM:', income_amount_total, income_vat_total, income_total_total])
        subtotal_fill = PatternFill(start_color="E8F5E9", end_color="E8F5E9", fill_type="solid")
        for col_idx in range(1, 10):
            cell = ws.cell(row=current_row, column=col_idx)
            cell.fill = subtotal_fill
            cell.font = Font(bold=True)
            if col_idx == 6:
                cell.alignment = Alignment(horizontal="right")
            if col_idx in [7, 8, 9]:
                cell.number_format = number_format
                cell.alignment = Alignment(horizontal="right")
        current_row += 1
        
        current_row += 2  # Empty rows between sections
    
    # EXPENSE INVOICES SECTION
    if expense_invoices:
        # Section title
        ws[f'A{current_row}'] = 'GİDER FATURALARI'
        ws[f'A{current_row}'].font = Font(bold=True, size=14, color="004D40")
        current_row += 1
        
        # Headers for expense
        expense_headers = [
            "Fatura No", "Tarih", "Düzenleyen", "Düzenleyen VKN", "Düzenleyen V.Dairesi",
            "Açıklama", "Net Tutar", "KDV", "Toplam"
        ]
        ws.append(expense_headers)
        header_row = current_row
        current_row += 1
        
        # Style headers
        for col_idx, _ in enumerate(expense_headers, 1):
            cell = ws.cell(row=header_row, column=col_idx)
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = Alignment(horizontal="center")
        
        # Add expense data
        for invoice in expense_invoices:
            ws.append([
                invoice.get('invoice_number', ''),
                invoice.get('date', ''),
                invoice.get('issuer_name', ''),
                invoice.get('issuer_tax_id', ''),
                invoice.get('issuer_tax_office', ''),
                invoice.get('description', ''),
                float(invoice.get('amount', 0) or 0),
                float(invoice.get('vat', 0) or 0),
                float(invoice.get('total', 0) or 0)
            ])
            # Apply number format and alignment
            ws[f'G{current_row}'].number_format = number_format
            ws[f'H{current_row}'].number_format = number_format
            ws[f'I{current_row}'].number_format = number_format
            ws[f'G{current_row}'].alignment = Alignment(horizontal="right")
            ws[f'H{current_row}'].alignment = Alignment(horizontal="right")
            ws[f'I{current_row}'].alignment = Alignment(horizontal="right")
            current_row += 1
        
        # Add subtotal row for expense
        expense_amount_total = sum(float(inv.get('amount', 0) or 0) for inv in expense_invoices)
        expense_vat_total = sum(float(inv.get('vat', 0) or 0) for inv in expense_invoices)
        expense_total_total = sum(float(inv.get('total', 0) or 0) for inv in expense_invoices)
        
        ws.append(['', '', '', '', '', 'TOPLAM:', expense_amount_total, expense_vat_total, expense_total_total])
        subtotal_fill = PatternFill(start_color="E8F5E9", end_color="E8F5E9", fill_type="solid")
        for col_idx in range(1, 10):
            cell = ws.cell(row=current_row, column=col_idx)
            cell.fill = subtotal_fill
            cell.font = Font(bold=True)
            if col_idx == 6:
                cell.alignment = Alignment(horizontal="right")
            if col_idx in [7, 8, 9]:
                cell.number_format = number_format
                cell.alignment = Alignment(horizontal="right")
        current_row += 1
    
    # Auto-adjust column widths (skip merged cells)
    from openpyxl.cell.cell import MergedCell
    for column in ws.columns:
        max_length = 0
        column_letter = None
        for cell in column:
            # Skip merged cells
            if isinstance(cell, MergedCell):
                continue
            if column_letter is None:
                column_letter = cell.column_letter
            try:
                if cell.value and len(str(cell.value)) > max_length:
                    max_length = len(str(cell.value))
            except:
                pass
        if column_letter:
            adjusted_width = min(max_length + 2, 50)
            ws.column_dimensions[column_letter].width = adjusted_width
    
    # Save to BytesIO
    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    
    # Generate filename based on session info and category
    category_name = "tumu"
    if category == 'income':
        category_name = "gelir"
    elif category == 'expense':
        category_name = "gider"
    
    if session:
        taxpayer_name = session.get('taxpayer_name', 'faturalar')
        # Clean taxpayer name for filename - convert Turkish chars to ASCII
        turkish_map = str.maketrans('İıĞğÜüŞşÖöÇç', 'IiGgUuSsOoCc')
        safe_name = taxpayer_name.translate(turkish_map)
        safe_name = "".join(c for c in safe_name if c.isalnum() or c in (' ', '-', '_')).strip()
        safe_name = safe_name.replace(' ', '_')
        year = session.get('year', '')
        month = session.get('month', 1)
        filename = f"{safe_name}_{year}_{month:02d}_{category_name}.xlsx"
    else:
        filename = f"faturalar_{category_name}.xlsx"
    
    # URL encode filename for Content-Disposition header (RFC 5987)
    from urllib.parse import quote
    encoded_filename = quote(filename)
    
    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{encoded_filename}"}
    )

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
        # Check referer/origin for API calls
        if request.url.path.startswith("/api"):
            referer = request.headers.get("referer", "")
            origin = request.headers.get("origin", "")
            
            # Allow if referer or origin is from allowed domains
            is_allowed = False
            for domain in ALLOWED_DOMAINS:
                if domain in referer or domain in origin:
                    is_allowed = True
                    break
            
            if not is_allowed:
                return JSONResponse(
                    status_code=403,
                    content={"detail": "Bu uygulamaya sadece documander.com üzerinden erişilebilir."}
                )
        
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

# Health check endpoint for deployment
@app.get("/health")
async def health_check():
    """Health check endpoint for Kubernetes deployment"""
    return {"status": "healthy", "service": "documander-api"}

@app.get("/api/health")
async def api_health_check():
    """API health check endpoint"""
    try:
        # Check MongoDB connection
        await db.command("ping")
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        return {"status": "unhealthy", "database": "disconnected", "error": str(e)}

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()