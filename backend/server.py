from fastapi import FastAPI, APIRouter, HTTPException, Depends, UploadFile, File, Form
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

class Invoice(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
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

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
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
- issuer_tax_office: Faturayı düzenleyen firmanın vergi dairesi
- customer_name: Müşteri adı (faturanın kesildiği kişi/firma)
- customer_tax_id: Müşterinin vergi kimlik numarası (TCKN veya VKN)
- customer_tax_office: Müşterinin vergi dairesi
- description: Fatura içeriğinin kısa özeti (ürün/hizmet açıklaması, max 50 kelime)
- amount: Net tutar (sadece sayı)
- vat: KDV tutarı (sadece sayı)
- total: Toplam tutar (sadece sayı)

Sadece JSON formatında yanıt ver, başka açıklama ekleme.
Örnek: {"invoice_number": "INV-2024-001", "date": "15/01/2024", "issuer_name": "ABC Ltd.", "issuer_tax_id": "1234567890", "issuer_tax_office": "Kadıköy", "customer_name": "XYZ A.Ş.", "customer_tax_id": "9876543210", "customer_tax_office": "Beşiktaş", "description": "Yazılım geliştirme hizmetleri, danışmanlık", "amount": 1000.0, "vat": 180.0, "total": 1180.0}"""
        
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
        raise HTTPException(status_code=500, detail=f"AI extraction failed: {str(e)}")

# Helper function for safe float conversion
def safe_float(value, default=0.0):
    try:
        if value is None:
            return default
        return float(value)
    except (ValueError, TypeError):
        return default

# Invoice Routes
@api_router.post("/invoices/upload")
async def upload_invoice(
    files: List[UploadFile] = File(...),
    user_id: str = Depends(get_current_user)
):
    allowed_types = ['application/pdf', 'image/jpeg', 'image/jpg', 'image/png', 'text/xml', 'application/xml']
    uploaded_invoices = []
    errors = []
    
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
            
            # Create invoice
            invoice = Invoice(
                user_id=user_id,
                invoice_number=extracted_data.get('invoice_number', 'N/A') or 'N/A',
                date=extracted_data.get('date', '') or '',
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
    
    return {
        "success": len(uploaded_invoices),
        "failed": len(errors),
        "invoices": uploaded_invoices,
        "errors": errors
    }

@api_router.get("/invoices", response_model=List[Invoice])
async def get_invoices(user_id: str = Depends(get_current_user)):
    invoices = await db.invoices.find({"user_id": user_id}, {"_id": 0}).to_list(1000)
    
    for invoice in invoices:
        if isinstance(invoice['created_at'], str):
            invoice['created_at'] = datetime.fromisoformat(invoice['created_at'])
        
        # Add missing fields for backward compatibility
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

@api_router.get("/invoices/export/excel")
async def export_to_excel(user_id: str = Depends(get_current_user)):
    invoices = await db.invoices.find({"user_id": user_id}, {"_id": 0}).to_list(1000)
    
    if not invoices:
        raise HTTPException(status_code=404, detail="No invoices found")
    
    # Create Excel workbook
    wb = Workbook()
    ws = wb.active
    ws.title = "Faturalar"
    
    # Headers
    headers = [
        "Fatura No", "Tarih", 
        "Düzenleyen", "Düzenleyen VKN", "Düzenleyen V.Dairesi",
        "Müşteri", "Müşteri VKN", "Müşteri V.Dairesi",
        "Net Tutar", "KDV", "Toplam"
    ]
    ws.append(headers)
    
    # Style headers
    header_fill = PatternFill(start_color="004D40", end_color="004D40", fill_type="solid")
    header_font = Font(bold=True, color="FFFFFF")
    
    for cell in ws[1]:
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center")
    
    # Add data
    for invoice in invoices:
        ws.append([
            invoice.get('invoice_number', ''),
            invoice.get('date', ''),
            invoice.get('issuer_name', ''),
            invoice.get('issuer_tax_id', ''),
            invoice.get('issuer_tax_office', ''),
            invoice.get('customer_name', ''),
            invoice.get('customer_tax_id', ''),
            invoice.get('customer_tax_office', ''),
            invoice.get('amount', 0),
            invoice.get('vat', 0),
            invoice.get('total', 0)
        ])
    
    # Auto-adjust column widths
    for column in ws.columns:
        max_length = 0
        column_letter = column[0].column_letter
        for cell in column:
            try:
                if len(str(cell.value)) > max_length:
                    max_length = len(cell.value)
            except:
                pass
        adjusted_width = min(max_length + 2, 50)
        ws.column_dimensions[column_letter].width = adjusted_width
    
    # Save to BytesIO
    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    
    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=faturalar.xlsx"}
    )

app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()