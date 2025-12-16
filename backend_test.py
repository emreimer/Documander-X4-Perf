import requests
import sys
import json
import io
from datetime import datetime
from pathlib import Path

class InvoiceAPITester:
    def __init__(self, base_url="https://fatura-yonetim-3.preview.emergentagent.com"):
        self.base_url = base_url
        self.api_url = f"{base_url}/api"
        self.token = None
        self.user_id = None
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

    def run_test(self, name, method, endpoint, expected_status, data=None, files=None, response_type='json'):
        """Run a single API test"""
        url = f"{self.api_url}/{endpoint}"
        headers = {'Content-Type': 'application/json'}
        
        if self.token:
            headers['Authorization'] = f'Bearer {self.token}'
        
        if files:
            # Remove Content-Type for file uploads
            headers.pop('Content-Type', None)

        print(f"\n🔍 Testing {name}...")
        print(f"   URL: {url}")
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers)
            elif method == 'POST':
                if files:
                    response = requests.post(url, files=files, headers=headers)
                else:
                    response = requests.post(url, json=data, headers=headers)
            elif method == 'PUT':
                response = requests.put(url, json=data, headers=headers)
            elif method == 'DELETE':
                response = requests.delete(url, headers=headers)

            success = response.status_code == expected_status
            
            if success:
                print(f"   Status: {response.status_code} ✅")
                if response_type == 'json' and response.content:
                    try:
                        return success, response.json()
                    except:
                        return success, {}
                else:
                    return success, response.content
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

    def test_auth_register(self):
        """Test user registration"""
        test_email = f"test_{datetime.now().strftime('%H%M%S')}@test.com"
        test_data = {
            "email": test_email,
            "password": "TestPass123!",
            "full_name": "Test User"
        }
        
        success, response = self.run_test(
            "User Registration",
            "POST",
            "auth/register",
            200,
            data=test_data
        )
        
        if success and 'token' in response:
            self.token = response['token']
            self.user_id = response['user']['id']
            self.log_test("User Registration", True)
            return True
        else:
            self.log_test("User Registration", False, "No token in response")
            return False

    def test_auth_login(self):
        """Test user login with existing credentials"""
        # First register a user
        test_email = f"login_test_{datetime.now().strftime('%H%M%S')}@test.com"
        register_data = {
            "email": test_email,
            "password": "TestPass123!",
            "full_name": "Login Test User"
        }
        
        # Register
        success, _ = self.run_test(
            "Pre-Login Registration",
            "POST",
            "auth/register",
            200,
            data=register_data
        )
        
        if not success:
            self.log_test("Login Test Setup", False, "Failed to register user for login test")
            return False
        
        # Now test login
        login_data = {
            "email": test_email,
            "password": "TestPass123!"
        }
        
        success, response = self.run_test(
            "User Login",
            "POST",
            "auth/login",
            200,
            data=login_data
        )
        
        if success and 'token' in response:
            # Update token for subsequent tests
            self.token = response['token']
            self.user_id = response['user']['id']
            self.log_test("User Login", True)
            return True
        else:
            self.log_test("User Login", False, "No token in response")
            return False

    def test_auth_me(self):
        """Test getting current user info"""
        if not self.token:
            self.log_test("Get Current User", False, "No token available")
            return False
        
        success, response = self.run_test(
            "Get Current User",
            "GET",
            "auth/me",
            200
        )
        
        if success and 'id' in response:
            self.log_test("Get Current User", True)
            return True
        else:
            self.log_test("Get Current User", False, "No user data in response")
            return False

    def test_invalid_login(self):
        """Test login with invalid credentials"""
        invalid_data = {
            "email": "nonexistent@test.com",
            "password": "wrongpassword"
        }
        
        success, _ = self.run_test(
            "Invalid Login",
            "POST",
            "auth/login",
            401,
            data=invalid_data
        )
        
        # For this test, success means we got 401 as expected
        self.log_test("Invalid Login", success)
        return success

    def test_protected_endpoint_without_token(self):
        """Test accessing protected endpoint without token"""
        # Temporarily remove token
        original_token = self.token
        self.token = None
        
        success, _ = self.run_test(
            "Protected Endpoint Without Token",
            "GET",
            "invoices",
            403  # FastAPI returns 403 for missing auth
        )
        
        # Restore token
        self.token = original_token
        
        # For this test, success means we got 403 as expected
        self.log_test("Protected Endpoint Without Token", success)
        return success

    def create_test_invoice_file(self):
        """Create a simple test XML file that mimics an invoice"""
        # Create a simple XML file that mimics an invoice
        invoice_content = """<?xml version="1.0" encoding="UTF-8"?>
<Invoice>
    <InvoiceNumber>INV-2024-001</InvoiceNumber>
    <Date>15/01/2024</Date>
    <Customer>Test Müşteri Ltd.</Customer>
    <Description>Test Hizmeti</Description>
    <Amount>1000.00</Amount>
    <VAT>180.00</VAT>
    <Total>1180.00</Total>
</Invoice>"""
        
        return io.BytesIO(invoice_content.encode('utf-8'))

    def test_invoice_upload(self):
        """Test invoice upload functionality"""
        if not self.token:
            self.log_test("Invoice Upload", False, "No token available")
            return False, None
        
        # Create test file
        test_file = self.create_test_invoice_file()
        
        files = {
            'file': ('test_invoice.xml', test_file, 'application/xml')
        }
        
        success, response = self.run_test(
            "Invoice Upload",
            "POST",
            "invoices/upload",
            200,
            files=files
        )
        
        if success and 'id' in response:
            self.log_test("Invoice Upload", True)
            return True, response['id']
        else:
            self.log_test("Invoice Upload", False, "No invoice ID in response or upload failed")
            return False, None

    def test_get_invoices(self):
        """Test getting user's invoices"""
        if not self.token:
            self.log_test("Get Invoices", False, "No token available")
            return False
        
        success, response = self.run_test(
            "Get Invoices",
            "GET",
            "invoices",
            200
        )
        
        if success and isinstance(response, list):
            self.log_test("Get Invoices", True)
            return True
        else:
            self.log_test("Get Invoices", False, "Response is not a list")
            return False

    def test_update_invoice(self, invoice_id):
        """Test updating an invoice"""
        if not self.token or not invoice_id:
            self.log_test("Update Invoice", False, "No token or invoice ID available")
            return False
        
        update_data = {
            "customer_name": "Updated Customer Name",
            "amount": 1500.0,
            "vat": 270.0,
            "total": 1770.0
        }
        
        success, response = self.run_test(
            "Update Invoice",
            "PUT",
            f"invoices/{invoice_id}",
            200,
            data=update_data
        )
        
        if success and response.get('customer_name') == "Updated Customer Name":
            self.log_test("Update Invoice", True)
            return True
        else:
            self.log_test("Update Invoice", False, "Invoice not updated correctly")
            return False

    def test_delete_invoice(self, invoice_id):
        """Test deleting an invoice"""
        if not self.token or not invoice_id:
            self.log_test("Delete Invoice", False, "No token or invoice ID available")
            return False
        
        success, response = self.run_test(
            "Delete Invoice",
            "DELETE",
            f"invoices/{invoice_id}",
            200
        )
        
        if success:
            self.log_test("Delete Invoice", True)
            return True
        else:
            self.log_test("Delete Invoice", False, "Failed to delete invoice")
            return False

    def test_excel_export(self):
        """Test Excel export functionality"""
        if not self.token:
            self.log_test("Excel Export", False, "No token available")
            return False
        
        success, response = self.run_test(
            "Excel Export",
            "GET",
            "invoices/export/excel",
            200,
            response_type='binary'
        )
        
        if success and len(response) > 0:
            self.log_test("Excel Export", True)
            return True
        else:
            self.log_test("Excel Export", False, "No Excel file content received")
            return False

    def run_all_tests(self):
        """Run all tests in sequence"""
        print("🚀 Starting Invoice Management API Tests")
        print(f"📍 Base URL: {self.base_url}")
        print("=" * 60)
        
        # Authentication Tests
        print("\n📋 AUTHENTICATION TESTS")
        print("-" * 30)
        
        if not self.test_auth_register():
            print("❌ Registration failed, stopping tests")
            return False
        
        if not self.test_auth_login():
            print("❌ Login failed, stopping tests")
            return False
        
        self.test_auth_me()
        self.test_invalid_login()
        self.test_protected_endpoint_without_token()
        
        # Invoice Tests
        print("\n📋 INVOICE MANAGEMENT TESTS")
        print("-" * 30)
        
        # Upload invoice and get ID for subsequent tests
        upload_success, invoice_id = self.test_invoice_upload()
        
        self.test_get_invoices()
        
        if upload_success and invoice_id:
            self.test_update_invoice(invoice_id)
            # Don't delete immediately, test export first
            
        self.test_excel_export()
        
        # Clean up - delete the test invoice
        if upload_success and invoice_id:
            self.test_delete_invoice(invoice_id)
        
        # Print summary
        print("\n" + "=" * 60)
        print("📊 TEST SUMMARY")
        print(f"✅ Passed: {self.tests_passed}/{self.tests_run}")
        print(f"❌ Failed: {self.tests_run - self.tests_passed}/{self.tests_run}")
        
        if self.tests_passed == self.tests_run:
            print("🎉 All tests passed!")
            return True
        else:
            print("⚠️  Some tests failed. Check details above.")
            return False

def main():
    tester = InvoiceAPITester()
    success = tester.run_all_tests()
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())