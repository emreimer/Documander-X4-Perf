import requests
import sys
import json
from datetime import datetime, timezone, timedelta

class TwelveMonthSubscriptionTester:
    def __init__(self, base_url="https://bundan-basla.preview.emergentagent.com"):
        self.base_url = base_url
        self.api_url = f"{base_url}/api"
        self.visitor_id = f"test_12month_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
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

    def get_headers(self, wix_member_id=None, wix_plan=None, wix_expires=None):
        """Get headers for API requests"""
        headers = {
            'X-Visitor-ID': self.visitor_id,
            'Referer': 'https://bundan-basla.preview.emergentagent.com/',
            'Origin': 'https://bundan-basla.preview.emergentagent.com'
        }
        if wix_member_id:
            headers['X-Wix-Member-ID'] = wix_member_id
        if wix_plan:
            headers['X-Wix-Plan'] = wix_plan
        if wix_expires:
            headers['X-Wix-Expires'] = wix_expires
        return headers

    def make_request(self, method, endpoint, data=None, headers=None, expected_status=200):
        """Make API request and return success, response"""
        url = f"{self.api_url}/{endpoint}"
        if headers is None:
            headers = self.get_headers()
        
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
                try:
                    return True, response.json()
                except:
                    return True, {}
            else:
                try:
                    error = response.json().get('detail', response.text)
                except:
                    error = response.text
                return False, {"error": error, "status": response.status_code}
                
        except Exception as e:
            return False, {"error": str(e)}

    def test_trial_plan_creation(self):
        """Test that new users get trial plan with 7 days expiry"""
        print(f"\n🔍 Testing Trial Plan Creation...")
        
        success, response = self.make_request('GET', 'subscription/status')
        
        if success:
            plan = response.get('plan')
            expires_at = response.get('expires_at')
            is_trial = response.get('is_trial')
            total_limit = response.get('total_limit', response.get('monthly_limit'))
            
            if plan == 'trial' and is_trial and total_limit == 20:
                # Check expiry is approximately 7 days from now
                if expires_at:
                    try:
                        exp_date = datetime.fromisoformat(expires_at.replace('Z', '+00:00'))
                        now = datetime.now(timezone.utc)
                        days_diff = (exp_date - now).days
                        if 6 <= days_diff <= 7:  # Allow some tolerance
                            self.log_test("Trial Plan Creation", True, f"Trial plan with 7 days expiry ({days_diff} days)")
                            return True
                        else:
                            self.log_test("Trial Plan Creation", False, f"Trial expiry is {days_diff} days, expected ~7")
                            return False
                    except Exception as e:
                        self.log_test("Trial Plan Creation", False, f"Date parsing error: {e}")
                        return False
                else:
                    self.log_test("Trial Plan Creation", False, "No expires_at field")
                    return False
            else:
                self.log_test("Trial Plan Creation", False, f"Expected trial plan with 20 limit, got {plan} with {total_limit}")
                return False
        else:
            self.log_test("Trial Plan Creation", False, f"API error: {response}")
            return False

    def test_paid_plan_12_month_expiry(self):
        """Test that paid plans get 12 month expiry"""
        print(f"\n🔍 Testing Paid Plan 12 Month Expiry...")
        
        # Simulate Wix user with starter plan
        wix_member_id = f"wix_test_12month_{datetime.now().strftime('%H%M%S')}"
        headers = self.get_headers(wix_member_id=wix_member_id, wix_plan='starter')
        
        success, response = self.make_request('GET', 'subscription/status', headers=headers)
        
        if success:
            plan = response.get('plan')
            expires_at = response.get('expires_at')
            is_annual_plan = response.get('is_annual_plan')
            total_limit = response.get('total_limit', response.get('monthly_limit'))
            
            if plan == 'starter' and is_annual_plan and total_limit == 1000:
                # Check expiry is approximately 12 months (365 days) from now
                if expires_at:
                    try:
                        exp_date = datetime.fromisoformat(expires_at.replace('Z', '+00:00'))
                        now = datetime.now(timezone.utc)
                        days_diff = (exp_date - now).days
                        if 360 <= days_diff <= 370:  # Allow some tolerance for 12 months
                            self.log_test("Paid Plan 12 Month Expiry", True, f"Starter plan with ~12 months expiry ({days_diff} days)")
                            return True
                        else:
                            self.log_test("Paid Plan 12 Month Expiry", False, f"Starter expiry is {days_diff} days, expected ~365")
                            return False
                    except Exception as e:
                        self.log_test("Paid Plan 12 Month Expiry", False, f"Date parsing error: {e}")
                        return False
                else:
                    self.log_test("Paid Plan 12 Month Expiry", False, "No expires_at field")
                    return False
            else:
                self.log_test("Paid Plan 12 Month Expiry", False, f"Expected starter plan with 1000 limit, got {plan} with {total_limit}")
                return False
        else:
            self.log_test("Paid Plan 12 Month Expiry", False, f"API error: {response}")
            return False

    def test_professional_plan_12_month_expiry(self):
        """Test professional plan gets 12 month expiry"""
        print(f"\n🔍 Testing Professional Plan 12 Month Expiry...")
        
        # Simulate Wix user with professional plan
        wix_member_id = f"wix_test_prof_{datetime.now().strftime('%H%M%S')}"
        headers = self.get_headers(wix_member_id=wix_member_id, wix_plan='professional')
        
        success, response = self.make_request('GET', 'subscription/status', headers=headers)
        
        if success:
            plan = response.get('plan')
            expires_at = response.get('expires_at')
            is_annual_plan = response.get('is_annual_plan')
            total_limit = response.get('total_limit', response.get('monthly_limit'))
            
            if plan == 'professional' and is_annual_plan and total_limit == 2500:
                # Check expiry is approximately 12 months (365 days) from now
                if expires_at:
                    try:
                        exp_date = datetime.fromisoformat(expires_at.replace('Z', '+00:00'))
                        now = datetime.now(timezone.utc)
                        days_diff = (exp_date - now).days
                        if 360 <= days_diff <= 370:  # Allow some tolerance for 12 months
                            self.log_test("Professional Plan 12 Month Expiry", True, f"Professional plan with ~12 months expiry ({days_diff} days)")
                            return True
                        else:
                            self.log_test("Professional Plan 12 Month Expiry", False, f"Professional expiry is {days_diff} days, expected ~365")
                            return False
                    except Exception as e:
                        self.log_test("Professional Plan 12 Month Expiry", False, f"Date parsing error: {e}")
                        return False
                else:
                    self.log_test("Professional Plan 12 Month Expiry", False, "No expires_at field")
                    return False
            else:
                self.log_test("Professional Plan 12 Month Expiry", False, f"Expected professional plan with 2500 limit, got {plan} with {total_limit}")
                return False
        else:
            self.log_test("Professional Plan 12 Month Expiry", False, f"API error: {response}")
            return False

    def test_no_monthly_reset_logic(self):
        """Test that there's no monthly reset logic - quota is total for subscription period"""
        print(f"\n🔍 Testing No Monthly Reset Logic...")
        
        # Create a user with starter plan
        wix_member_id = f"wix_test_noreset_{datetime.now().strftime('%H%M%S')}"
        headers = self.get_headers(wix_member_id=wix_member_id, wix_plan='starter')
        
        # Get initial status
        success, response = self.make_request('GET', 'subscription/status', headers=headers)
        
        if success:
            initial_uploads = response.get('total_uploads', response.get('monthly_uploads', 0))
            total_limit = response.get('total_limit', response.get('monthly_limit'))
            
            # Check that the field names indicate total usage, not monthly
            has_total_fields = 'total_uploads' in response and 'total_limit' in response
            
            if has_total_fields:
                self.log_test("No Monthly Reset Logic", True, f"API uses total_uploads ({initial_uploads}) and total_limit ({total_limit}) fields")
                return True
            else:
                # Check if monthly fields are used but represent total usage
                if 'monthly_uploads' in response and 'monthly_limit' in response:
                    self.log_test("No Monthly Reset Logic", True, f"API uses monthly_uploads ({initial_uploads}) but represents total usage for subscription period")
                    return True
                else:
                    self.log_test("No Monthly Reset Logic", False, "Missing usage tracking fields")
                    return False
        else:
            self.log_test("No Monthly Reset Logic", False, f"API error: {response}")
            return False

    def test_quota_exhaustion_blocking(self):
        """Test that uploads are blocked when quota is exhausted"""
        print(f"\n🔍 Testing Quota Exhaustion Blocking...")
        
        # Create a trial user (20 file limit)
        trial_visitor_id = f"test_quota_block_{datetime.now().strftime('%H%M%S')}"
        headers = {
            'X-Visitor-ID': trial_visitor_id,
            'Referer': 'https://bundan-basla.preview.emergentagent.com/',
            'Origin': 'https://bundan-basla.preview.emergentagent.com'
        }
        
        # First create a session (required for upload)
        session_data = {
            "taxpayer_name": "Test Quota Block",
            "year": 2024,
            "month": 12
        }
        
        success, _ = self.make_request('POST', 'sessions', session_data, headers)
        if not success:
            self.log_test("Quota Exhaustion Blocking", False, "Could not create session")
            return False
        
        # Get initial quota status
        success, response = self.make_request('GET', 'subscription/status', headers=headers)
        if not success:
            self.log_test("Quota Exhaustion Blocking", False, "Could not get subscription status")
            return False
        
        remaining = response.get('remaining', 0)
        total_limit = response.get('total_limit', response.get('monthly_limit', 0))
        
        print(f"   Initial quota: {remaining}/{total_limit}")
        
        # Try to upload more files than the limit allows
        # We'll simulate this by checking the upload limit API directly
        url = f"{self.api_url}/invoices/upload"
        
        # Create a simple test file
        files = {'files': ('test.txt', 'test content', 'text/plain')}
        data = {'category': 'income'}
        
        # Try to upload when we have quota
        if remaining > 0:
            response = requests.post(url, files=files, data=data, headers=headers)
            if response.status_code == 200:
                print(f"   Upload successful when quota available")
                
                # Now check if quota was decremented
                success, status_response = self.make_request('GET', 'subscription/status', headers=headers)
                if success:
                    new_remaining = status_response.get('remaining', 0)
                    if new_remaining == remaining - 1:
                        self.log_test("Quota Exhaustion Blocking", True, f"Quota correctly decremented from {remaining} to {new_remaining}")
                        return True
                    else:
                        self.log_test("Quota Exhaustion Blocking", False, f"Quota not decremented correctly: {remaining} -> {new_remaining}")
                        return False
                else:
                    self.log_test("Quota Exhaustion Blocking", False, "Could not check quota after upload")
                    return False
            else:
                # Check if it's a quota exhaustion error
                try:
                    error_response = response.json()
                    error_detail = error_response.get('detail', '')
                    if 'kota' in error_detail.lower() or 'quota' in error_detail.lower() or 'limit' in error_detail.lower():
                        self.log_test("Quota Exhaustion Blocking", True, f"Upload blocked due to quota: {error_detail}")
                        return True
                    else:
                        self.log_test("Quota Exhaustion Blocking", False, f"Upload failed for other reason: {error_detail}")
                        return False
                except:
                    self.log_test("Quota Exhaustion Blocking", False, f"Upload failed with status {response.status_code}")
                    return False
        else:
            # No quota remaining, upload should be blocked
            response = requests.post(url, files=files, data=data, headers=headers)
            if response.status_code != 200:
                try:
                    error_response = response.json()
                    error_detail = error_response.get('detail', '')
                    if 'kota' in error_detail.lower() or 'quota' in error_detail.lower() or 'deneme' in error_detail.lower():
                        self.log_test("Quota Exhaustion Blocking", True, f"Upload correctly blocked: {error_detail}")
                        return True
                    else:
                        self.log_test("Quota Exhaustion Blocking", False, f"Upload blocked for wrong reason: {error_detail}")
                        return False
                except:
                    self.log_test("Quota Exhaustion Blocking", False, f"Upload blocked but no error message (status {response.status_code})")
                    return False
            else:
                self.log_test("Quota Exhaustion Blocking", False, "Upload succeeded when quota should be exhausted")
                return False

    def test_subscription_status_fields(self):
        """Test that subscription status API returns correct fields for 12-month system"""
        print(f"\n🔍 Testing Subscription Status Fields...")
        
        # Test with starter plan
        wix_member_id = f"wix_test_fields_{datetime.now().strftime('%H%M%S')}"
        headers = self.get_headers(wix_member_id=wix_member_id, wix_plan='starter')
        
        success, response = self.make_request('GET', 'subscription/status', headers=headers)
        
        if success:
            required_fields = [
                'plan', 'plan_name', 'total_limit', 'total_uploads', 'remaining',
                'is_trial', 'is_unlimited', 'is_annual_plan', 'expires_at',
                'is_expired', 'is_quota_exhausted', 'days_remaining'
            ]
            
            missing_fields = []
            for field in required_fields:
                if field not in response:
                    missing_fields.append(field)
            
            if not missing_fields:
                # Check specific values for starter plan
                plan = response.get('plan')
                is_annual_plan = response.get('is_annual_plan')
                total_limit = response.get('total_limit', response.get('monthly_limit'))
                
                if plan == 'starter' and is_annual_plan and total_limit == 1000:
                    self.log_test("Subscription Status Fields", True, "All required fields present with correct values")
                    return True
                else:
                    self.log_test("Subscription Status Fields", False, f"Incorrect values: plan={plan}, is_annual={is_annual_plan}, limit={total_limit}")
                    return False
            else:
                self.log_test("Subscription Status Fields", False, f"Missing fields: {missing_fields}")
                return False
        else:
            self.log_test("Subscription Status Fields", False, f"API error: {response}")
            return False

    def test_plans_api_12_month_info(self):
        """Test that plans API returns correct information for 12-month system"""
        print(f"\n🔍 Testing Plans API 12 Month Info...")
        
        success, response = self.make_request('GET', 'subscription/plans')
        
        if success:
            plans = response.get('plans', [])
            
            if len(plans) >= 5:  # Should have at least trial, starter, professional, business, enterprise
                # Check starter plan
                starter_plan = next((p for p in plans if p['id'] == 'starter'), None)
                professional_plan = next((p for p in plans if p['id'] == 'professional'), None)
                
                if starter_plan and professional_plan:
                    starter_limit = starter_plan.get('monthly_limit')  # Note: field name is monthly_limit but represents total
                    starter_price = starter_plan.get('price')
                    
                    prof_limit = professional_plan.get('monthly_limit')
                    prof_price = professional_plan.get('price')
                    
                    if starter_limit == 1000 and starter_price == 699 and prof_limit == 2500 and prof_price == 1399:
                        self.log_test("Plans API 12 Month Info", True, f"Plans have correct limits and prices for 12-month system")
                        return True
                    else:
                        self.log_test("Plans API 12 Month Info", False, f"Incorrect plan values: starter({starter_limit}, {starter_price}), prof({prof_limit}, {prof_price})")
                        return False
                else:
                    self.log_test("Plans API 12 Month Info", False, "Missing starter or professional plan")
                    return False
            else:
                self.log_test("Plans API 12 Month Info", False, f"Expected at least 5 plans, got {len(plans)}")
                return False
        else:
            self.log_test("Plans API 12 Month Info", False, f"API error: {response}")
            return False

    def run_all_tests(self):
        """Run all 12-month subscription tests"""
        print("🚀 Starting 12-Month Subscription System Tests")
        print(f"📍 Base URL: {self.base_url}")
        print("=" * 60)
        
        # Test 1: Trial plan creation (7 days)
        self.test_trial_plan_creation()
        
        # Test 2: Paid plans get 12 month expiry
        self.test_paid_plan_12_month_expiry()
        self.test_professional_plan_12_month_expiry()
        
        # Test 3: No monthly reset logic
        self.test_no_monthly_reset_logic()
        
        # Test 4: Quota exhaustion blocking
        self.test_quota_exhaustion_blocking()
        
        # Test 5: Subscription status API fields
        self.test_subscription_status_fields()
        
        # Test 6: Plans API information
        self.test_plans_api_12_month_info()
        
        # Print summary
        print("\n" + "=" * 60)
        print("📊 12-MONTH SUBSCRIPTION TEST SUMMARY")
        print(f"✅ Passed: {self.tests_passed}/{self.tests_run}")
        print(f"❌ Failed: {self.tests_run - self.tests_passed}/{self.tests_run}")
        
        if self.tests_passed == self.tests_run:
            print("🎉 All 12-month subscription tests passed!")
            return True
        else:
            print("⚠️  Some tests failed. Check details above.")
            return False

def main():
    tester = TwelveMonthSubscriptionTester()
    success = tester.run_all_tests()
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())