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

async def get_current_user(x_visitor_id: Optional[str] = Header(None)):
    # Get visitor ID from header for user isolation
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
        raise HTTPException(status_code=500, detail=f"AI extraction failed: {str(e)}")

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
    
    return {
        "success": len(uploaded_invoices),
        "failed": len(errors) + len(date_mismatches),
        "invoices": uploaded_invoices,
        "errors": errors,
        "date_mismatches": date_mismatches
    }

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
    
    # Helper function to format number as Turkish string (1.234,56)
    def format_turkish(num):
        formatted = f"{num:,.2f}"  # 1,234.56
        # Swap . and , for Turkish format
        formatted = formatted.replace(',', 'X').replace('.', ',').replace('X', '.')
        return formatted
    
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
                format_turkish(invoice.get('amount', 0)),
                format_turkish(invoice.get('vat', 0)),
                format_turkish(invoice.get('total', 0))
            ])
            # Right align number columns
            ws[f'G{current_row}'].alignment = Alignment(horizontal="right")
            ws[f'H{current_row}'].alignment = Alignment(horizontal="right")
            ws[f'I{current_row}'].alignment = Alignment(horizontal="right")
            current_row += 1
        
        # Add subtotal row for income
        income_amount_total = sum(inv.get('amount', 0) for inv in income_invoices)
        income_vat_total = sum(inv.get('vat', 0) for inv in income_invoices)
        income_total_total = sum(inv.get('total', 0) for inv in income_invoices)
        
        ws.append(['', '', '', '', '', 'TOPLAM:', format_turkish(income_amount_total), format_turkish(income_vat_total), format_turkish(income_total_total)])
        subtotal_fill = PatternFill(start_color="E8F5E9", end_color="E8F5E9", fill_type="solid")
        for col_idx in range(1, 10):
            cell = ws.cell(row=current_row, column=col_idx)
            cell.fill = subtotal_fill
            cell.font = Font(bold=True)
            if col_idx == 6:
                cell.alignment = Alignment(horizontal="right")
            if col_idx in [7, 8, 9]:
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
                format_turkish(invoice.get('amount', 0)),
                format_turkish(invoice.get('vat', 0)),
                format_turkish(invoice.get('total', 0))
            ])
            # Right align number columns
            ws[f'G{current_row}'].alignment = Alignment(horizontal="right")
            ws[f'H{current_row}'].alignment = Alignment(horizontal="right")
            ws[f'I{current_row}'].alignment = Alignment(horizontal="right")
            current_row += 1
        
        # Add subtotal row for expense
        expense_amount_total = sum(inv.get('amount', 0) for inv in expense_invoices)
        expense_vat_total = sum(inv.get('vat', 0) for inv in expense_invoices)
        expense_total_total = sum(inv.get('total', 0) for inv in expense_invoices)
        
        ws.append(['', '', '', '', '', 'TOPLAM:', format_turkish(expense_amount_total), format_turkish(expense_vat_total), format_turkish(expense_total_total)])
        subtotal_fill = PatternFill(start_color="E8F5E9", end_color="E8F5E9", fill_type="solid")
        for col_idx in range(1, 10):
            cell = ws.cell(row=current_row, column=col_idx)
            cell.fill = subtotal_fill
            cell.font = Font(bold=True)
            if col_idx == 6:
                cell.alignment = Alignment(horizontal="right")
            if col_idx in [7, 8, 9]:
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

# CORS for Wix embed - allow only documander.com
ALLOWED_ORIGINS = [
    "https://www.documander.com",
    "https://documander.com",
    "http://www.documander.com",
    "http://documander.com",
    "http://localhost:3000",  # For local development
]

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

ALLOWED_DOMAINS = [
    "documander.com", 
    "www.documander.com", 
    "localhost:3000", 
    "localhost",
    "ac9e1a11-9445-4f64-848e-b5dc762e0e64.emergent.host",  # Production
    "emergent.host"
]

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
            
            # No referer/origin = direct access = blocked
            # Only documander.com can access
            
            if not is_allowed:
                return JSONResponse(
                    status_code=403,
                    content={"detail": "Access denied. This application can only be accessed from documander.com"}
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

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()