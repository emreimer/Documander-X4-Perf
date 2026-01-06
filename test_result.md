#====================================================================================================
# START - Testing Protocol - DO NOT EDIT OR REMOVE THIS SECTION
#====================================================================================================

# THIS SECTION CONTAINS CRITICAL TESTING INSTRUCTIONS FOR BOTH AGENTS
# BOTH MAIN_AGENT AND TESTING_AGENT MUST PRESERVE THIS ENTIRE BLOCK

# Communication Protocol:
# If the `testing_agent` is available, main agent should delegate all testing tasks to it.
#
# You have access to a file called `test_result.md`. This file contains the complete testing state
# and history, and is the primary means of communication between main and the testing agent.
#
# Main and testing agents must follow this exact format to maintain testing data. 
# The testing data must be entered in yaml format Below is the data structure:
# 
## user_problem_statement: {problem_statement}
## backend:
##   - task: "Task name"
##     implemented: true
##     working: true  # or false or "NA"
##     file: "file_path.py"
##     stuck_count: 0
##     priority: "high"  # or "medium" or "low"
##     needs_retesting: false
##     status_history:
##         -working: true  # or false or "NA"
##         -agent: "main"  # or "testing" or "user"
##         -comment: "Detailed comment about status"
##
## frontend:
##   - task: "Task name"
##     implemented: true
##     working: true  # or false or "NA"
##     file: "file_path.js"
##     stuck_count: 0
##     priority: "high"  # or "medium" or "low"
##     needs_retesting: false
##     status_history:
##         -working: true  # or false or "NA"
##         -agent: "main"  # or "testing" or "user"
##         -comment: "Detailed comment about status"
##
## metadata:
##   created_by: "main_agent"
##   version: "1.0"
##   test_sequence: 0
##   run_ui: false
##
## test_plan:
##   current_focus:
##     - "Task name 1"
##     - "Task name 2"
##   stuck_tasks:
##     - "Task name with persistent issues"
##   test_all: false
##   test_priority: "high_first"  # or "sequential" or "stuck_first"
##
## agent_communication:
##     -agent: "main"  # or "testing" or "user"
##     -message: "Communication message between agents"

# Protocol Guidelines for Main agent
#
# 1. Update Test Result File Before Testing:
#    - Main agent must always update the `test_result.md` file before calling the testing agent
#    - Add implementation details to the status_history
#    - Set `needs_retesting` to true for tasks that need testing
#    - Update the `test_plan` section to guide testing priorities
#    - Add a message to `agent_communication` explaining what you've done
#
# 2. Incorporate User Feedback:
#    - When a user provides feedback that something is or isn't working, add this information to the relevant task's status_history
#    - Update the working status based on user feedback
#    - If a user reports an issue with a task that was marked as working, increment the stuck_count
#    - Whenever user reports issue in the app, if we have testing agent and task_result.md file so find the appropriate task for that and append in status_history of that task to contain the user concern and problem as well 
#
# 3. Track Stuck Tasks:
#    - Monitor which tasks have high stuck_count values or where you are fixing same issue again and again, analyze that when you read task_result.md
#    - For persistent issues, use websearch tool to find solutions
#    - Pay special attention to tasks in the stuck_tasks list
#    - When you fix an issue with a stuck task, don't reset the stuck_count until the testing agent confirms it's working
#
# 4. Provide Context to Testing Agent:
#    - When calling the testing agent, provide clear instructions about:
#      - Which tasks need testing (reference the test_plan)
#      - Any authentication details or configuration needed
#      - Specific test scenarios to focus on
#      - Any known issues or edge cases to verify
#
# 5. Call the testing agent with specific instructions referring to test_result.md
#
# IMPORTANT: Main agent must ALWAYS update test_result.md BEFORE calling the testing agent, as it relies on this file to understand what to test next.

#====================================================================================================
# END - Testing Protocol - DO NOT EDIT OR REMOVE THIS SECTION
#====================================================================================================



#====================================================================================================
# Testing Data - Main Agent and testing sub agent both should log testing data below this section
#====================================================================================================
## Test Session: 2025-12-16
### New Features to Test:

#### Feature 1: Reset All Invoices Button
- **Location**: Dashboard header, next to "Excel İndir" button
- **Endpoint**: DELETE /api/invoices
- **Behavior**: 
  - Shows confirmation dialog before deleting
  - Deletes all invoices for current user
  - Button is disabled when no invoices exist
  - Shows success toast after deletion

#### Feature 2: Excel Export with Subtotals
- **Location**: Dashboard header, "Excel İndir" button
- **Endpoint**: GET /api/invoices/export/excel
- **Expected Excel structure**:
  - GELİR FATURALARI section with subtotal row
  - GİDER FATURALARI section with subtotal row
  - Turkish number format (1.234,56)
  - Subtotal rows highlighted in light green

### Test Credentials:
- Email: muhasebe2@test.com
- Password: test123456

