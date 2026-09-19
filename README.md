# SENTINEL - AI-Powered Document Forensics

**Tagline:** Trust the Evidence.
**Hackathon:** MUSA CodeX 2026
**Problem Statement:** CX0203 — The Aadhaar Look-Alike: AI-Powered Document Forensics for Synthetic Aadhaar & PAN Detection.

## Project Overview

SENTINEL is a robust forensic screening prototype designed to identify synthetic or manipulated Aadhaar and PAN documents. It leverages an advanced pipeline of Computer Vision, OCR, and QR analysis to provide a deterministic risk score without claiming to be an official government authentication service.

## Features (P0 & P1 Implementation)

1. **Forensic Analysis Pipeline (P0)**
   - Document Classification & Identification
   - Visual/Image Quality Analysis (Blur, Lighting, Tampering markers)
   - OCR Extraction via EasyOCR
   - QR Code Consistency Checking
   - Risk Scoring Engine (0-100 deterministic risk assessment)
   - Forensic Heatmap Generation

2. **Investigation Platform (P1)**
   - **Persistent Storage:** MongoDB primary with SQLite fallback.
   - **User Authentication:** JWT-based secure login and registration.
   - **Case Management:** Save analysis results as persistent investigation cases.
   - **Dashboards:** Full metrics and analytics visualization using Chart.js.
   - **PDF Reporting:** Automatic forensic evidence PDF report generation via ReportLab.
   - **AI Assistant:** Context-aware local chatbot integrated directly into the case detail view.

## Tech Stack

- **Backend:** Python, FastAPI, Motor (MongoDB), SQLite3, ReportLab, Passlib/Jose
- **Frontend:** HTML5, CSS3, Vanilla JavaScript, Chart.js
- **Machine Learning/CV:** OpenCV, EasyOCR, Pillow, PyZBar

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

3. Ensure MongoDB is running (default `mongodb://localhost:27017`). If unavailable, it will fallback to SQLite automatically.

4. Start the backend API:
   ```bash
   cd backend
   python -m uvicorn app:app --host 0.0.0.0 --port 8000 --reload
   ```

5. Open the Frontend:
   Open `frontend/login.html` directly in your web browser. Or serve the frontend directory using Live Server.

## Demo Flow

1. Register an investigator account on the `register.html` page.
2. Sign in to access the `dashboard.html`.
3. Start a new analysis from the dashboard. Upload an image (e.g. from `samples/`).
4. Review the analysis results and interact with the AI assistant.
5. Click **"Save as Case"** to store the investigation.
6. Navigate to **Cases** and view the case details.
7. Click **Generate PDF** to download the official forensic report.

## Disclaimer
SENTINEL is a forensic screening prototype intended for educational and investigation purposes. It does not authenticate official government IDs.
