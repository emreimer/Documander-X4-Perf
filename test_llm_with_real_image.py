#!/usr/bin/env python3
"""
Test the LLM with the actual converted PDF image
"""

import sys
import os
import asyncio
import json
import base64
from pathlib import Path
from io import BytesIO

# Add backend to path
sys.path.append('/app/backend')

# Set up environment
os.chdir('/app/backend')
from dotenv import load_dotenv

# Load environment variables
ROOT_DIR = Path('/app/backend')
load_dotenv(ROOT_DIR / '.env')

async def test_llm_with_real_image():
    """Test LLM with the actual converted PDF image"""
    
    try:
        from emergentintegrations.llm.chat import LlmChat, UserMessage, ImageContent
        from pdf2image import convert_from_bytes
        import uuid
        
        # Get the LLM key
        EMERGENT_LLM_KEY = os.environ.get('EMERGENT_LLM_KEY', '')
        print(f"🔑 EMERGENT_LLM_KEY configured: {bool(EMERGENT_LLM_KEY)}")
        
        if not EMERGENT_LLM_KEY:
            print("❌ No EMERGENT_LLM_KEY found!")
            return False
        
        # Create the same test PDF as in the upload test
        pdf_content = b"""%PDF-1.4
1 0 obj
<<
/Type /Catalog
/Pages 2 0 R
>>
endobj

2 0 obj
<<
/Type /Pages
/Kids [3 0 R]
/Count 1
>>
endobj

3 0 obj
<<
/Type /Page
/Parent 2 0 R
/MediaBox [0 0 612 792]
/Contents 4 0 R
>>
endobj

4 0 obj
<<
/Length 300
>>
stream
BT
/F1 12 Tf
50 750 Td
(FATURA / INVOICE) Tj
0 -20 Td
(Fatura No: INV-2025-001) Tj
0 -20 Td
(Tarih: 15/01/2025) Tj
0 -40 Td
(Satici: Test Firma A.S.) Tj
0 -20 Td
(Vergi No: 1234567890) Tj
0 -20 Td
(Vergi Dairesi: KADIKOY) Tj
0 -40 Td
(Musteri: Test Musteri Ltd.) Tj
0 -20 Td
(Musteri VKN: 0987654321) Tj
0 -40 Td
(Aciklama: Test urun satisi) Tj
0 -20 Td
(Tutar: 1000.00 TL) Tj
0 -20 Td
(KDV: 200.00 TL) Tj
0 -20 Td
(Toplam: 1200.00 TL) Tj
ET
endstream
endobj

xref
0 5
0000000000 65535 f 
0000000009 00000 n 
0000000058 00000 n 
0000000115 00000 n 
0000000206 00000 n 
trailer
<<
/Size 5
/Root 1 0 R
>>
startxref
556
%%EOF"""
        
        print("📄 Converting PDF to image...")
        
        # Convert PDF to images (same as in the backend)
        images = convert_from_bytes(pdf_content, dpi=150, first_page=1, last_page=3)
        
        if not images:
            print("❌ No images generated from PDF")
            return False
        
        # Process first image (same as in backend)
        img = images[0]
        img_buffer = BytesIO()
        img.save(img_buffer, format='PNG')
        img_buffer.seek(0)
        image_base64 = base64.b64encode(img_buffer.read()).decode('utf-8')
        
        print(f"✅ Image converted. Size: {img.size}, Base64 length: {len(image_base64)}")
        
        # Create image content object
        image_obj = ImageContent(image_base64=image_base64)
        
        # Initialize LLM Chat
        chat = LlmChat(
            api_key=EMERGENT_LLM_KEY,
            session_id=f"test-extraction-{uuid.uuid4()}",
            system_message="You are an invoice data extraction assistant. Extract invoice information accurately from Turkish invoices and receipts."
        ).with_model("openai", "gpt-4o")
        
        print("✅ LLM Chat initialized successfully")
        
        # Use the same prompt as in the backend
        prompt = """Bu görseli analiz et. Eğer birden fazla fiş/fatura varsa HER BİRİNİ AYRI AYRI çıkar.

Her fiş/fatura için şu bilgileri çıkar:
- invoice_number: Fatura/fiş numarası
- date: Fatura tarihi (GG/AA/YYYY formatında)
- issuer_name: Faturayı düzenleyen firma/kişi adı
- issuer_tax_id: Vergi kimlik numarası (TCKN veya VKN)
- issuer_tax_office: Vergi dairesi (SADECE isim, BÜYÜK HARFLERLE, "VERGİ DAİRESİ", "V.D." gibi ekler OLMADAN)
- customer_name: Müşteri adı (varsa)
- customer_tax_id: Müşteri vergi numarası (varsa)
- customer_tax_office: Müşteri vergi dairesi (varsa)
- description: Fatura içeriğinin KISA özeti (3-5 kelime)
- amount: Net tutar (sadece sayı)
- vat: KDV tutarı (sadece sayı)
- total: Toplam tutar (sadece sayı)

SADECE JSON formatında yanıt ver. 
- Tek fiş varsa: {"invoices": [{ ... fiş bilgileri ... }]}
- Birden fazla fiş varsa: {"invoices": [{ fiş1 }, { fiş2 }, ...]}

Örnek:
{"invoices": [{"invoice_number": "FIS-001", "date": "15/01/2024", "issuer_name": "ABC Market", "issuer_tax_id": "1234567890", "issuer_tax_office": "KADIKÖY", "customer_name": "", "customer_tax_id": "", "customer_tax_office": "", "description": "Market alışverişi", "amount": 100.0, "vat": 20.0, "total": 120.0}]}"""
        
        message = UserMessage(
            text=prompt,
            file_contents=[image_obj]
        )
        
        print("🤖 Sending message to LLM...")
        response = await chat.send_message(message)
        
        print(f"📥 Raw LLM Response:")
        print(f"Type: {type(response)}")
        print(f"Length: {len(response) if response else 0}")
        print(f"Content: '{response}'")
        print()
        
        # Test the parsing logic (same as backend)
        response_text = response.strip() if response else ""
        print(f"📝 After strip: '{response_text}'")
        
        if response_text.startswith("```json"):
            response_text = response_text[7:]
            print(f"📝 After removing ```json: '{response_text}'")
        if response_text.startswith("```"):
            response_text = response_text[3:]
            print(f"📝 After removing ```: '{response_text}'")
        if response_text.endswith("```"):
            response_text = response_text[:-3]
            print(f"📝 After removing ending ```: '{response_text}'")
        response_text = response_text.strip()
        print(f"📝 Final text for JSON parsing: '{response_text}'")
        print()
        
        if not response_text:
            print("❌ Empty response from LLM!")
            return False
        
        try:
            data = json.loads(response_text)
            print(f"✅ JSON parsing successful:")
            print(json.dumps(data, indent=2))
            return True
        except json.JSONDecodeError as e:
            print(f"❌ JSON parsing failed: {e}")
            print(f"   Problematic text: '{response_text}'")
            return False
            
    except Exception as e:
        print(f"❌ Exception: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    result = asyncio.run(test_llm_with_real_image())
    sys.exit(0 if result else 1)