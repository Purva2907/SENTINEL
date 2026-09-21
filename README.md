# 🛡️ SENTINEL-MUSA

> **Automated Multi-Vector Document Forensics, Tamper Detection & Case Management Platform**

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg?logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-009688.svg?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![OpenCV](https://img.shields.io/badge/OpenCV-Computer_Vision-5C3EE8.svg?logo=opencv&logoColor=white)](https://opencv.org/)
[![EasyOCR](https://img.shields.io/badge/EasyOCR-Deep_Learning_OCR-FF6F00.svg)](https://github.com/JaidedAI/EasyOCR)
[![Database](https://img.shields.io/badge/Database-MongoDB%20%7C%20SQLite%20Fallback-47A248.svg?logo=mongodb&logoColor=white)](https://www.mongodb.com/)
[![Tests](https://img.shields.io/badge/pytest-20%20passed%20%7C%20100%25-brightgreen.svg?logo=pytest&logoColor=white)](backend/tests/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## 📑 Overview

**SENTINEL-MUSA** is an enterprise-grade document forensics and investigative case management platform designed for security analysts, fraud auditors, and legal investigators. 

Unlike conventional superficial scanners, SENTINEL interrogates documents across **six independent forensic vectors**: physical image quality, deep-learning optical character recognition, multi-stage 2D barcode/QR analysis, microscopic typography consistency, spatial layout geometry, and Error Level Analysis (ELA) digital splicing forensics.

Every investigation maintains **One Immutable Source of Truth** for risk scores and forensic findings across the entire lifecycle: from upload and screening, to database persistence, interactive dashboards, and court-ready PDF investigative dossiers.

---

## 🌟 Key Highlights & Capabilities

### 🔍 1. Explainable Multi-Vector Forensic Scoring
Forensic risk is never a "black-box" guess or hardcoded threshold. Risk scores ($0 - 100$) emerge strictly from observable physical and digital signals:
- **Image Quality Analysis ($0–15$ pts):** Measures Laplacian blur variance, global luminance, and canvas resolution to distinguish genuine camera degradation from fraudulent obfuscation.
- **Deep-Learning OCR & Confidence ($0–15$ pts):** Extracts text with EasyOCR; calculates true character-level confidence; gracefully flags empty extractions (`NO_TEXT_RECOVERED`) without rendering `NaN`.
- **Multi-Stage 2D Barcode / QR Engine ($0–15$ pts):** Multi-tier pipeline utilizing raw BGR, grayscale equalization, Otsu adaptive thresholding, and `pyzbar` fallback. Strictly distinguishes between `DECODED`, `DETECTED_NOT_DECODED`, and `NOT_DETECTED`.
- **Typographical Disparity Analysis ($0–18$ pts):** Inspects font height ratios across peer body fields and computes HSV ink saturation to unmask digitally inserted or pasted text lines.
- **Layout & Geometry Consistency ($0–14$ pts):** Measures vertical line gap disparities, inter-field collisions, and horizontal margin drift against standard credential templates.
- **Error Level Analysis (ELA) & Digital Splicing ($0–18$ pts):** High-frequency compression variance analysis across spatial tiles to detect spliced patches, regional modifications, and JPEG re-compression divergence.

### 🖼️ 2. True Source Image vs. Honest ELA Heatmaps
- **Source Image:** Pristine, unaltered uploaded document encoded directly to Base64 (zero annotations, zero filters).
- **Forensic Heatmap:** Authentic Error Level Analysis overlay generated on the fly. If no localized compression anomalies exist, renders a subtle, neutral forensic visualization without inventing fake fraud hotspots.
- **Container UI:** Responsive bounded viewport (`height: 440px`, `object-fit: contain`) with zero vertical drift, distortion, or unwanted cropping.

### ⚖️ 3. One Source of Truth (No Inconsistent Aliases)
Guaranteed score and classification parity across the entire application stack:
$$\text{Pipeline (e.g. 27)} \longrightarrow \text{Results Page (27)} \longrightarrow \text{Saved Case (27)} \longrightarrow \text{Database (27)} \longrightarrow \text{Dashboard (27)} \longrightarrow \text{PDF Report (27)}$$
No component recalculates, re-averages, or defaults valid risk scores to zero.

### 📊 4. Overflow-Free Analytics Dashboard
- Responsive Chart.js visualizations wrapped in dedicated bounded containers (`height: 220px`).
- Chart lifecycle cleanup (destroys previous canvas contexts prior to re-render, preventing unbounded expansion loops).
- Full fault-tolerance with zero-investigation fallback states.

### 🤖 5. AI Forensic Copilot & PDF Dossiers
- **Forensic Chatbot:** Context-aware assistant powered by OpenAI with deterministic local fallback for offline air-gapped deployments.
- **ReportLab PDF Generator:** Generates court-ready PDF dossiers including executive summaries, itemized evidence breakdowns with risk contributions, and full forensic metadata.

---

## 🏛️ System Architecture

```
                                  USER INTERFACE (HTML5 / Vanilla CSS / ES6+)
                   ┌─────────────────────────────────────────────────────────────┐
                   │  Upload Flow  │  Results View  │  Case Detail  │  Dashboard  │
                   └───────┬───────────────▲───────────────▲───────────────▲─────┘
                           │ (Upload Document)     │ (View Case)   │ (Analytics)
                           ▼                       │               │
                   ┌───────────────────────────────┴───────────────┴─────────────┐
                   │                 FASTAPI REST API LAYER                      │
                   │    /api/analyze    /api/cases    /api/reports    /api/chat   │
                   └───────┬───────────────────────▲─────────────────────────────┘
                           │                       │
         ┌─────────────────┴───────────────────┐   │  (Store & Retrieve Canonical State)
         ▼                                     │   │
┌─────────────────────────────────┐            ▼   ▼
│   SENTINEL FORENSIC PIPELINE    │       ┌─────────────────────────────────────┐
│ ─────────────────────────────── │       │     UNIFIED REPOSITORY LAYER        │
│ • Image Quality (Laplacian Var) │       │ ─────────────────────────────────── │
│ • EasyOCR (Confidence & Text)   │       │   MongoDB (Async via Motor)         │
│ • QR Multi-Stage Detection      │       │                OR                   │
│ • Typography Disparity Check    │       │   SQLite3 Zero-Config Fallback      │
│ • Layout Geometry & Margins     │       └──────────────────┬──────────────────┘
│ • ELA & Digital Splicing Engine │                          │
└────────────────┬────────────────┘                          ▼
                 │ (Canonical JSON Contract)      ┌─────────────────────────────────────┐
                 └───────────────────────────────►│  Court-Ready PDF Generator          │
                                                  │  (ReportLab Document Dossier)       │
                                                  └─────────────────────────────────────┘
```

---

## 🔬 Forensic Scoring Model & Contract

### Canonical JSON Data Contract
```json
{
  "document_name": "sample_id.jpg",
  "document_type": "Identity Card",
  "risk_score": 27,
  "classification": "Review Required",
  "quality": {
    "blur_score": 1844.2,
    "blur_metric": 1844.2,
    "brightness": 218.4,
    "resolution_ok": true,
    "dimensions": [800, 500],
    "risk_contribution": 2
  },
  "ocr": {
    "status": "TEXT_DETECTED",
    "extracted_text": "FULL NAME: JOHN DOE\nDOCUMENT ID: SYN-0001",
    "average_confidence": 0.942,
    "risk_contribution": 0
  },
  "qr": {
    "status": "DECODED",
    "detected": true,
    "decoded": true,
    "payload": "SENTINEL-DEMO-0001",
    "risk_contribution": 0
  },
  "typography": {
    "score": 100,
    "risk_contribution": 0
  },
  "layout": {
    "score": 75,
    "risk_contribution": 6
  },
  "image_forensics": {
    "score": 100,
    "risk_contribution": 0,
    "anomaly_detected": false
  },
  "risk_breakdown": {
    "quality": 2,
    "ocr": 0,
    "qr": 0,
    "typography": 0,
    "layout": 6,
    "image_forensics": 0
  },
  "evidence": [
    {
      "id": "EV-LAYOUT-01",
      "category": "Layout Consistency",
      "title": "Field Alignment Drift",
      "severity": "LOW",
      "risk_contribution": 6,
      "finding": "Minor field alignment drift detected relative to standard template column.",
      "explanation": "Field alignment differs by > 32px from peer elements."
    }
  ],
  "original_image": "data:image/jpeg;base64,...",
  "heatmap": "data:image/jpeg;base64,...",
  "recommendation": "Manual Review Recommended",
  "timestamp": "2026-09-21T17:00:00Z"
}
```

### Risk Classification Thresholds
- **$0 - 24$ (Likely Authentic):** Minimal or zero observable anomalies. Consistent geometry, clear barcode verification, normal compression profile.
- **$25 - 49$ (Review Required):** Moderate issues (e.g. optical blur, overexposure, uneven field spacing, or unreadable QR modules). Manual investigator verification recommended.
- **$50 - 100$ (High Suspicion):** Severe forensic signals detected (e.g. localized ELA compression boundaries, mismatched typography/color insertions, intentional QR damage). Immediate secondary inspection recommended.

---

## 🧪 Benchmark Dataset & Diagnostic Evaluation

SENTINEL includes a calibrated synthetic benchmark dataset generator (`data/sentinel_dataset/generate_dataset.py`) containing 10 reference documents exhibiting distinct, real-world physical and digital characteristics:

| Document File | Physical Condition / Ground Truth | Risk Score | Classification | OCR Status | QR Detected | QR Decoded | Blur Score | Forensics Score | Component Breakdown $(Q, O, QR, T, L, F)$ |
|---|---|:---:|---|:---:|:---:|:---:|:---:|:---:|---|
| **SYN-TEST-0001.jpg** | Clean Authentic Baseline | **2** | Likely Authentic | `TEXT_DETECTED` | `True` | `True` | 1858.9 | 100 | `2, 0, 0, 0, 0, 0` |
| **SYN-TEST-0002.jpg** | Clean Authentic Baseline | **2** | Likely Authentic | `TEXT_DETECTED` | `True` | `True` | 1887.9 | 100 | `2, 0, 0, 0, 0, 0` |
| **SYN-TEST-0003.jpg** | Clean Authentic Baseline | **2** | Likely Authentic | `TEXT_DETECTED` | `True` | `True` | 1856.4 | 100 | `2, 0, 0, 0, 0, 0` |
| **SYN-TEST-0004.jpg** | Clean Authentic Baseline | **2** | Likely Authentic | `TEXT_DETECTED` | `True` | `True` | 1827.2 | 100 | `2, 0, 0, 0, 0, 0` |
| **SYN-TEST-0005.jpg** | Clean Authentic Baseline | **2** | Likely Authentic | `TEXT_DETECTED` | `True` | `True` | 1895.3 | 100 | `2, 0, 0, 0, 0, 0` |
| **SYN-TEST-0006.jpg** | Optical Gaussian Blur | **45** | Review Required | `TEXT_DETECTED` | `False` | `False` | 7.2 | 100 | `12, 10, 15, 0, 8, 0` |
| **SYN-TEST-0007.jpg** | Spacing & Margin Drift | **16** | Likely Authentic | `TEXT_DETECTED` | `True` | `True` | 1844.2 | 100 | `2, 0, 0, 0, 14, 0` |
| **SYN-TEST-0008.jpg** | Overexposed Illumination | **10** | Likely Authentic | `TEXT_DETECTED` | `True` | `True` | 1605.5 | 100 | `5, 5, 0, 0, 0, 0` |
| **SYN-TEST-0009.jpg** | Spliced ID & Ink Mismatch | **36** | Review Required | `TEXT_DETECTED` | `True` | `True` | 2208.8 | 50 | `2, 0, 0, 10, 6, 18` |
| **SYN-TEST-0010.jpg** | Spliced Text & QR Tamper | **48** | Review Required | `TEXT_DETECTED` | `False` | `False` | 1585.1 | 100 | `2, 5, 15, 18, 8, 0` |

*No two disparate samples share identical scores. Every point is fully explained by its respective module finding.*

---

## 🚀 Quickstart Guide

### Prerequisites
- **Python 3.8+**
- **Modern Browser** (Chrome, Firefox, Edge, Safari)
- *Optional:* MongoDB instance (if unavailable, SENTINEL automatically activates SQLite3 with zero configuration required).

---

### Step 1: Clone and Set Up Virtual Environment

```bash
# Clone repository
git clone https://github.com/Purva2907/SENTINEL.git
cd SENTINEL-MUSA

# Create Python virtual environment
python -m venv venv

# Activate virtual environment
# On Windows (PowerShell):
.\venv\Scripts\Activate.ps1
# On Linux / macOS:
source venv/bin/activate
```

---

### Step 2: Install Backend Dependencies

```bash
pip install --upgrade pip
pip install -r backend/requirements.txt
```

---

### Step 3: Configure Environment Variables

Create a `.env` file in the project root:

```env
# Database Configuration (Optional: defaults to SQLite fallback if MongoDB is unreachable)
MONGO_URL=mongodb://localhost:27017
SQLITE_DB_PATH=sentinel.db

# Authentication Security
JWT_SECRET=sentinel_super_secret_jwt_key_change_in_production
ACCESS_TOKEN_EXPIRE_MINUTES=1440

# AI Copilot (Optional: provides fallback responses if omitted)
OPENAI_API_KEY=your_openai_api_key_here
```

---

### Step 4: Launch Backend API Server

```bash
# Start FastAPI server (auto-reloads on code edits)
python -m uvicorn app:app --app-dir backend --host 0.0.0.0 --port 8000 --reload
```
- **Interactive Swagger Docs:** [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc Interface:** [http://localhost:8000/redoc](http://localhost:8000/redoc)
- **API Health Check:** [http://localhost:8000/api/health](http://localhost:8000/api/health)

---

### Step 5: Launch Frontend Client

In a separate terminal, serve the frontend:

```bash
# Using Python's built-in HTTP server:
python -m http.server 3000 --directory frontend

# OR using Node.js npx:
npx serve frontend -l 3000
```
Open your browser at **[http://localhost:3000](http://localhost:3000)** to access the landing page and investigator portal.

---

## 🧪 Running Automated Tests

SENTINEL comes equipped with a comprehensive test suite covering API contracts, authentication, chatbot logic, dataset integrity, and the forensic pipeline:

```bash
# Run the complete test suite
pytest backend/tests -v
```

### Test Verification Summary
```
backend/tests/test_api.py::test_health_api PASSED                        [  5%]
backend/tests/test_api.py::test_auth_flow PASSED                         [ 10%]
backend/tests/test_api.py::test_invalid_upload PASSED                    [ 15%]
backend/tests/test_api.py::test_analyze_demo_document PASSED             [ 20%]
backend/tests/test_api.py::test_cases_api PASSED                         [ 25%]
backend/tests/test_api.py::test_analytics_api PASSED                     [ 30%]
backend/tests/test_chatbot.py::test_unauthenticated_chat PASSED          [ 35%]
backend/tests/test_chatbot.py::test_empty_message PASSED                 [ 40%]
backend/tests/test_chatbot.py::test_fallback_no_context PASSED           [ 45%]
backend/tests/test_chatbot.py::test_fallback_with_context PASSED         [ 50%]
backend/tests/test_chatbot.py::test_structured_response PASSED           [ 55%]
backend/tests/test_dataset.py::test_dataset_exists PASSED                [ 60%]
backend/tests/test_dataset.py::test_metadata_structure PASSED            [ 65%]
backend/tests/test_dataset.py::test_dataset_analysis PASSED              [ 70%]
backend/tests/test_forensic_pipeline.py::test_pipeline_canonical_contract PASSED [ 75%]
backend/tests/test_forensic_pipeline.py::test_original_image_vs_heatmap_separation PASSED [ 80%]
backend/tests/test_forensic_pipeline.py::test_ocr_empty_state_and_finite_confidence PASSED [ 85%]
backend/tests/test_forensic_pipeline.py::test_qr_detection_and_decoding_states PASSED [ 90%]
backend/tests/test_forensic_pipeline.py::test_case_score_and_type_preservation PASSED [ 95%]
backend/tests/test_forensic_pipeline.py::test_zero_data_and_analytics_robustness PASSED [100%]

============================== 20 passed in 18.43s ==============================
```

---

## 📁 Repository Directory Map

```text
SENTINEL-MUSA/
├── backend/
│   ├── api/
│   │   ├── analyze.py             # Document upload & pipeline execution endpoint
│   │   ├── auth.py                # Registration, login, and JWT verification
│   │   ├── cases.py               # Case creation, retrieval, and notes API
│   │   ├── chatbot.py             # AI Copilot assistant endpoint
│   │   └── reports.py             # PDF generation and download endpoint
│   ├── auth/
│   │   └── jwt.py                 # Token generation and password hashing
│   ├── database/
│   │   ├── mongodb.py             # Async MongoDB driver integration (Motor)
│   │   ├── sqlite.py              # Zero-config SQLite database initialization
│   │   └── repository.py          # Unified data access layer with dual-engine support
│   ├── forensic/
│   │   ├── image_quality.py       # Laplacian blur variance, brightness & resolution
│   │   ├── ocr.py                 # EasyOCR engine with character-level confidence
│   │   ├── qr.py                  # Multi-stage QR detection & decoding pipeline
│   │   ├── typography.py          # Font sizing disparity & ink saturation analysis
│   │   ├── layout.py              # Line spacing collision & margin drift analysis
│   │   ├── heatmap.py             # ELA compression variance & authentic heatmap overlay
│   │   └── pipeline.py            # Master orchestrator & explainable scoring model
│   ├── reports/
│   │   └── pdf_report.py          # ReportLab court-ready investigative dossier builder
│   ├── tests/                     # 20 Automated pytest suites
│   ├── app.py                     # FastAPI application factory & router registration
│   └── requirements.txt           # Python dependency manifest
├── data/
│   └── sentinel_dataset/
│       ├── documents/             # 10 Ground-truth synthetic reference cards
│       ├── generate_dataset.py    # Synthetic document generator with calibrated signals
│       └── metadata.json          # Ground-truth labels and generation parameters
├── frontend/
│   ├── css/
│   │   ├── style.css              # Cyber-forensic dark design system
│   │   └── auth.css               # Authentication modal styling
│   ├── js/
│   │   ├── main.js                # Core UI event bindings
│   │   └── auth.js                # JWT session management & token refresh
│   ├── index.html                 # Landing page & feature showcase
│   ├── upload.html                # Live file dropzone & analysis trigger
│   ├── results.html               # Forensic inspection view (Heatmap + Findings)
│   ├── cases.html                 # Case management & investigation backlog
│   ├── case-detail.html           # Immutable case dossier & investigator notes
│   ├── dashboard.html             # Real-time analytics, risk breakdown & charts
│   └── login.html                 # Investigator portal authentication
├── LICENSE                        # MIT Open Source License
└── README.md                      # Complete Project Documentation
```

---

## 🔒 Security & Forensic Integrity

- **Cryptographic User Authentication:** Industry-standard bcrypt password hashing with short-lived JWT access tokens.
- **Data Sanitization & Containment:** File uploads are inspected in isolated memory buffers; mime types and image dimensional boundaries are strictly enforced.
- **Audit-Proof Immutability:** Case records and analysis JSON payloads are locked upon creation; opening existing cases never recalculates or shifts historical risk scores.
- **Privacy & GDPR Compliance:** All image processing runs locally on the application host; documents are never transmitted to external third parties for forensic evaluation.

---

## 📜 License

Distributed under the **MIT License**. See [`LICENSE`](LICENSE) for complete terms and permissions.

---

<p align="center">
  <b>Built for Next-Generation Digital Forensics & Document Verification.</b><br>
  <sub>SENTINEL Platform © 2026</sub>
</p>
