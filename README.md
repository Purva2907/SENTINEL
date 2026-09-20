# SENTINEL - AI-Powered Document Forensics

**Tagline:** Trust the Evidence.
**Hackathon:** MUSA CodeX 2026
**Problem Statement:** CX0203 — The Aadhaar Look-Alike: AI-Powered Document Forensics for Synthetic Aadhaar & PAN Detection.

## SENTINEL
AI-Powered Document Forensics

## Overview
SENTINEL is a forensic document screening and analysis prototype.

SENTINEL is a screening/decision-support system and does not replace official government authentication.

## Features
- document upload
- OCR
- QR analysis
- image quality analysis
- typography analysis
- layout analysis
- image forensics
- deterministic risk scoring
- forensic evidence log
- ELA/heatmap visualization
- case management
- case detail
- PDF reports
- analytics
- AI Assistant
- local fallback assistant
- authentication
- profile management
- dark/light theme

## AI Assistant
SENTINEL includes a context-aware forensic assistant that uses both Results context and Case context to help analyze data. It integrates with OpenAI if configured, but includes a local fallback to operate securely when an API key is not provided.
OpenAI is optional. The local fallback allows the assistant to operate without an API key.

## Synthetic Dataset
The project includes a synthetic dataset at `data/sentinel_dataset/`.
- 10 synthetic documents
- 5 AUTHENTIC_LIKE
- 3 REVIEW_REQUIRED
- 2 HIGH_SUSPICION

No real Aadhaar/PAN documents are used. No real personal data is present.
Generation:
```bash
python data/sentinel_dataset/generate_dataset.py
```

## Authentication
SENTINEL supports standard registration and login.
Do not publish or commit any real or test credentials.

## Environment Variables
The application requires several environment variables for its operation, which you can set in your `.env` file:
- `SECRET_KEY`: JWT signing secret
- `OPENAI_API_KEY`: (Optional) Connects the AI Assistant to OpenAI.

## Local Setup
```bash
# Create a virtual environment
python -m venv venv
venv\Scripts\activate

# Install requirements
pip install -r requirements.txt

# Start backend
cd backend
python -m uvicorn app:app --host 0.0.0.0 --port 8000 --reload

# Start frontend (using a simple HTTP server in a separate terminal)
cd frontend
python -m http.server 3000
```

## Testing
To run the automated tests, ensure your virtual environment is active and execute:
```bash
pytest -q
pytest backend/tests/test_chatbot.py -q
pytest backend/tests/test_dataset.py -q
```

## Architecture
- **Frontend**: Vanilla HTML/CSS/JS interface
- **Backend**: FastAPI
- **Forensic Engine**: Python-based document analyzer (`pipeline.py`)
- **Database**: Supports SQLite and MongoDB for profile, cases, and analysis persistence
- **Authentication**: JWT-based session security
- **AI Assistant**: Context-aware Chatbot for results and cases, with local fallback
- **Reporting**: ReportLab-based PDF generation

## Limitations
- screening aid
- not official authentication
- no direct government database dependency
- synthetic dataset is for testing
- results require human review where indicated

## Demo Workflow
1. Login
2. Upload
3. Analyze
4. Review Evidence
5. Ask SENTINEL AI
6. Save Case
7. Review Case
8. Generate Report
 synthetic or manipulated Aadhaar and PAN documents. It leverages an advanced pipeline of Computer Vision, OCR, and QR analysis to provide a deterministic risk score without claiming to be an official government authentication service.

## Features (P0 & P1 Implementation)

1. **Forensic Analysis Pipeline (P0)**
   - Document Classification & Identification
   - Visual/Image Quality Analysis (Blur, Lighting, Tampering markers)
   - OCR Extraction via EasyOCR
   - QR Code Consistency Checking
   - Risk Scoring Engine (0-100 deterministic risk assessment)
   - Forensic Heatmap Generation

2. **Investigation Platform (P1 & Premium Enhancements)**
   - **Persistent Storage:** MongoDB primary with SQLite fallback.
   - **User Authentication:** JWT-based secure login and registration.
   - **Premium UI / UX:** Polished cybersecurity/forensics aesthetic with persistent Forensic Dark / Clean Light global themes.
   - **Case Management:** Save analysis results as persistent investigation cases.
   - **Dashboards:** Full metrics and analytics visualization using Chart.js.
   - **PDF Reporting:** Automatic forensic evidence PDF report generation via ReportLab.
   - **SENTINEL AI Assistant:** Context-aware local chatbot integrated globally via a floating panel. Connects to OpenAI APIs with a fully functional offline local rule-based fallback system.

3. **QA & Testing Infrastructure**
   - **Synthetic Dataset Generator:** Auto-generates labeled synthetic ID documents with dynamic risk-factors and scannable QR payloads for testing.
   - **Automated Tests:** Comprehensive Pytest suites for testing the forensic APIs, dataset pipeline, and AI assistant logic.
   - **E2E Scaffolding:** Canonical test user injection helpers for scalable browser testing.

## Tech Stack

- **Backend:** Python, FastAPI, Motor (MongoDB), SQLite3, ReportLab, Passlib/Jose
- **Frontend:** HTML5, CSS3, Vanilla JavaScript, Chart.js
- **Machine Learning/CV:** OpenCV, EasyOCR, Pillow, PyZBar, qrcode
- **AI Integrations:** OpenAI API (Python SDK)

## How to Run Locally

1. Create and activate a Python virtual environment:
   ```bash
   python -m venv venv
   .\venv\Scripts\Activate.ps1
   ```

2. Install dependencies:
   ```bash
   pip install -r backend/requirements.txt
   ```

3. (Optional) Generate the Synthetic Testing Dataset:
   ```bash
   python data/sentinel_dataset/generate_dataset.py
   ```

4. Run Backend Tests:
   ```bash
   cd backend
   pytest -q
   ```

5. Ensure MongoDB is running (default `mongodb://localhost:27017`). If unavailable, it will fallback to SQLite automatically.

6. Start the backend API:
   ```bash
   cd backend
   python -m uvicorn app:app --host 0.0.0.0 --port 8000 --reload
   ```

7. Open the Frontend:
   You can serve the frontend on a local port:
   ```bash
   python -m http.server 3000
   ```
   Navigate to `http://localhost:3000/login.html`

## Demo Flow

1. Register an investigator account on the `login.html` page (or use the canonical `sentinel.test@localhost.dev` account generated via the tests).
2. Sign in to access the Dashboard.
3. Start a new analysis from the dashboard. Upload a synthetic image from `data/sentinel_dataset/documents/`.
4. Review the forensic risk score, interactive heatmap, and evidence log.
5. Click the floating **SENTINEL AI** button in the bottom right to ask context-aware questions about the findings (e.g. "Why was this flagged?").
6. Click **"Save Case"** to store the investigation.
7. Navigate to **Cases** and view the case details.
8. Click **Generate PDF** to download the official forensic report.
9. Toggle between **Clean Light** and **Forensic Dark** themes in the Settings panel and watch it elegantly persist globally.

## Disclaimer
SENTINEL is a forensic screening prototype intended for educational and investigation purposes. It does not authenticate official government IDs.
