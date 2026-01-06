#!/usr/bin/env python3
"""
PDF Upload Test for Invoice Extraction
Tests the specific PDF upload functionality as requested in the review.
"""

import requests
import json
import io
from datetime import datetime
import sys

class PDFUploadTester:
    def __init__(self):
        self.base_url = "https://bundan-basla.preview.emergentagent.com"
        self.api_url = f"{self.base_url}/api"
        self.token = None
        self.user_id = None
        self.session_id = None
        
    def log_result(self, test_name, success, details=""):
        """Log test result with clear formatting"""
        status = "✅ PASSED" if success else "❌ FAILED"
        print(f"{status}: {test_name}")
        if details:
            print(f"   Details: {details}")
        print()
        
    def register_user(self):
        """Step 1: Register a new user"""
        print("🔐 Step 1: User Registration")
        
        test_email = f"pdftest@test.com"
        user_data = {
            "email": test_email,
            "password": "test123456",
            "full_name": "PDF Test User"
        }
        
        try:
            response = requests.post(f"{self.api_url}/auth/register", json=user_data)
            
            if response.status_code == 200:
                data = response.json()
                self.token = data.get('token')
                self.user_id = data.get('user', {}).get('id')
                self.log_result("User Registration", True, f"Token obtained, User ID: {self.user_id}")
                return True
            elif response.status_code == 400 and "already registered" in response.text:
                # User already exists, try login
                return self.login_user()
            else:
                self.log_result("User Registration", False, f"Status: {response.status_code}, Response: {response.text[:200]}")
                return False
                
        except Exception as e:
            self.log_result("User Registration", False, f"Exception: {str(e)}")
            return False
    
    def login_user(self):
        """Alternative: Login with existing user"""
        print("🔐 Step 1b: User Login (fallback)")
        
        login_data = {
            "email": "pdftest@test.com",
            "password": "test123456"
        }
        
        try:
            response = requests.post(f"{self.api_url}/auth/login", json=login_data)
            
            if response.status_code == 200:
                data = response.json()
                self.token = data.get('token')
                self.user_id = data.get('user', {}).get('id')
                self.log_result("User Login", True, f"Token obtained, User ID: {self.user_id}")
                return True
            else:
                self.log_result("User Login", False, f"Status: {response.status_code}, Response: {response.text[:200]}")
                return False
                
        except Exception as e:
            self.log_result("User Login", False, f"Exception: {str(e)}")
            return False
    
    def create_taxpayer_session(self):
        """Step 2: Create a taxpayer session"""
        print("📋 Step 2: Create Taxpayer Session")
        
        if not self.token:
            self.log_result("Create Taxpayer Session", False, "No authentication token")
            return False
        
        session_data = {
            "taxpayer_name": "Test Mükellef",
            "year": 2025,
            "month": 1
        }
        
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }
        
        try:
            response = requests.post(f"{self.api_url}/sessions", json=session_data, headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                self.session_id = data.get('id')
                self.log_result("Create Taxpayer Session", True, f"Session ID: {self.session_id}")
                return True
            else:
                self.log_result("Create Taxpayer Session", False, f"Status: {response.status_code}, Response: {response.text[:200]}")
                return False
                
        except Exception as e:
            self.log_result("Create Taxpayer Session", False, f"Exception: {str(e)}")
            return False
    
    def create_test_pdf(self):
        """Step 3: Create a simple test PDF with invoice-like content"""
        print("📄 Step 3: Create Test PDF")
        
        # Create a more realistic PDF with invoice content
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
        
        self.log_result("Create Test PDF", True, "PDF with invoice content created")
        return io.BytesIO(pdf_content)
    
    def upload_pdf(self):
        """Step 4: Upload the PDF and test extraction"""
        print("📤 Step 4: Upload PDF for Invoice Extraction")
        
        if not self.token:
            self.log_result("PDF Upload", False, "No authentication token")
            return False
        
        # Create test PDF
        test_pdf = self.create_test_pdf()
        
        # Prepare upload
        files = {
            'files': ('test_invoice.pdf', test_pdf, 'application/pdf')
        }
        data = {
            'category': 'income'
        }
        headers = {
            "Authorization": f"Bearer {self.token}"
        }
        
        try:
            print(f"   Uploading to: {self.api_url}/invoices/upload")
            response = requests.post(f"{self.api_url}/invoices/upload", files=files, data=data, headers=headers)
            
            print(f"   Response Status: {response.status_code}")
            
            if response.status_code == 200:
                response_data = response.json()
                print(f"   Response Data: {json.dumps(response_data, indent=2)}")
                
                # Check if invoices were extracted
                if 'invoices' in response_data and len(response_data['invoices']) > 0:
                    invoice = response_data['invoices'][0]
                    extracted_details = {
                        'invoice_number': invoice.get('invoice_number', 'N/A'),
                        'date': invoice.get('date', 'N/A'),
                        'issuer_name': invoice.get('issuer_name', 'N/A'),
                        'amount': invoice.get('amount', 0),
                        'vat': invoice.get('vat', 0),
                        'total': invoice.get('total', 0)
                    }
                    
                    self.log_result("PDF Upload and Extraction", True, 
                                  f"Invoice extracted successfully: {json.dumps(extracted_details, indent=2)}")
                    return True, response_data
                else:
                    self.log_result("PDF Upload and Extraction", False, 
                                  f"No invoices extracted from PDF. Response: {response_data}")
                    return False, response_data
            else:
                error_text = response.text[:500]
                self.log_result("PDF Upload and Extraction", False, 
                              f"Status: {response.status_code}, Error: {error_text}")
                return False, {}
                
        except Exception as e:
            self.log_result("PDF Upload and Extraction", False, f"Exception: {str(e)}")
            return False, {}
    
    def verify_invoice_data(self, upload_response):
        """Step 5: Verify the extracted invoice data"""
        print("🔍 Step 5: Verify Extracted Invoice Data")
        
        if not self.token:
            self.log_result("Verify Invoice Data", False, "No authentication token")
            return False
        
        headers = {
            "Authorization": f"Bearer {self.token}"
        }
        
        try:
            # Get all invoices
            response = requests.get(f"{self.api_url}/invoices", headers=headers)
            
            if response.status_code == 200:
                invoices = response.json()
                
                if len(invoices) > 0:
                    latest_invoice = invoices[-1]  # Get the latest invoice
                    
                    # Verify key fields are extracted
                    verification_results = {
                        'has_invoice_number': bool(latest_invoice.get('invoice_number') and latest_invoice.get('invoice_number') != 'N/A'),
                        'has_date': bool(latest_invoice.get('date') and latest_invoice.get('date') != 'N/A'),
                        'has_issuer_name': bool(latest_invoice.get('issuer_name') and latest_invoice.get('issuer_name') != 'N/A'),
                        'has_amounts': bool(latest_invoice.get('amount', 0) > 0 or latest_invoice.get('total', 0) > 0),
                        'invoice_data': latest_invoice
                    }
                    
                    success = any([verification_results['has_invoice_number'], 
                                 verification_results['has_date'],
                                 verification_results['has_issuer_name'],
                                 verification_results['has_amounts']])
                    
                    self.log_result("Verify Invoice Data", success, 
                                  f"Verification results: {json.dumps(verification_results, indent=2)}")
                    return success
                else:
                    self.log_result("Verify Invoice Data", False, "No invoices found in database")
                    return False
            else:
                self.log_result("Verify Invoice Data", False, 
                              f"Failed to get invoices. Status: {response.status_code}")
                return False
                
        except Exception as e:
            self.log_result("Verify Invoice Data", False, f"Exception: {str(e)}")
            return False
    
    def check_backend_logs(self):
        """Check backend logs for PDF processing errors"""
        print("📋 Step 6: Check Backend Logs for PDF Processing")
        
        try:
            import subprocess
            result = subprocess.run(['tail', '-n', '20', '/var/log/supervisor/backend.err.log'], 
                                  capture_output=True, text=True)
            
            if result.returncode == 0:
                logs = result.stdout
                
                # Check for PDF-related errors
                pdf_errors = []
                for line in logs.split('\n'):
                    if any(keyword in line.lower() for keyword in ['pdf', 'poppler', 'pdf2image', 'conversion']):
                        pdf_errors.append(line.strip())
                
                if pdf_errors:
                    self.log_result("Backend Logs Check", False, 
                                  f"PDF processing errors found:\n" + "\n".join(pdf_errors))
                    return False
                else:
                    self.log_result("Backend Logs Check", True, "No PDF processing errors in recent logs")
                    return True
            else:
                self.log_result("Backend Logs Check", False, "Could not read backend logs")
                return False
                
        except Exception as e:
            self.log_result("Backend Logs Check", False, f"Exception: {str(e)}")
            return False
    
    def run_pdf_upload_test(self):
        """Run the complete PDF upload test sequence"""
        print("🚀 PDF Upload Functionality Test")
        print("=" * 50)
        print(f"Backend URL: {self.base_url}")
        print(f"API URL: {self.api_url}")
        print()
        
        # Test sequence
        test_results = []
        
        # Step 1: Authentication
        if self.register_user():
            test_results.append(("Authentication", True))
        else:
            test_results.append(("Authentication", False))
            print("❌ Authentication failed. Cannot proceed with PDF upload test.")
            return False
        
        # Step 2: Create session
        if self.create_taxpayer_session():
            test_results.append(("Taxpayer Session", True))
        else:
            test_results.append(("Taxpayer Session", False))
            print("❌ Session creation failed. Cannot proceed with PDF upload test.")
            return False
        
        # Step 3 & 4: PDF Upload and Extraction
        upload_success, upload_response = self.upload_pdf()
        test_results.append(("PDF Upload & Extraction", upload_success))
        
        # Step 5: Verify extracted data
        if upload_success:
            verify_success = self.verify_invoice_data(upload_response)
            test_results.append(("Data Verification", verify_success))
        else:
            test_results.append(("Data Verification", False))
        
        # Step 6: Check logs
        log_check = self.check_backend_logs()
        test_results.append(("Backend Logs", log_check))
        
        # Summary
        print("=" * 50)
        print("📊 PDF UPLOAD TEST SUMMARY")
        print("=" * 50)
        
        passed = 0
        total = len(test_results)
        
        for test_name, success in test_results:
            status = "✅ PASSED" if success else "❌ FAILED"
            print(f"{status}: {test_name}")
            if success:
                passed += 1
        
        print()
        print(f"Overall Result: {passed}/{total} tests passed")
        
        if passed == total:
            print("🎉 PDF upload functionality is working correctly!")
            return True
        else:
            print("⚠️ PDF upload functionality has issues that need attention.")
            return False

def main():
    tester = PDFUploadTester()
    success = tester.run_pdf_upload_test()
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())