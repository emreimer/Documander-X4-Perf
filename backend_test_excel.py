import requests
import sys
import json
import io
from datetime import datetime
from pathlib import Path

class ExcelExportTester:
    def __init__(self, base_url="https://accountingai-2.preview.emergentagent.com"):
        self.base_url = base_url
        self.api_url = f"{base_url}/api"
        self.visitor_id = f"test_visitor_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
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
        """Run a single API test with visitor_id authentication"""
        url = f"{self.api_url}/{endpoint}"
        headers = {'X-Visitor-ID': self.visitor_id}
        
        if not files:
            headers['Content-Type'] = 'application/json'

        print(f"\n🔍 Testing {name}...")
        print(f"   URL: {url}")
        print(f"   Visitor ID: {self.visitor_id}")
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers)
            elif method == 'POST':
                if files:
                    response = requests.post(url, files=files, data=data, headers=headers)
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

    def test_create_session(self):
        """Test creating taxpayer session with visitor_id"""
        session_data = {
            "taxpayer_name": "Test Mükellef Excel",
            "year": 2024,
            "month": 12
        }
        
        success, response = self.run_test(
            "Create Taxpayer Session (Visitor ID)",
            "POST",
            "sessions",
            200,
            data=session_data
        )
        
        if success and 'id' in response:
            session_id = response['id']
            self.log_test("Create Taxpayer Session (Visitor ID)", True)
            return True, session_id
        else:
            self.log_test("Create Taxpayer Session (Visitor ID)", False, "No session ID in response")
            return False, None

    def test_get_current_session(self):
        """Test getting current session with visitor_id"""
        success, response = self.run_test(
            "Get Current Session (Visitor ID)",
            "GET",
            "sessions/current",
            200
        )
        
        if success and response and 'taxpayer_name' in response:
            self.log_test("Get Current Session (Visitor ID)", True)
            return True
        else:
            self.log_test("Get Current Session (Visitor ID)", False, "No session data in response")
            return False

    def create_test_invoice_file(self):
        """Create a simple test PDF-like file"""
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

    def test_invoice_upload(self, category='income'):
        """Test invoice upload functionality with visitor_id"""
        # Create test file
        test_file = self.create_test_invoice_file()
        
        files = {
            'files': (f'test_invoice_{category}.pdf', test_file, 'application/pdf')
        }
        data = {
            'category': category
        }
        
        # Manual upload since run_test doesn't handle form data properly
        url = f"{self.api_url}/invoices/upload"
        headers = {'X-Visitor-ID': self.visitor_id}
        
        try:
            response = requests.post(url, files=files, data=data, headers=headers)
            success = response.status_code == 200
            
            print(f"🔍 Testing Invoice Upload ({category})...")
            print(f"   URL: {url}")
            print(f"   Status: {response.status_code} {'✅' if success else '❌'}")
            
            if success:
                response_data = response.json()
                if 'invoices' in response_data and len(response_data['invoices']) > 0:
                    invoice_id = response_data['invoices'][0]['id']
                    self.log_test(f"Invoice Upload ({category})", True)
                    return True, invoice_id
                else:
                    # Check if there are errors or date mismatches
                    errors = response_data.get('errors', [])
                    date_mismatches = response_data.get('date_mismatches', [])
                    if errors or date_mismatches:
                        self.log_test(f"Invoice Upload ({category})", False, f"Errors: {errors}, Date mismatches: {date_mismatches}")
                    else:
                        self.log_test(f"Invoice Upload ({category})", False, "No invoices in response")
                    return False, None
            else:
                error_detail = response.text[:200]
                print(f"   Error: {error_detail}")
                self.log_test(f"Invoice Upload ({category})", False, f"Status {response.status_code}: {error_detail}")
                return False, None
                
        except Exception as e:
            print(f"   Exception: {str(e)} ❌")
            self.log_test(f"Invoice Upload ({category})", False, f"Exception: {str(e)}")
            return False, None

    def test_excel_export_no_invoices(self):
        """Test Excel export when no invoices exist - should return 404"""
        success, response = self.run_test(
            "Excel Export (No Invoices - Should be 404)",
            "GET",
            "invoices/export/excel",
            404,
            response_type='binary'
        )
        
        self.log_test("Excel Export (No Invoices)", success, "Correctly returns 404 when no invoices")
        return success

    def test_excel_export_income_only(self):
        """Test Excel export for income category only"""
        success, response = self.run_test(
            "Excel Export (Income Only)",
            "GET",
            "invoices/export/excel?category=income",
            200,
            response_type='binary'
        )
        
        if success and len(response) > 0:
            self.log_test("Excel Export (Income Only)", True, f"Excel file generated, size: {len(response)} bytes")
            return True
        else:
            self.log_test("Excel Export (Income Only)", False, "No Excel file content received")
            return False

    def test_excel_export_expense_only(self):
        """Test Excel export for expense category only"""
        success, response = self.run_test(
            "Excel Export (Expense Only)",
            "GET",
            "invoices/export/excel?category=expense",
            200,
            response_type='binary'
        )
        
        if success and len(response) > 0:
            self.log_test("Excel Export (Expense Only)", True, f"Excel file generated, size: {len(response)} bytes")
            return True
        else:
            self.log_test("Excel Export (Expense Only)", False, "No Excel file content received")
            return False

    def test_excel_export_all(self):
        """Test Excel export for all invoices"""
        success, response = self.run_test(
            "Excel Export (All Invoices)",
            "GET",
            "invoices/export/excel",
            200,
            response_type='binary'
        )
        
        if success and len(response) > 0:
            self.log_test("Excel Export (All Invoices)", True, f"Excel file generated, size: {len(response)} bytes")
            return True
        else:
            self.log_test("Excel Export (All Invoices)", False, "No Excel file content received")
            return False

    def test_get_invoices(self, category=None):
        """Test getting invoices"""
        endpoint = "invoices"
        if category:
            endpoint += f"?category={category}"
        
        success, response = self.run_test(
            f"Get Invoices ({category or 'All'})",
            "GET",
            endpoint,
            200
        )
        
        if success and isinstance(response, list):
            self.log_test(f"Get Invoices ({category or 'All'})", True, f"Found {len(response)} invoices")
            return True, response
        else:
            self.log_test(f"Get Invoices ({category or 'All'})", False, "Response is not a list")
            return False, []

    def run_excel_focused_tests(self):
        """Run tests focused on Excel export functionality"""
        print("🚀 Starting Excel Export Focused Tests")
        print(f"📍 Base URL: {self.base_url}")
        print(f"🆔 Visitor ID: {self.visitor_id}")
        print("=" * 60)
        
        # Test 1: Create session (required for invoice operations)
        print("\n📋 STEP 1: CREATE TAXPAYER SESSION")
        print("-" * 30)
        session_success, session_id = self.test_create_session()
        if not session_success:
            print("❌ Session creation failed, stopping tests")
            return False
        
        self.test_get_current_session()
        
        # Test 2: Test Excel export with no invoices (should return 404)
        print("\n📋 STEP 2: TEST EXCEL EXPORT WITH NO INVOICES")
        print("-" * 30)
        self.test_excel_export_no_invoices()
        
        # Test 3: Upload income invoices
        print("\n📋 STEP 3: UPLOAD INCOME INVOICES")
        print("-" * 30)
        income_upload_success, income_invoice_id = self.test_invoice_upload('income')
        
        # Test 4: Upload expense invoices
        print("\n📋 STEP 4: UPLOAD EXPENSE INVOICES")
        print("-" * 30)
        expense_upload_success, expense_invoice_id = self.test_invoice_upload('expense')
        
        # Test 5: Check uploaded invoices
        print("\n📋 STEP 5: VERIFY UPLOADED INVOICES")
        print("-" * 30)
        income_get_success, income_invoices = self.test_get_invoices('income')
        expense_get_success, expense_invoices = self.test_get_invoices('expense')
        all_get_success, all_invoices = self.test_get_invoices()
        
        # Test 6: Test Excel exports (the main functionality being tested)
        print("\n📋 STEP 6: TEST EXCEL EXPORTS (MAIN FUNCTIONALITY)")
        print("-" * 30)
        
        # Test income Excel export (GELİR EXCEL button)
        if income_invoices:
            print("Testing 'GELİR EXCEL' button functionality...")
            self.test_excel_export_income_only()
        else:
            print("⚠️ No income invoices to test income Excel export")
        
        # Test expense Excel export (GİDER EXCEL button)
        if expense_invoices:
            print("Testing 'GİDER EXCEL' button functionality...")
            self.test_excel_export_expense_only()
        else:
            print("⚠️ No expense invoices to test expense Excel export")
        
        # Test all Excel export (TÜMÜNÜ EXCEL İNDİR button)
        if all_invoices:
            print("Testing 'TÜMÜNÜ EXCEL İNDİR' button functionality...")
            self.test_excel_export_all()
        else:
            print("⚠️ No invoices to test all Excel export")
        
        # Print summary
        print("\n" + "=" * 60)
        print("📊 EXCEL EXPORT TEST SUMMARY")
        print(f"✅ Passed: {self.tests_passed}/{self.tests_run}")
        print(f"❌ Failed: {self.tests_run - self.tests_passed}/{self.tests_run}")
        
        if self.tests_passed == self.tests_run:
            print("🎉 All Excel export tests passed!")
            return True
        else:
            print("⚠️ Some Excel export tests failed. Check details above.")
            return False

def main():
    tester = ExcelExportTester()
    success = tester.run_excel_focused_tests()
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())