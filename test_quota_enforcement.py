import requests
import json
from datetime import datetime

def test_quota_enforcement_api_level():
    """Test quota enforcement at API level - upload more files than limit allows"""
    base_url = "https://kdvreport.preview.emergentagent.com"
    api_url = f"{base_url}/api"
    
    # Create unique visitor ID
    visitor_id = f"quota_enforce_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    headers = {
        'X-Visitor-ID': visitor_id,
        'Referer': 'https://www.documander.com/'
    }
    
    print(f"🔍 Testing Quota Enforcement at API Level")
    print(f"Visitor ID: {visitor_id}")
    print("=" * 60)
    
    # 1. Check initial subscription status
    print("\n1. Initial subscription status:")
    response = requests.get(f"{api_url}/subscription/status", headers=headers)
    print(f"   Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        monthly_limit = data.get('monthly_limit', 20)
        print(f"   Plan: {data.get('plan')}")
        print(f"   Monthly limit: {monthly_limit}")
        print(f"   Remaining: {data.get('remaining')}")
    
    # 2. Create session
    print("\n2. Creating session:")
    session_data = {
        "taxpayer_name": "Quota Enforcement Test",
        "year": 2024,
        "month": 12
    }
    response = requests.post(f"{api_url}/sessions", json=session_data, headers=headers)
    print(f"   Session creation status: {response.status_code}")
    
    # 3. Try to upload MORE files than the limit allows (should fail with 403)
    print(f"\n3. Attempting to upload {monthly_limit + 5} files (more than limit of {monthly_limit}):")
    
    # Create multiple files in a single request
    files = []
    for i in range(monthly_limit + 5):  # Upload more than limit
        files.append(('files', (f'test{i}.pdf', b'%PDF-1.4 test content', 'application/pdf')))
    
    data = {'category': 'income'}
    
    response = requests.post(f"{api_url}/invoices/upload", files=files, data=data, headers=headers)
    print(f"   Upload status: {response.status_code}")
    
    if response.status_code == 403:
        error_data = response.json()
        print(f"   ✅ Correctly blocked bulk upload: {error_data.get('detail')}")
        return True
    elif response.status_code == 200:
        upload_data = response.json()
        print(f"   ❌ Bulk upload succeeded when it should have failed!")
        print(f"   Success: {upload_data.get('success')}")
        print(f"   Failed: {upload_data.get('failed')}")
        return False
    else:
        print(f"   Unexpected status: {response.text[:200]}")
        return False

def test_quota_with_valid_files():
    """Test quota with files that should process successfully"""
    base_url = "https://kdvreport.preview.emergentagent.com"
    api_url = f"{base_url}/api"
    
    # Create unique visitor ID
    visitor_id = f"valid_files_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    headers = {
        'X-Visitor-ID': visitor_id,
        'Referer': 'https://www.documander.com/'
    }
    
    print(f"\n🔍 Testing Quota with Valid-ish Files")
    print(f"Visitor ID: {visitor_id}")
    print("=" * 60)
    
    # Create session
    session_data = {
        "taxpayer_name": "Valid Files Test",
        "year": 2024,
        "month": 12
    }
    response = requests.post(f"{api_url}/sessions", json=session_data, headers=headers)
    print(f"Session creation status: {response.status_code}")
    
    # Try with HTML content that might be easier for AI to process
    html_content = """
    <!DOCTYPE html>
    <html>
    <head><title>FATURA</title></head>
    <body>
        <h1>FATURA</h1>
        <p>Fatura No: INV-2024-001</p>
        <p>Tarih: 15/12/2024</p>
        <p>Düzenleyen: Test Firma A.Ş.</p>
        <p>VKN: 1234567890</p>
        <p>Vergi Dairesi: KADIKÖY</p>
        <p>Müşteri: Test Müşteri Ltd.</p>
        <p>Müşteri VKN: 0987654321</p>
        <p>Müşteri V.Dairesi: BEŞİKTAŞ</p>
        <p>Açıklama: Yazılım hizmeti</p>
        <p>Net Tutar: 1000.00</p>
        <p>KDV: 180.00</p>
        <p>Toplam: 1180.00</p>
    </body>
    </html>
    """.encode('utf-8')
    
    # Upload one HTML file
    files = {
        'files': ('test_invoice.html', html_content, 'text/html')
    }
    data = {'category': 'income'}
    
    response = requests.post(f"{api_url}/invoices/upload", files=files, data=data, headers=headers)
    print(f"HTML upload status: {response.status_code}")
    
    if response.status_code == 200:
        upload_data = response.json()
        print(f"Success: {upload_data.get('success')}")
        print(f"Failed: {upload_data.get('failed')}")
        print(f"Remaining quota: {upload_data.get('remaining_quota')}")
        print(f"Errors: {upload_data.get('errors', [])}")
        
        if upload_data.get('success', 0) > 0:
            print("✅ Successfully processed at least one file")
            return True
        else:
            print("❌ No files processed successfully")
            return False
    else:
        print(f"Upload failed: {response.text[:200]}")
        return False

if __name__ == "__main__":
    print("Testing Quota Enforcement Mechanisms")
    print("=" * 80)
    
    # Test 1: API level enforcement (bulk upload beyond limit)
    result1 = test_quota_enforcement_api_level()
    
    # Test 2: Try with more processable files
    result2 = test_quota_with_valid_files()
    
    print("\n" + "=" * 80)
    print("SUMMARY:")
    print(f"API Level Enforcement: {'✅ PASS' if result1 else '❌ FAIL'}")
    print(f"Valid Files Processing: {'✅ PASS' if result2 else '❌ FAIL'}")