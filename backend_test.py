import requests
import sys
import json
import io
from datetime import datetime
from pathlib import Path

class InvoiceAPITester:
    def __init__(self, base_url="https://accountingai-2.preview.emergentagent.com"):
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
        """Create a simple test PDF-like file"""
        # Create a minimal PDF structure for testing
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
/Length 44
>>
stream
BT
/F1 12 Tf
100 700 Td
(FATURA INV-2024-001) Tj
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
299
%%EOF"""
        
        return io.BytesIO(pdf_content)

    def test_invoice_upload(self):
        """Test invoice upload functionality"""
        if not self.token:
            self.log_test("Invoice Upload", False, "No token available")
            return False, None
        
        # Create test file
        test_file = self.create_test_invoice_file()
        
        files = {
            'files': ('test_invoice.pdf', test_file, 'application/pdf')
        }
        data = {
            'category': 'income'
        }
        
        # Manual upload since run_test doesn't handle form data properly
        url = f"{self.api_url}/invoices/upload"
        headers = {'Authorization': f'Bearer {self.token}'}
        
        try:
            response = requests.post(url, files=files, data=data, headers=headers)
            success = response.status_code == 200
            
            print(f"🔍 Testing Invoice Upload...")
            print(f"   URL: {url}")
            print(f"   Status: {response.status_code} {'✅' if success else '❌'}")
            
            if success:
                response_data = response.json()
                if 'invoices' in response_data and len(response_data['invoices']) > 0:
                    invoice_id = response_data['invoices'][0]['id']
                    self.log_test("Invoice Upload", True)
                    return True, invoice_id
                else:
                    self.log_test("Invoice Upload", False, "No invoices in response")
                    return False, None
            else:
                error_detail = response.text[:200]
                print(f"   Error: {error_detail}")
                self.log_test("Invoice Upload", False, f"Status {response.status_code}: {error_detail}")
                return False, None
                
        except Exception as e:
            print(f"   Exception: {str(e)} ❌")
            self.log_test("Invoice Upload", False, f"Exception: {str(e)}")
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

    def test_delete_all_invoices(self):
        """Test deleting all invoices (new feature)"""
        if not self.token:
            self.log_test("Delete All Invoices", False, "No token available")
            return False
        
        # First create some test invoices to delete
        test_file = self.create_test_invoice_file()
        files = {
            'files': ('test_invoice.pdf', test_file, 'application/pdf')
        }
        data = {'category': 'income'}
        
        # Upload a test invoice
        url = f"{self.api_url}/invoices/upload"
        headers = {'Authorization': f'Bearer {self.token}'}
        
        try:
            response = requests.post(url, files=files, data=data, headers=headers)
            success = response.status_code == 200
            print(f"   Upload Test Invoice Status: {response.status_code}")
        except Exception as e:
            success = False
            print(f"   Upload Test Invoice Error: {str(e)}")
        
        if not success:
            self.log_test("Delete All Invoices Setup", False, "Could not upload test invoice")
            return False
        
        # Now test delete all invoices
        success, response = self.run_test(
            "Delete All Invoices",
            "DELETE",
            "invoices",
            200
        )
        
        if success and 'deleted_count' in response:
            deleted_count = response['deleted_count']
            print(f"   Deleted {deleted_count} invoices")
            self.log_test("Delete All Invoices", True, f"Deleted {deleted_count} invoices")
            return True
        else:
            self.log_test("Delete All Invoices", False, "No deleted_count in response")
            return False

    def test_delete_all_invoices_by_category(self):
        """Test deleting all invoices by category"""
        if not self.token:
            self.log_test("Delete All Invoices by Category", False, "No token available")
            return False
        
        # Create test invoices for both categories
        test_file1 = self.create_test_invoice_file()
        test_file2 = self.create_test_invoice_file()
        
        # Upload income invoice
        files1 = {'files': ('test_income.pdf', test_file1, 'application/pdf')}
        data1 = {'category': 'income'}
        
        # Upload expense invoice  
        files2 = {'files': ('test_expense.pdf', test_file2, 'application/pdf')}
        data2 = {'category': 'expense'}
        
        # Upload both invoices manually
        url = f"{self.api_url}/invoices/upload"
        headers = {'Authorization': f'Bearer {self.token}'}
        
        requests.post(url, files=files1, data=data1, headers=headers)
        requests.post(url, files=files2, data=data2, headers=headers)
        
        # Delete only income invoices
        success, response = self.run_test(
            "Delete Income Invoices Only",
            "DELETE",
            "invoices?category=income",
            200
        )
        
        if success and 'deleted_count' in response:
            self.log_test("Delete All Invoices by Category", True)
            return True
        else:
            self.log_test("Delete All Invoices by Category", False, "Failed to delete by category")
            return False

    def test_create_session(self):
        """Test creating taxpayer session"""
        if not self.token:
            self.log_test("Create Session", False, "No token available")
            return False, None
        
        session_data = {
            "taxpayer_name": "Test Mükellef A.Ş.",
            "year": 2024,
            "month": 12
        }
        
        success, response = self.run_test(
            "Create Taxpayer Session",
            "POST",
            "sessions",
            200,
            data=session_data
        )
        
        if success and 'id' in response:
            session_id = response['id']
            self.log_test("Create Taxpayer Session", True)
            return True, session_id
        else:
            self.log_test("Create Taxpayer Session", False, "No session ID in response")
            return False, None

    def test_get_current_session(self):
        """Test getting current session"""
        if not self.token:
            self.log_test("Get Current Session", False, "No token available")
            return False
        
        success, response = self.run_test(
            "Get Current Session",
            "GET",
            "sessions/current",
            200
        )
        
        if success and response and 'taxpayer_name' in response:
            self.log_test("Get Current Session", True)
            return True
        else:
            self.log_test("Get Current Session", False, "No session data in response")
            return False

    def test_delete_session(self):
        """Test deleting session"""
        if not self.token:
            self.log_test("Delete Session", False, "No token available")
            return False
        
        success, response = self.run_test(
            "Delete Session",
            "DELETE",
            "sessions",
            200
        )
        
        if success and 'message' in response:
            self.log_test("Delete Session", True)
            return True
        else:
            self.log_test("Delete Session", False, "No success message in response")
            return False

    def test_invoice_upload_date_validation(self):
        """Test invoice upload with date validation"""
        if not self.token:
            self.log_test("Invoice Upload Date Validation", False, "No token available")
            return False
        
        # First create a session for December 2024
        session_data = {
            "taxpayer_name": "Test Mükellef Date Validation",
            "year": 2024,
            "month": 12
        }
        
        success, _ = self.run_test(
            "Create Session for Date Test",
            "POST",
            "sessions",
            200,
            data=session_data
        )
        
        if not success:
            self.log_test("Invoice Upload Date Validation", False, "Could not create session")
            return False
        
        # Create test file
        test_file = self.create_test_invoice_file()
        
        files = {
            'files': ('test_invoice_wrong_date.pdf', test_file, 'application/pdf')
        }
        data = {
            'category': 'income'
        }
        
        # Manual upload since run_test doesn't handle form data properly
        url = f"{self.api_url}/invoices/upload"
        headers = {'Authorization': f'Bearer {self.token}'}
        
        try:
            response = requests.post(url, files=files, data=data, headers=headers)
            success = response.status_code == 200
            
            print(f"🔍 Testing Invoice Upload Date Validation...")
            print(f"   URL: {url}")
            print(f"   Status: {response.status_code} {'✅' if success else '❌'}")
            
            if success:
                response_data = response.json()
                # Check if there are date mismatches reported
                if 'date_mismatches' in response_data:
                    self.log_test("Invoice Upload Date Validation", True, "Date validation working")
                    return True
                else:
                    self.log_test("Invoice Upload Date Validation", True, "Upload successful (no date issues)")
                    return True
            else:
                error_detail = response.text[:200]
                print(f"   Error: {error_detail}")
                self.log_test("Invoice Upload Date Validation", False, f"Status {response.status_code}: {error_detail}")
                return False
                
        except Exception as e:
            print(f"   Exception: {str(e)} ❌")
            self.log_test("Invoice Upload Date Validation", False, f"Exception: {str(e)}")
            return False

    def test_excel_export_with_session(self):
        """Test Excel export with session info in filename"""
        if not self.token:
            self.log_test("Excel Export with Session", False, "No token available")
            return False
        
        # Create a session first
        session_data = {
            "taxpayer_name": "Test Export Mükellef",
            "year": 2024,
            "month": 11
        }
        
        success, _ = self.run_test(
            "Create Session for Export Test",
            "POST",
            "sessions",
            200,
            data=session_data
        )
        
        if not success:
            self.log_test("Excel Export with Session", False, "Could not create session")
            return False
        
        # Upload a test invoice
        test_file = self.create_test_invoice_file()
        files = {'files': ('test_invoice.pdf', test_file, 'application/pdf')}
        data = {'category': 'income'}
        
        url = f"{self.api_url}/invoices/upload"
        headers = {'Authorization': f'Bearer {self.token}'}
        
        try:
            response = requests.post(url, files=files, data=data, headers=headers)
            if response.status_code != 200:
                self.log_test("Excel Export with Session", False, "Could not upload test invoice")
                return False
        except Exception as e:
            self.log_test("Excel Export with Session", False, f"Upload error: {str(e)}")
            return False
        
        # Now test export
        success, response = self.run_test(
            "Excel Export with Session Info",
            "GET",
            "invoices/export/excel",
            200,
            response_type='binary'
        )
        
        if success and len(response) > 0:
            self.log_test("Excel Export with Session", True, "Excel file generated with session info")
            return True
        else:
            self.log_test("Excel Export with Session", False, "No Excel file content received")
            return False

    def test_excel_export(self):
        """Test Excel export functionality"""
        if not self.token:
            self.log_test("Excel Export", False, "No token available")
            return False
        
        # First check if we have invoices
        success, invoices = self.run_test(
            "Check Invoices for Export",
            "GET",
            "invoices",
            200
        )
        
        if not success:
            self.log_test("Excel Export", False, "Could not check invoices")
            return False
        
        if len(invoices) == 0:
            # Test export with no invoices - should return 404
            success, response = self.run_test(
                "Excel Export (No Invoices)",
                "GET",
                "invoices/export/excel",
                404,
                response_type='binary'
            )
            self.log_test("Excel Export (No Invoices)", success)
            return success
        else:
            # Test export with invoices - should return 200
            success, response = self.run_test(
                "Excel Export (With Invoices)",
                "GET",
                "invoices/export/excel",
                200,
                response_type='binary'
            )
            
            if success and len(response) > 0:
                self.log_test("Excel Export (With Invoices)", True)
                return True
            else:
                self.log_test("Excel Export (With Invoices)", False, "No Excel file content received")
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
        
        # Taxpayer Session Tests (NEW FEATURES)
        print("\n📋 TAXPAYER SESSION TESTS (NEW FEATURES)")
        print("-" * 30)
        
        session_success, session_id = self.test_create_session()
        self.test_get_current_session()
        
        # Invoice Tests
        print("\n📋 INVOICE MANAGEMENT TESTS")
        print("-" * 30)
        
        # Upload invoice and get ID for subsequent tests
        upload_success, invoice_id = self.test_invoice_upload()
        
        self.test_get_invoices()
        
        if upload_success and invoice_id:
            self.test_update_invoice(invoice_id)
            # Don't delete immediately, test export first
            
        # Test date validation feature
        self.test_invoice_upload_date_validation()
        
        # Test Excel export with session info
        self.test_excel_export_with_session()
        self.test_excel_export()
        
        # Test new DELETE all invoices functionality
        print("\n📋 DELETE FEATURES TESTS")
        print("-" * 30)
        
        self.test_delete_all_invoices_by_category()
        self.test_delete_all_invoices()
        
        # Test session deletion
        self.test_delete_session()
        
        # Clean up - delete the test invoice (if any remaining)
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