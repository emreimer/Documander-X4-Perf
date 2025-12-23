import requests
import sys
from datetime import datetime

def test_quota_decrement():
    """Test quota decrement with proper session setup"""
    base_url = "https://invoice-extract-10.preview.emergentagent.com"
    api_url = f"{base_url}/api"
    visitor_id = f"test_quota_detailed_{datetime.now().strftime('%H%M%S')}"
    
    headers = {
        'X-Visitor-ID': visitor_id,
        'Referer': 'https://invoice-extract-10.preview.emergentagent.com/',
        'Origin': 'https://invoice-extract-10.preview.emergentagent.com'
    }
    
    print(f"🔍 Testing Quota Decrement with Visitor ID: {visitor_id}")
    
    # Step 1: Get initial subscription status
    print("\n1. Getting initial subscription status...")
    response = requests.get(f"{api_url}/subscription/status", headers=headers)
    print(f"   Status: {response.status_code}")
    if response.status_code == 200:
        initial_status = response.json()
        print(f"   Initial quota: {initial_status.get('remaining')}/{initial_status.get('total_limit')}")
        print(f"   Total uploads: {initial_status.get('total_uploads')}")
    else:
        print(f"   Error: {response.text}")
        return False
    
    # Step 2: Create a session (required for upload)
    print("\n2. Creating taxpayer session...")
    session_data = {
        "taxpayer_name": "Test Quota Decrement",
        "year": 2024,
        "month": 12
    }
    response = requests.post(f"{api_url}/sessions", json=session_data, headers=headers)
    print(f"   Status: {response.status_code}")
    if response.status_code == 200:
        session = response.json()
        print(f"   Session created: {session.get('id')}")
    else:
        print(f"   Error: {response.text}")
        return False
    
    # Step 3: Create a simple test image file (AI can process)
    print("\n3. Creating test invoice file...")
    # Create a simple text file that looks like an invoice
    invoice_content = """
FATURA / INVOICE

Fatura No: TEST-2024-001
Tarih: 15/12/2024

Düzenleyen: Test Firma A.Ş.
VKN: 1234567890
Vergi Dairesi: KADIKÖY

Müşteri: Test Müşteri Ltd.
VKN: 0987654321
Vergi Dairesi: BEŞIKTAŞ

Açıklama: Test hizmeti
Net Tutar: 1000.00 TL
KDV: 180.00 TL
Toplam: 1180.00 TL
"""
    
    # Step 4: Upload the invoice
    print("\n4. Uploading test invoice...")
    files = {'files': ('test_invoice.txt', invoice_content, 'text/plain')}
    data = {'category': 'income'}
    
    response = requests.post(f"{api_url}/invoices/upload", files=files, data=data, headers=headers)
    print(f"   Status: {response.status_code}")
    
    if response.status_code == 200:
        upload_result = response.json()
        print(f"   Upload result: {upload_result}")
        success_count = upload_result.get('success', 0)
        failed_count = upload_result.get('failed', 0)
        print(f"   Successful uploads: {success_count}")
        print(f"   Failed uploads: {failed_count}")
        
        if success_count > 0:
            print("   ✅ Upload successful")
        else:
            print("   ❌ No successful uploads")
            print(f"   Errors: {upload_result.get('errors', [])}")
            return False
    else:
        print(f"   Error: {response.text}")
        return False
    
    # Step 5: Check quota after upload
    print("\n5. Checking quota after upload...")
    response = requests.get(f"{api_url}/subscription/status", headers=headers)
    print(f"   Status: {response.status_code}")
    if response.status_code == 200:
        final_status = response.json()
        print(f"   Final quota: {final_status.get('remaining')}/{final_status.get('total_limit')}")
        print(f"   Total uploads: {final_status.get('total_uploads')}")
        
        initial_remaining = initial_status.get('remaining', 0)
        final_remaining = final_status.get('remaining', 0)
        initial_uploads = initial_status.get('total_uploads', 0)
        final_uploads = final_status.get('total_uploads', 0)
        
        if final_remaining == initial_remaining - 1 and final_uploads == initial_uploads + 1:
            print("   ✅ Quota decremented correctly")
            return True
        else:
            print(f"   ❌ Quota not decremented correctly")
            print(f"   Expected: remaining={initial_remaining-1}, uploads={initial_uploads+1}")
            print(f"   Actual: remaining={final_remaining}, uploads={final_uploads}")
            return False
    else:
        print(f"   Error: {response.text}")
        return False

if __name__ == "__main__":
    success = test_quota_decrement()
    sys.exit(0 if success else 1)