### agent_communication:
- agent: main
- message: Implemented two new features - reset all invoices button and Excel subtotals. Backend endpoints working. Frontend has new button. Need to test full flow.

## Test Session: 2025-12-16 - Session Management Feature
### New Features to Test:

#### Feature 1: Taxpayer Session Management
- **Create Session**: POST /api/sessions - creates new taxpayer session with name, year, month
- **Get Current Session**: GET /api/sessions/current
- **Delete Session**: DELETE /api/sessions
- **UI**: Session form modal for entering taxpayer name and selecting year/month
- **Dashboard Title**: Shows taxpayer name and period (e.g., "Test Mükellef - ARALIK 2025")

#### Feature 2: Invoice Date Validation
- When uploading invoices, system validates that invoice date matches selected period
- If date doesn't match, invoice is rejected with warning message
- Response includes `date_mismatches` array with rejected files

#### Feature 3: Dynamic Excel Filename
- Excel filename format: `{taxpayer_name}-{year}-{month}.xlsx`
- Example: `Test_Mukellef-2025-12.xlsx`

### Test Credentials:
- Email: muhasebe2@test.com
- Password: test123456

### agent_communication:
- agent: main
- message: Added taxpayer session management. Dashboard now shows taxpayer name and period. Excel filename is dynamic. Invoice date validation added.

## Test Session: 2025-12-18 - Subscription System Implementation
### New Features to Test:

#### Feature 1: Subscription Plans API
- **GET /api/subscription/plans**: Returns all available plans with pricing
- **Plans**: trial (20 free), starter (₺699, 1000), professional (₺1399, 2500), business (₺2399, 5000), enterprise (₺3999, 10000), unlimited (contact)
- **Annual pricing**: 10 months = 2 months free

#### Feature 2: Subscription Status API
- **GET /api/subscription/status**: Returns user's current subscription status
- **Fields**: plan, plan_name, monthly_limit, monthly_uploads, remaining, is_trial, trial_used
- Auto-creates trial subscription for new users (20 free invoices)
- Monthly counter resets on new month for paid plans

#### Feature 3: Upload Limit Enforcement
- **POST /api/invoices/upload**: Now checks subscription limits before processing
- Returns 403 error with message when limit exceeded
- Increments upload counter after successful upload
- Returns remaining_quota and quota_warning in response

#### Feature 4: Frontend Subscription UI
- **Quota Badge**: Shows current plan and remaining quota in header
- **Plans Modal**: Opens when clicking quota badge, shows all plans with pricing
- **Trial Info**: Shows remaining trial invoices
- **Low Quota Warning**: Toast notification when remaining < 5

### Test Scenarios:
1. New user gets trial plan with 20 free invoices
2. Quota badge shows correct plan and remaining count
3. Plans modal displays all plans with correct pricing
4. Upload limit is enforced (try uploading when limit reached)
5. Counter increments after successful upload

### agent_communication:
- agent: main
- message: Implemented subscription system with trial (20 free), 5 paid plans. Backend enforces limits on upload. Frontend shows quota badge and plans modal. All APIs working. Need comprehensive testing.

## Test Session: 2026-01-06 - PDF Upload Functionality Testing
### PDF Upload Test Results:

#### Backend Testing Results:
- **Authentication**: ✅ WORKING - User registration and login successful
- **Taxpayer Session**: ✅ WORKING - Session creation and management working
- **PDF Upload Endpoint**: ✅ WORKING - POST /api/invoices/upload accepts PDF files
- **File Processing**: ✅ WORKING - PDF files are processed and stored
- **Subscription Limits**: ✅ WORKING - Upload quota tracking functional

#### Critical Issue Identified:
- **AI Extraction**: ❌ FAILING - PDF to image conversion produces unreadable images
- **Root Cause**: The programmatically generated PDF content doesn't render text properly when converted to images for LLM processing
- **LLM Integration**: ✅ WORKING - When provided with readable images, LLM extracts data correctly in JSON format
- **API Keys**: ✅ WORKING - Both EMERGENT_LLM_KEY and OPENAI_API_KEY configured correctly

#### Technical Details:
- PDF to image conversion using pdf2image library works
- Generated images have proper dimensions (1275x1650) and format
- LLM responds with "cannot analyze the image" because text is not visible in converted images
- When tested with PIL-generated text images, LLM extraction works perfectly

#### Test Evidence:
- Created comprehensive test suite (/app/pdf_upload_test.py)
- Isolated PDF conversion testing (/app/test_pdf_conversion.py)
- LLM integration testing (/app/test_llm_with_text_image.py)
- All tests demonstrate the specific failure point in PDF text rendering

### agent_communication:
- agent: testing
- message: PDF upload functionality partially working. File upload, authentication, session management all functional. Critical issue: AI extraction fails because PDF-to-image conversion doesn't produce readable text. LLM integration itself works correctly when given proper images. Need to fix PDF text rendering or use alternative approach for text extraction.
