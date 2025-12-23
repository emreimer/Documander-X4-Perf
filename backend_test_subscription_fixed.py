import requests
import sys
import json
from datetime import datetime

class SubscriptionAPITester:
    def __init__(self, base_url="https://invoice-extract-10.preview.emergentagent.com"):
        self.base_url = base_url
        self.api_url = f"{base_url}/api"
        self.tests_run = 0
        self.tests_passed = 0
        self.test_results = []

    def log_test(self, name, success, details=""):
        """Log test result"""
        self.tests_run += 1
        if success:
            self.tests_passed += 1
            print(f"✅ {name} - PASSED")
        else:
            print(f"❌ {name} - FAILED: {details}")
        
        self.test_results.append({
            "test": name,
            "success": success,
            "details": details
        })

    def get_auth_header(self, visitor_id):
        """Get authentication header with visitor ID"""
        return {
            'X-Visitor-ID': visitor_id,
            'Referer': 'https://www.documander.com/'
        }

    def create_valid_invoice_html(self, invoice_num):
        """Create a valid HTML invoice that AI can process"""
        return f"""
        <!DOCTYPE html>
        <html>
        <head><title>FATURA</title></head>
        <body>
            <h1>FATURA</h1>
            <p>Fatura No: INV-2024-{invoice_num:03d}</p>
            <p>Tarih: 15/12/2024</p>
            <p>Düzenleyen: Test Firma A.Ş.</p>
            <p>VKN: 1234567890</p>
            <p>Vergi Dairesi: KADIKÖY</p>
            <p>Müşteri: Test Müşteri Ltd.</p>
            <p>Müşteri VKN: 0987654321</p>
            <p>Müşteri V.Dairesi: BEŞİKTAŞ</p>
            <p>Açıklama: Yazılım hizmeti {invoice_num}</p>
            <p>Net Tutar: {1000 + invoice_num}.00</p>
            <p>KDV: {180 + invoice_num}.00</p>
            <p>Toplam: {1180 + invoice_num}.00</p>
        </body>
        </html>
        """.encode('utf-8')

    def run_test(self, name, method, endpoint, expected_status, visitor_id, data=None):
        """Run a single API test"""
        url = f"{self.api_url}/{endpoint}"
        headers = self.get_auth_header(visitor_id)
        
        if data and method in ['POST', 'PUT']:
            headers['Content-Type'] = 'application/json'

        print(f"\n🔍 Testing {name}...")
        print(f"   URL: {url}")
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=headers)
            elif method == 'PUT':
                response = requests.put(url, json=data, headers=headers)
            elif method == 'DELETE':
                response = requests.delete(url, headers=headers)

            success = response.status_code == expected_status
            
            if success:
                print(f"   Status: {response.status_code} ✅")
                try:
                    return success, response.json()
                except:
                    return success, {}
            else:
                error_detail = ""
                try:
                    error_detail = response.json().get('detail', 'Unknown error')
                except:
                    error_detail = response.text[:200]
                
                print(f"   Status: {response.status_code} ❌")
                print(f"   Error: {error_detail}")
                self.log_test(name, False, f"Expected {expected_status}, got {response.status_code}: {error_detail}")
                return False, {}

        except Exception as e:
            print(f"   Exception: {str(e)} ❌")
            self.log_test(name, False, f"Exception: {str(e)}")
            return False, {}

    def test_get_subscription_plans(self):
        """Test GET /api/subscription/plans - List all plans"""
        success, response = self.run_test(
            "Get Subscription Plans",
            "GET",
            "subscription/plans",
            200,
            "test_visitor_plans"
        )
        
        if success and 'plans' in response:
            plans = response['plans']
            expected_plans = ['trial', 'starter', 'professional', 'business', 'enterprise', 'unlimited']
            
            # Check if all expected plans are present
            plan_ids = [plan['id'] for plan in plans]
            missing_plans = [p for p in expected_plans if p not in plan_ids]
            
            if not missing_plans:
                print(f"   Found {len(plans)} plans: {plan_ids}")
                self.log_test("Get Subscription Plans", True, f"All {len(plans)} plans available")
                return True, plans
            else:
                self.log_test("Get Subscription Plans", False, f"Missing plans: {missing_plans}")
                return False, []
        else:
            self.log_test("Get Subscription Plans", False, "No plans in response")
            return False, []

    def test_get_subscription_status_new_user(self):
        """Test GET /api/subscription/status - New user should get trial"""
        # Use unique visitor ID for new user
        new_visitor_id = f"new_user_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        success, response = self.run_test(
            "Get Subscription Status (New User)",
            "GET",
            "subscription/status",
            200,
            new_visitor_id
        )
        
        if success:
            expected_fields = ['plan', 'plan_name', 'monthly_limit', 'monthly_uploads', 'remaining', 'is_trial', 'trial_used']
            missing_fields = [field for field in expected_fields if field not in response]
            
            if not missing_fields:
                plan = response.get('plan')
                is_trial = response.get('is_trial')
                monthly_limit = response.get('monthly_limit')
                remaining = response.get('remaining')
                
                if plan == 'trial' and is_trial and monthly_limit == 20:
                    print(f"   New user got trial plan: {remaining}/{monthly_limit} remaining")
                    self.log_test("Get Subscription Status (New User)", True, f"Trial plan assigned: {remaining}/20 remaining")
                    return True, new_visitor_id
                else:
                    self.log_test("Get Subscription Status (New User)", False, f"Expected trial plan, got: {plan}")
                    return False, new_visitor_id
            else:
                self.log_test("Get Subscription Status (New User)", False, f"Missing fields: {missing_fields}")
                return False, new_visitor_id
        else:
            self.log_test("Get Subscription Status (New User)", False, "Failed to get subscription status")
            return False, new_visitor_id

    def test_bulk_upload_limit_enforcement(self):
        """Test bulk upload limit enforcement - try to upload more than limit"""
        visitor_id = f"bulk_test_{datetime.now().strftime('%H%M%S')}"
        
        # Create session
        session_data = {
            "taxpayer_name": "Bulk Upload Test",
            "year": 2024,
            "month": 12
        }
        
        success, _ = self.run_test(
            "Create Session for Bulk Test",
            "POST",
            "sessions",
            200,
            visitor_id,
            data=session_data
        )
        
        if not success:
            self.log_test("Bulk Upload Limit Enforcement", False, "Could not create session")
            return False
        
        # Try to upload 25 files (more than 20 limit)
        url = f"{self.api_url}/invoices/upload"
        headers = self.get_auth_header(visitor_id)
        
        files = []
        for i in range(25):  # More than trial limit of 20
            files.append(('files', (f'test{i}.html', self.create_valid_invoice_html(i), 'text/html')))
        
        data = {'category': 'income'}
        
        try:
            response = requests.post(url, files=files, data=data, headers=headers)
            
            if response.status_code == 403:
                error_detail = response.json().get('detail', '')
                if 'deneme' in error_detail.lower() or 'limit' in error_detail.lower():
                    print(f"   ✅ Correctly blocked bulk upload: {error_detail}")
                    self.log_test("Bulk Upload Limit Enforcement", True, "Bulk upload correctly blocked")
                    return True
                else:
                    self.log_test("Bulk Upload Limit Enforcement", False, f"Wrong error message: {error_detail}")
                    return False
            else:
                self.log_test("Bulk Upload Limit Enforcement", False, f"Expected 403, got {response.status_code}")
                return False
                
        except Exception as e:
            self.log_test("Bulk Upload Limit Enforcement", False, f"Exception: {str(e)}")
            return False

    def test_quota_consumption_and_enforcement(self):
        """Test that quota is consumed and enforced correctly with valid files"""
        visitor_id = f"quota_test_{datetime.now().strftime('%H%M%S')}"
        
        # Create session
        session_data = {
            "taxpayer_name": "Quota Consumption Test",
            "year": 2024,
            "month": 12
        }
        
        success, _ = self.run_test(
            "Create Session for Quota Test",
            "POST",
            "sessions",
            200,
            visitor_id,
            data=session_data
        )
        
        if not success:
            self.log_test("Quota Consumption and Enforcement", False, "Could not create session")
            return False
        
        # Upload 3 valid HTML files
        url = f"{self.api_url}/invoices/upload"
        headers = self.get_auth_header(visitor_id)
        
        for i in range(3):
            files = {
                'files': (f'valid_invoice_{i}.html', self.create_valid_invoice_html(i), 'text/html')
            }
            data = {'category': 'income'}
            
            response = requests.post(url, files=files, data=data, headers=headers)
            
            if response.status_code == 200:
                upload_data = response.json()
                success_count = upload_data.get('success', 0)
                remaining = upload_data.get('remaining_quota', -1)
                
                print(f"   Upload {i+1}: Success={success_count}, Remaining={remaining}")
                
                if success_count == 0:
                    print(f"   ⚠️  Upload {i+1} failed to process (AI issue)")
                else:
                    print(f"   ✅ Upload {i+1} processed successfully")
            else:
                print(f"   ❌ Upload {i+1} failed with status {response.status_code}")
        
        # Check final subscription status
        success, sub_status = self.run_test(
            "Check Final Subscription Status",
            "GET",
            "subscription/status",
            200,
            visitor_id
        )
        
        if success:
            monthly_uploads = sub_status.get('monthly_uploads', 0)
            remaining = sub_status.get('remaining', 20)
            
            print(f"   Final status: {monthly_uploads} uploads used, {remaining} remaining")
            
            if monthly_uploads > 0:
                self.log_test("Quota Consumption and Enforcement", True, f"Quota consumed: {monthly_uploads} used")
                return True
            else:
                self.log_test("Quota Consumption and Enforcement", False, "No quota consumed (all uploads failed)")
                return False
        else:
            self.log_test("Quota Consumption and Enforcement", False, "Could not check final status")
            return False

    def test_subscription_upgrade(self):
        """Test POST /api/subscription/upgrade - Upgrade subscription"""
        visitor_id = f"upgrade_test_{datetime.now().strftime('%H%M%S')}"
        
        upgrade_data = {
            "plan_id": "starter",
            "wix_member_id": f"wix_member_{datetime.now().strftime('%H%M%S')}"
        }
        
        # Use form data for upgrade endpoint
        url = f"{self.api_url}/subscription/upgrade"
        headers = self.get_auth_header(visitor_id)
        
        try:
            response = requests.post(url, data=upgrade_data, headers=headers)
            
            if response.status_code == 200:
                response_data = response.json()
                if response_data.get('success') and response_data.get('plan') == 'starter':
                    print(f"   Upgrade successful: {response_data.get('message')}")
                    self.log_test("Subscription Upgrade", True, "Successfully upgraded to starter plan")
                    return True
                else:
                    self.log_test("Subscription Upgrade", False, "Upgrade response invalid")
                    return False
            else:
                error_detail = response.text[:200]
                self.log_test("Subscription Upgrade", False, f"Upgrade failed: {error_detail}")
                return False
                
        except Exception as e:
            self.log_test("Subscription Upgrade", False, f"Exception: {str(e)}")
            return False

    def run_all_tests(self):
        """Run all subscription system tests"""
        print("🚀 Starting Subscription System API Tests (Fixed)")
        print(f"📍 Base URL: {self.base_url}")
        print("=" * 60)
        
        # Test 1: Get subscription plans
        print("\n📋 SUBSCRIPTION PLANS TEST")
        print("-" * 30)
        plans_success, plans = self.test_get_subscription_plans()
        
        # Test 2: New user subscription status (should get trial)
        print("\n📋 NEW USER SUBSCRIPTION STATUS TEST")
        print("-" * 30)
        status_success, new_visitor_id = self.test_get_subscription_status_new_user()
        
        # Test 3: Bulk upload limit enforcement
        print("\n📋 BULK UPLOAD LIMIT ENFORCEMENT TEST")
        print("-" * 30)
        bulk_success = self.test_bulk_upload_limit_enforcement()
        
        # Test 4: Quota consumption with valid files
        print("\n📋 QUOTA CONSUMPTION TEST")
        print("-" * 30)
        quota_success = self.test_quota_consumption_and_enforcement()
        
        # Test 5: Subscription upgrade
        print("\n📋 SUBSCRIPTION UPGRADE TEST")
        print("-" * 30)
        upgrade_success = self.test_subscription_upgrade()
        
        # Print summary
        print("\n" + "=" * 60)
        print("📊 SUBSCRIPTION SYSTEM TEST SUMMARY")
        print(f"✅ Passed: {self.tests_passed}/{self.tests_run}")
        print(f"❌ Failed: {self.tests_run - self.tests_passed}/{self.tests_run}")
        
        if self.tests_passed == self.tests_run:
            print("🎉 All subscription tests passed!")
            return True
        else:
            print("⚠️  Some subscription tests failed. Check details above.")
            return False

def main():
    tester = SubscriptionAPITester()
    success = tester.run_all_tests()
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())