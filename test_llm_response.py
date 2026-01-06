#!/usr/bin/env python3
"""
Test the LLM response directly to see what it's returning
"""

import sys
import os
import asyncio
import json
import base64
from pathlib import Path

# Add backend to path
sys.path.append('/app/backend')

# Set up environment
os.chdir('/app/backend')
from dotenv import load_dotenv
load_dotenv()

async def test_llm_response():
    """Test what the LLM is actually returning"""
    
    try:
        from emergentintegrations.llm.chat import LlmChat, UserMessage, ImageContent
        import uuid
        
        # Get the LLM key
        EMERGENT_LLM_KEY = os.environ.get('EMERGENT_LLM_KEY', '')
        print(f"🔑 LLM Key configured: {bool(EMERGENT_LLM_KEY)}")
        
        # Initialize LLM Chat
        chat = LlmChat(
            api_key=EMERGENT_LLM_KEY,
            session_id=f"test-extraction-{uuid.uuid4()}",
            system_message="You are an invoice data extraction assistant. Extract invoice information accurately from Turkish invoices and receipts."
        ).with_model("openai", "gpt-4o")
        
        print("✅ LLM Chat initialized successfully")
        
        # Create a simple test image (1x1 pixel PNG)
        # This is a minimal valid PNG image
        png_data = base64.b64decode(
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChAI9jU77yQAAAABJRU5ErkJggg=="
        )
        image_base64 = base64.b64encode(png_data).decode('utf-8')
        image_obj = ImageContent(image_base64=image_base64)
        
        print("📄 Test image created")
        
        # Simple prompt
        prompt = """Analyze this image and extract invoice data. Return ONLY JSON format:
{"invoices": [{"invoice_number": "TEST-001", "date": "01/01/2025", "issuer_name": "Test Company", "amount": 100.0, "vat": 20.0, "total": 120.0}]}"""
        
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
    result = asyncio.run(test_llm_response())
    sys.exit(0 if result else 1)