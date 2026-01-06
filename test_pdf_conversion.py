#!/usr/bin/env python3
"""
Test PDF to image conversion directly
"""

import sys
import os
import base64
from io import BytesIO

# Add backend to path
sys.path.append('/app/backend')
os.chdir('/app/backend')

def test_pdf_conversion():
    """Test PDF to image conversion"""
    
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
    
    print("🔍 Testing PDF to Image Conversion")
    print("=" * 40)
    
    try:
        from pdf2image import convert_from_bytes
        from PIL import Image
        
        print("📄 Converting PDF to images...")
        
        # Convert PDF to images
        images = convert_from_bytes(pdf_content, dpi=150, first_page=1, last_page=3)
        
        print(f"✅ Conversion successful! Generated {len(images)} image(s)")
        
        if images:
            # Process first image
            img = images[0]
            print(f"📏 Image size: {img.size}")
            print(f"📏 Image mode: {img.mode}")
            
            # Convert to base64
            img_buffer = BytesIO()
            img.save(img_buffer, format='PNG')
            img_buffer.seek(0)
            image_base64 = base64.b64encode(img_buffer.read()).decode('utf-8')
            
            print(f"📏 Base64 length: {len(image_base64)}")
            print(f"📏 Base64 starts with: {image_base64[:50]}...")
            
            # Save image for inspection
            img.save('/app/test_converted_image.png')
            print("💾 Saved test image to /app/test_converted_image.png")
            
            return True
        else:
            print("❌ No images generated from PDF")
            return False
            
    except Exception as e:
        print(f"❌ PDF conversion failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_pdf_conversion()
    sys.exit(0 if success else 1)