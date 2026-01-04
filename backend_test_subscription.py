import requests
import sys
import json
from datetime import datetime

class SubscriptionAPITester:
    def __init__(self, base_url="https://kdvreport.preview.emergentagent.com"):
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

    def run_test(self, name, method, endpoint, expected_status, visitor_id, data=None):
        """Run a single API test"""
        url = f"{self.api_url}/{endpoint}"
        headers = self.get_auth_header(visitor_id)
        
        if data and method in ['POST', 'PUT']:
            headers['Content-Type'] = 'application/json'

        print(f"\n🔍 Testing {name}...")
        print(f"   URL: {url}")
        print(f"   Visitor ID: {visitor_id}")
        
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

    def test_upload_limit_enforcement(self, visitor_id):
        """Test POST /api/invoices/upload - Limit control for trial users"""
        # First create a session for this user
        session_data = {
            "taxpayer_name": "Test Limit Enforcement",
            "year": 2024,
            "month": 12
        }
        
        success, _ = self.run_test(
            "Create Session for Limit Test",
            "POST",
            "sessions",
            200,
            visitor_id,
            data=session_data
        )
        
        if not success:
            self.log_test("Upload Limit Enforcement", False, "Could not create session")
            return False
        
        # Check current subscription status
        success, sub_status = self.run_test(
            "Check Subscription Before Upload",
            "GET",
            "subscription/status",
            200,
            visitor_id
        )
        
        if not success:
            self.log_test("Upload Limit Enforcement", False, "Could not check subscription status")
            return False
        
        remaining = sub_status.get('remaining', 0)
        print(f"   Current remaining quota: {remaining}")
        
        # Try to upload a file
        url = f"{self.api_url}/invoices/upload"
        headers = self.get_auth_header(visitor_id)
        
        # Create a simple test file
        files = {
            'files': ('test_invoice.pdf', b'%PDF-1.4 test content', 'application/pdf')
        }
        data = {
            'category': 'income'
        }
        
        try:
            response = requests.post(url, files=files, data=data, headers=headers)
            
            print(f"   Upload Status: {response.status_code}")
            
            if remaining > 0:
                # Should succeed if quota available
                if response.status_code == 200:
                    response_data = response.json()
                    success_count = response_data.get('success', 0)
                    new_remaining = response_data.get('remaining_quota', 0)
                    
                    print(f"   Upload successful: {success_count} files, {new_remaining} remaining")
                    self.log_test("Upload Limit Enforcement (Within Limit)", True, f"Upload successful: {new_remaining} remaining")
                    return True
                else:
                    error_detail = response.text[:200]
                    self.log_test("Upload Limit Enforcement (Within Limit)", False, f"Upload failed: {error_detail}")
                    return False
            else:
                # Should fail if no quota
                if response.status_code == 403:
                    error_detail = response.json().get('detail', '')
                    if 'limit' in error_detail.lower() or 'deneme' in error_detail.lower():
                        print(f"   Correctly blocked: {error_detail}")
                        self.log_test("Upload Limit Enforcement (Quota Exceeded)", True, "Upload correctly blocked")
                        return True
                    else:
                        self.log_test("Upload Limit Enforcement (Quota Exceeded)", False, f"Wrong error message: {error_detail}")
                        return False
                else:
                    self.log_test("Upload Limit Enforcement (Quota Exceeded)", False, f"Expected 403, got {response.status_code}")
                    return False
                    
        except Exception as e:
            self.log_test("Upload Limit Enforcement", False, f"Exception: {str(e)}")
            return False

    def test_exhaust_trial_quota(self, visitor_id):
        """Test exhausting trial quota to trigger 403 error"""
        # Get current subscription status
        success, sub_status = self.run_test(
            "Check Subscription for Quota Exhaustion",
            "GET",
            "subscription/status",
            200,
            visitor_id
        )
        
        if not success:
            self.log_test("Exhaust Trial Quota", False, "Could not check subscription status")
            return False
        
        remaining = sub_status.get('remaining', 0)
        monthly_limit = sub_status.get('monthly_limit', 20)
        
        print(f"   Current quota: {remaining}/{monthly_limit}")
        
        if remaining == 0:
            print("   Quota already exhausted, testing 403 response")
            return self.test_upload_with_no_quota(visitor_id)
        
        # Upload files to exhaust quota
        url = f"{self.api_url}/invoices/upload"
        headers = self.get_auth_header(visitor_id)
        
        uploads_needed = remaining
        successful_uploads = 0
        
        for i in range(uploads_needed):
            files = {
                'files': (f'test_invoice_{i}.pdf', b'%PDF-1.4 test content', 'application/pdf')
            }
            data = {'category': 'income'}
            
            try:
                response = requests.post(url, files=files, data=data, headers=headers)
                if response.status_code == 200:
                    successful_uploads += 1
                    print(f"   Upload {i+1}/{uploads_needed} successful")
                else:
                    print(f"   Upload {i+1} failed: {response.status_code}")
                    break
            except Exception as e:
                print(f"   Upload {i+1} exception: {str(e)}")
                break
        
        print(f"   Completed {successful_uploads} uploads")
        
        # Now test that next upload fails with 403
        return self.test_upload_with_no_quota(visitor_id)

    def test_upload_with_no_quota(self, visitor_id):
        """Test upload when quota is exhausted - should return 403"""
        url = f"{self.api_url}/invoices/upload"
        headers = self.get_auth_header(visitor_id)
        
        files = {
            'files': ('test_over_limit.pdf', b'%PDF-1.4 test content', 'application/pdf')
        }
        data = {'category': 'income'}
        
        try:
            response = requests.post(url, files=files, data=data, headers=headers)
            
            if response.status_code == 403:
                error_detail = response.json().get('detail', '')
                if 'limit' in error_detail.lower() or 'deneme' in error_detail.lower():
                    print(f"   Correctly returned 403: {error_detail}")
                    self.log_test("Upload with No Quota (403 Error)", True, "403 error correctly returned")
                    return True
                else:
                    self.log_test("Upload with No Quota (403 Error)", False, f"Wrong error message: {error_detail}")
                    return False
            else:
                self.log_test("Upload with No Quota (403 Error)", False, f"Expected 403, got {response.status_code}")
                return False
                
        except Exception as e:
            self.log_test("Upload with No Quota (403 Error)", False, f"Exception: {str(e)}")
            return False

    def test_subscription_upgrade(self, visitor_id):
        """Test POST /api/subscription/upgrade - Upgrade subscription"""
        upgrade_data = {
            "plan_id": "starter",
            "wix_member_id": f"wix_member_{datetime.now().strftime('%H%M%S')}"
        }
        
        # Use form data for upgrade endpoint
        url = f"{self.api_url}/subscription/upgrade"
        headers = self.get_auth_header(visitor_id)
        
        try:
            response = requests.post(url, data=upgrade_data, headers=headers)
            
            print(f"   Upgrade Status: {response.status_code}")
            
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

    def test_link_wix_member(self, visitor_id):
        """Test POST /api/subscription/link-wix - Link Wix member ID"""
        link_data = {
            "wix_member_id": f"wix_test_{datetime.now().strftime('%H%M%S')}"
        }
        
        url = f"{self.api_url}/subscription/link-wix"
        headers = self.get_auth_header(visitor_id)
        
        try:
            response = requests.post(url, data=link_data, headers=headers)
            
            print(f"   Link Wix Status: {response.status_code}")
            
            if response.status_code == 200:
                response_data = response.json()
                if response_data.get('success'):
                    print(f"   Wix link successful: {response_data.get('message')}")
                    self.log_test("Link Wix Member", True, "Successfully linked Wix member")
                    return True
                else:
                    self.log_test("Link Wix Member", False, "Link response invalid")
                    return False
            else:
                error_detail = response.text[:200]
                self.log_test("Link Wix Member", False, f"Link failed: {error_detail}")
                return False
                
        except Exception as e:
            self.log_test("Link Wix Member", False, f"Exception: {str(e)}")
            return False

    def run_all_tests(self):
        """Run all subscription system tests"""
        print("🚀 Starting Subscription System API Tests")
        print(f"📍 Base URL: {self.base_url}")
        print("=" * 60)
        
        # Test 1: Get subscription plans
        print("\n📋 SUBSCRIPTION PLANS TEST")
        print("-" * 30)
        
        plans_success, plans = self.test_get_subscription_plans()
        if not plans_success:
            print("❌ Plans test failed, but continuing...")
        
        # Test 2: New user subscription status (should get trial)
        print("\n📋 NEW USER SUBSCRIPTION STATUS TEST")
        print("-" * 30)
        
        status_success, new_visitor_id = self.test_get_subscription_status_new_user()
        if not status_success:
            print("❌ New user status test failed, but continuing...")
            new_visitor_id = f"fallback_visitor_{datetime.now().strftime('%H%M%S')}"
        
        # Test 3: Upload limit enforcement
        print("\n📋 UPLOAD LIMIT ENFORCEMENT TEST")
        print("-" * 30)
        
        limit_success = self.test_upload_limit_enforcement(new_visitor_id)
        
        # Test 4: Exhaust trial quota and test 403 error
        print("\n📋 QUOTA EXHAUSTION TEST")
        print("-" * 30)
        
        quota_success = self.test_exhaust_trial_quota(new_visitor_id)
        
        # Test 5: Subscription upgrade
        print("\n📋 SUBSCRIPTION UPGRADE TEST")
        print("-" * 30)
        
        upgrade_visitor_id = f"upgrade_visitor_{datetime.now().strftime('%H%M%S')}"
        upgrade_success = self.test_subscription_upgrade(upgrade_visitor_id)
        
        # Test 6: Link Wix member
        print("\n📋 WIX MEMBER LINK TEST")
        print("-" * 30)
        
        link_success = self.test_link_wix_member(upgrade_visitor_id)
        
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