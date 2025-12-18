import requests
import json
from datetime import datetime

def test_quota_debug():
    base_url = "https://finance-assist-28.preview.emergentagent.com"
    api_url = f"{base_url}/api"
    
    # Create unique visitor ID
    visitor_id = f"debug_quota_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    headers = {
        'X-Visitor-ID': visitor_id,
        'Referer': 'https://www.documander.com/'
    }
    
    print(f"🔍 Debug Quota Test with Visitor ID: {visitor_id}")
    print("=" * 60)
    
    # 1. Check initial subscription status
    print("\n1. Initial subscription status:")
    response = requests.get(f"{api_url}/subscription/status", headers=headers)
    print(f"   Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"   Plan: {data.get('plan')}")
        print(f"   Monthly limit: {data.get('monthly_limit')}")
        print(f"   Monthly uploads: {data.get('monthly_uploads')}")
        print(f"   Remaining: {data.get('remaining')}")
        print(f"   Is trial: {data.get('is_trial')}")
        print(f"   Trial used: {data.get('trial_used')}")
    
    # 2. Create session
    print("\n2. Creating session:")
    session_data = {
        "taxpayer_name": "Debug Quota Test",
        "year": 2024,
        "month": 12
    }
    response = requests.post(f"{api_url}/sessions", json=session_data, headers=headers)
    print(f"   Session creation status: {response.status_code}")
    
    # 3. Upload one file and check quota
    print("\n3. Upload one file:")
    files = {
        'files': ('test1.pdf', b'%PDF-1.4 test content 1', 'application/pdf')
    }
    data = {'category': 'income'}
    
    response = requests.post(f"{api_url}/invoices/upload", files=files, data=data, headers=headers)
    print(f"   Upload status: {response.status_code}")
    if response.status_code == 200:
        upload_data = response.json()
        print(f"   Success: {upload_data.get('success')}")
        print(f"   Failed: {upload_data.get('failed')}")
        print(f"   Remaining quota: {upload_data.get('remaining_quota')}")
        print(f"   Errors: {upload_data.get('errors', [])}")
    else:
        print(f"   Error: {response.text[:200]}")
    
    # 4. Check subscription status after upload
    print("\n4. Subscription status after 1 upload:")
    response = requests.get(f"{api_url}/subscription/status", headers=headers)
    if response.status_code == 200:
        data = response.json()
        print(f"   Monthly uploads: {data.get('monthly_uploads')}")
        print(f"   Remaining: {data.get('remaining')}")
        print(f"   Trial used: {data.get('trial_used')}")
    
    # 5. Upload 19 more files to reach limit
    print("\n5. Uploading 19 more files to reach limit:")
    for i in range(2, 21):  # Upload files 2-20
        files = {
            'files': (f'test{i}.pdf', f'%PDF-1.4 test content {i}'.encode(), 'application/pdf')
        }
        data = {'category': 'income'}
        
        response = requests.post(f"{api_url}/invoices/upload", files=files, data=data, headers=headers)
        if response.status_code == 200:
            upload_data = response.json()
            remaining = upload_data.get('remaining_quota', -1)
            print(f"   Upload {i}: Success, remaining: {remaining}")
            
            if remaining == 0:
                print(f"   ⚠️  Quota exhausted after upload {i}")
                break
        else:
            print(f"   Upload {i}: Failed with status {response.status_code}")
            print(f"   Error: {response.text[:100]}")
            break
    
    # 6. Check final subscription status
    print("\n6. Final subscription status:")
    response = requests.get(f"{api_url}/subscription/status", headers=headers)
    if response.status_code == 200:
        data = response.json()
        print(f"   Monthly uploads: {data.get('monthly_uploads')}")
        print(f"   Remaining: {data.get('remaining')}")
        print(f"   Trial used: {data.get('trial_used')}")
    
    # 7. Try to upload one more file (should fail with 403)
    print("\n7. Attempting upload beyond limit:")
    files = {
        'files': ('test_over_limit.pdf', b'%PDF-1.4 over limit content', 'application/pdf')
    }
    data = {'category': 'income'}
    
    response = requests.post(f"{api_url}/invoices/upload", files=files, data=data, headers=headers)
    print(f"   Over-limit upload status: {response.status_code}")
    if response.status_code == 403:
        error_data = response.json()
        print(f"   ✅ Correctly blocked: {error_data.get('detail')}")
    elif response.status_code == 200:
        upload_data = response.json()
        print(f"   ❌ Upload succeeded when it should have failed!")
        print(f"   Success: {upload_data.get('success')}")
        print(f"   Remaining: {upload_data.get('remaining_quota')}")
    else:
        print(f"   Unexpected status: {response.text[:200]}")

if __name__ == "__main__":
    test_quota_debug()