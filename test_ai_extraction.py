#!/usr/bin/env python3
"""
Test the AI extraction function directly to debug the issue
"""

import sys
import os
import asyncio
import json
from pathlib import Path

# Add backend to path
sys.path.append('/app/backend')

# Set up environment
os.chdir('/app/backend')
from dotenv import load_dotenv
load_dotenv()

async def test_ai_extraction():
    """Test the AI extraction function directly"""
    
    # Import the function
    from server import extract_invoice_data_with_ai
    
    # Create a simple test PDF
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
/Length 200
>>
stream
BT
/F1 12 Tf
50 750 Td
(FATURA INV-2025-001) Tj
0 -20 Td
(Tarih: 15/01/2025) Tj
0 -20 Td
(Firma: Test A.S.) Tj
0 -20 Td
(VKN: 1234567890) Tj
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
456
%%EOF"""
    
    print("🔍 Testing AI Extraction Function")
    print("=" * 40)
    
    try:
        print("📄 Calling extract_invoice_data_with_ai...")
        result = await extract_invoice_data_with_ai(pdf_content, "test.pdf", "application/pdf")
        
        print(f"✅ AI Extraction Result:")
        print(json.dumps(result, indent=2))
        
        if isinstance(result, dict) and "error" in result:
            print(f"❌ Error in AI extraction: {result['error']}")
            return False
        elif isinstance(result, list) and len(result) > 0:
            print(f"✅ Successfully extracted {len(result)} invoice(s)")
            return True
        else:
            print(f"⚠️ Unexpected result format: {type(result)}")
            return False
            
    except Exception as e:
        print(f"❌ Exception in AI extraction: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    result = asyncio.run(test_ai_extraction())
    sys.exit(0 if result else 1)