#!/usr/bin/env python3
"""
Test the LLM with a simple text-based image created using PIL
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

async def test_llm_with_text_image():
    """Test LLM with a simple text image created using PIL"""
    
    try:
        from emergentintegrations.llm.chat import LlmChat, UserMessage, ImageContent
        from PIL import Image, ImageDraw, ImageFont
        import uuid
        
        # Get the LLM key
        EMERGENT_LLM_KEY = os.environ.get('EMERGENT_LLM_KEY', '')
        print(f"🔑 EMERGENT_LLM_KEY configured: {bool(EMERGENT_LLM_KEY)}")
        
        if not EMERGENT_LLM_KEY:
            print("❌ No EMERGENT_LLM_KEY found!")
            return False
        
        print("📄 Creating text-based invoice image...")
        
        # Create a simple invoice image with PIL
        img = Image.new('RGB', (800, 600), color='white')
        draw = ImageDraw.Draw(img)
        
        # Try to use a default font
        try:
            font = ImageFont.load_default()
        except:
            font = None
        
        # Add invoice text
        y_pos = 50
        line_height = 30
        
        invoice_lines = [
            "FATURA / INVOICE",
            "",
            "Fatura No: INV-2025-001",
            "Tarih: 15/01/2025",
            "",
            "Satici: Test Firma A.S.",
            "Vergi No: 1234567890",
            "Vergi Dairesi: KADIKOY",
            "",
            "Musteri: Test Musteri Ltd.",
            "Musteri VKN: 0987654321",
            "",
            "Aciklama: Test urun satisi",
            "Tutar: 1000.00 TL",
            "KDV: 200.00 TL",
            "Toplam: 1200.00 TL"
        ]
        
        for line in invoice_lines:
            if line:  # Skip empty lines
                draw.text((50, y_pos), line, fill='black', font=font)
            y_pos += line_height
        
        # Convert to base64
        img_buffer = BytesIO()
        img.save(img_buffer, format='PNG')
        img_buffer.seek(0)
        image_base64 = base64.b64encode(img_buffer.read()).decode('utf-8')
        
        # Save for inspection
        img.save('/app/test_text_image.png')
        print(f"✅ Text image created. Size: {img.size}, Base64 length: {len(image_base64)}")
        print("💾 Saved test image to /app/test_text_image.png")
        
        # Create image content object
        image_obj = ImageContent(image_base64=image_base64)
        
        # Initialize LLM Chat
        chat = LlmChat(
            api_key=EMERGENT_LLM_KEY,
            session_id=f"test-extraction-{uuid.uuid4()}",
            system_message="You are an invoice data extraction assistant. Extract invoice information accurately from Turkish invoices and receipts."
        ).with_model("openai", "gpt-4o")
        
        print("✅ LLM Chat initialized successfully")
        
        # Simplified prompt for testing
        prompt = """Analyze this invoice image and extract the data. Return ONLY JSON format:

{"invoices": [{"invoice_number": "...", "date": "...", "issuer_name": "...", "issuer_tax_id": "...", "issuer_tax_office": "...", "customer_name": "...", "customer_tax_id": "...", "description": "...", "amount": 0.0, "vat": 0.0, "total": 0.0}]}"""
        
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
        
        # Test the parsing logic
        response_text = response.strip() if response else ""
        
        if response_text.startswith("```json"):
            response_text = response_text[7:]
        if response_text.startswith("```"):
            response_text = response_text[3:]
        if response_text.endswith("```"):
            response_text = response_text[:-3]
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
            
            # If JSON parsing fails, let's see if we can extract any useful info
            if "invoice" in response_text.lower() or "fatura" in response_text.lower():
                print("ℹ️  Response contains invoice-related content but not in JSON format")
            
            return False
            
    except Exception as e:
        print(f"❌ Exception: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    result = asyncio.run(test_llm_with_text_image())
    sys.exit(0 if result else 1)