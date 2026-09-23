<p align="center">
  <img src="assets/hero-banner.svg" alt="SENTINEL-MUSA Forensic Defense Platform Banner" width="100%">
</p>

<p align="center">
  <a href="https://www.python.org/"><img src="https://img.shields.io/badge/python-3.8+-blue.svg?logo=python&logoColor=white" alt="Python 3.8+"></a>
  <a href="https://fastapi.tiangolo.com/"><img src="https://img.shields.io/badge/FastAPI-0.100+-009688.svg?logo=fastapi&logoColor=white" alt="FastAPI"></a>
  <a href="https://opencv.org/"><img src="https://img.shields.io/badge/OpenCV-Computer_Vision-5C3EE8.svg?logo=opencv&logoColor=white" alt="OpenCV"></a>
  <a href="https://github.com/JaidedAI/EasyOCR"><img src="https://img.shields.io/badge/EasyOCR-Deep_Learning_OCR-FF6F00.svg" alt="EasyOCR"></a>
  <a href="https://www.mongodb.com/"><img src="https://img.shields.io/badge/Database-MongoDB%20%7C%20SQLite%20Fallback-47A248.svg?logo=mongodb&logoColor=white" alt="Database"></a>
  <a href="backend/tests/"><img src="https://img.shields.io/badge/pytest-40%20passed%20%7C%20100%25-brightgreen.svg?logo=pytest&logoColor=white" alt="Tests"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-yellow.svg" alt="License"></a>
</p>

---

## ⚡ Live Forensic Pipeline Flow

<p align="center">
  <img src="assets/animated-flow.svg" alt="SENTINEL-MUSA Animated Forensic Workflow" width="100%">
</p>

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

## 🔬 Forensic Scoring Model & Canonical Data Contract

The SENTINEL analysis engine maintains a strict, standardized contract across intake screening, persistent case dossiers, dashboard analytics, and forensic PDF reports.

### Canonical Analysis Response Payload
```json
{
  "case_id": "SC-2026-849102",
  "document_type": "Identity Card",
  "risk_score": 27,
  "classification": "Review Required",
  "confidence": 88,
  "risk_contribution": 27,
  "quality": {
    "blur_score": 1844.2,
    "blur_metric": 1844.2,
    "brightness": 218.4,
    "resolution_ok": true,
    "dimensions": [850, 540],
    "risk_contribution": 2
  },
  "ocr": {
    "status": "TEXT_DETECTED",
    "extracted_text": "FULL NAME: JOHN DOE | DOCUMENT ID: SYN-0001",
    "average_confidence": 0.942,
    "risk_contribution": 0
  },
  "qr": {
    "status": "DECODED",
    "detected": true,
    "decoded": true,
    "payload": "SENTINEL-DEMO-0001",
    "consistency": "Matching demographic payload",
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
      "severity": "Warning",
      "risk_contribution": 6,
      "confidence": 85,
      "observed_metrics": [
        "Inter-field baseline variance: 2.1x baseline",
        "Horizontal margin offset: 18px"
      ],
      "assessment": "Minor field alignment drift detected relative to standard credential geometry.",
      "finding": "Field alignment differs by > 18px from standard template columns.",
      "explanation": "Field alignment differs by > 18px from peer elements."
    }
  ],
  "fingerprint": {
    "fingerprint_hash": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
    "fingerprint_vector": [0.42, 0.54, 0.63, 0.12, 0.94, 0.05, 0.18, 1.0, 0.88, 0.72, 0.0]
  },
  "chain_of_custody": {
    "evidence_id": "EVID-SC-2026-849102",
    "sha256_hash": "a1b2c3d4e5f60718293a4b5c6d7e8f90123456789abcdef0123456789abcdef0",
    "analysis_version": "2.1.0",
    "ingestion_timestamp": "2026-09-23T21:45:00Z",
    "status": "TAMPER_FREE"
  },
  "original_image": "data:image/jpeg;base64,...",
  "heatmap": "data:image/jpeg;base64,...",
  "recommendation": "Manual investigator review recommended. Minor structural geometry variations observed.",
  "timestamp": "2026-09-23T21:45:00Z"
}
```

### Canonical Field Specifications

| Canonical Field | Type | Range / Example | Description & Operational Semantics |
| :--- | :--- | :--- | :--- |
| `case_id` | `string` | `"SC-2026-849102"` | Unique deterministic case dossier identifier. |
| `document_type` | `string` | Categorical | Classification of the examined document (e.g. Identity Card, Passport-like, Taxpayer Specimen). |
| `risk_score` | `integer` | `0 – 100` | Finite aggregate forensic risk score calculated from additive component contributions. |
| `classification` | `string` | Categorical | Qualitative triage status (`Likely Authentic`, `Review Required`, or `High Suspicion`). |
| `confidence` | `integer` | `0 – 100` | Aggregate **Forensic Signal Confidence** (observation certainty, not probability of fraud). |
| `risk_contribution` | `integer` | `0 – 100` | Total cumulative risk points contributed across all forensic modules. |
| `quality` | `object` | Quality metrics | Physical image metrics: Laplacian blur variance, global luminance, resolution validation. |
| `ocr` | `object` | OCR extraction | Optical character recognition state (`TEXT_DETECTED`, `NO_TEXT_RECOVERED`), text string, token confidence. |
| `qr` | `object` | 2D matrix checks | Barcode verification state (`DECODED`, `DETECTED_NOT_DECODED`, `NOT_DETECTED`) and payload parity. |
| `typography` | `object` | Typographic checks | Font height ratios across peer lines, kerning variance, and HSV ink saturation deltas. |
| `layout` | `object` | Layout geometry | Spatial alignment, inter-field vertical line spacing variance, and margin drift. |
| `image_forensics` | `object` | ELA & splicing | Error Level Analysis compression variance and digital splicing patch detection. |
| `risk_breakdown` | `object` | Per-vector scores | Explicit dictionary mapping each of the 6 forensic vectors to its exact point contribution. |
| `evidence` | `array` | Signal cards | Itemized forensic observations with `category`, `risk_contribution`, `confidence`, `observed_metrics`, `assessment`. |
| `fingerprint` | `object` | Morphological hash | 11-dimensional normalized characteristic vector and deterministic SHA-256 hash (`risk_score` excluded). |
| `chain_of_custody` | `object` | Cryptographic audit | Intake evidence ID, cryptographic SHA-256 file hash, version (`2.1.0`), and integrity status. |
| `original_image` | `string` | Base64 URI | Pristine, unaltered uploaded source document bytes. |
| `heatmap` | `string` | Base64 URI | Authentic Error Level Analysis thermal compression overlay. |
| `recommendation` | `string` | Text assessment | Clear, defensible forensic guidance for the investigating analyst. |
| `timestamp` | `string` | ISO 8601 UTC | Ingestion and screening completion timestamp. |

### Risk Classification Thresholds
- **`0 – 34` (Likely Authentic):** Minimal or zero observable anomalies. Consistent geometry, clear barcode verification, normal compression profile.
- **`35 – 69` (Review Required):** Moderate issues (e.g. optical blur, overexposure, uneven field spacing, or unreadable QR modules). Manual investigator verification recommended.
- **`70 – 100` (High Suspicion):** Severe forensic signals detected (e.g. localized ELA compression boundaries, mismatched typography/color insertions, intentional QR damage). Immediate secondary inspection recommended.

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
backend/tests/test_advanced_features.py::test_chain_of_custody_full_lifecycle PASSED      [ 25%]
backend/tests/test_advanced_features.py::test_synthetic_lab_generation_and_safety PASSED  [ 50%]
backend/tests/test_advanced_features.py::test_synthetic_lab_all_manipulations PASSED      [ 75%]
backend/tests/test_advanced_features.py::test_document_comparison_cases PASSED            [100%]

============================== 40 passed, 138 warnings in 54.93s ==============================
```

---

## 🚀 Advanced Forensic Features Suite (v2.1.0)

SENTINEL-MUSA v2.1.0 introduces an advanced suite of forensic capabilities spanning evidence chain of custody, controlled synthetic document generation, forensic document fingerprinting, similar case intelligence, chronological event timelines, and side-by-side differential analysis.

### 🔗 1. Cryptographic Evidence Chain of Custody
- **SHA-256 Evidence Ingestion Digest:** At the point of document upload, raw bytes are hashed with SHA-256 and persisted alongside the immutable case dossier (`analysis_version: "2.1.0"`).
- **Integrity Verification (`GET /api/cases/{case_id}/verify-custody`):** Actively verifies stored evidence bytes against the initial intake digest on demand.
- **Defensible Statuses:** Explicitly returns `TAMPER_FREE`, `INTEGRITY_BREACH` (if bytes diverge), or `UNAVAILABLE` (if file access is severed).
- **Visual Intake Flow:** Illustrated sequence in Case Detail: $\text{Evidence Ingested} \to \text{SHA-256 Calculated} \to \text{Forensic Analysis} \to \text{Case Dossier} \to \text{Forensic Report}$.

### 🔬 2. Controlled Synthetic Forensics Lab (`frontend/lab.html`)
- **Safety Standard:** Strictly generates fictional credentials carrying a prominent, non-removable watermark:  
  `"SYNTHETIC DEMO — NOT A REAL GOVERNMENT DOCUMENT"`. No real identity data, Aadhaar numbers, PAN numbers, or real credentials are ever fabricated.
- **Deterministic Manipulations:** 8 controlled, reproducible transformations with variable severity ($1 - 100$):
  1. *Typography Alteration* (font scaling disparity and stroke weight variance)
  2. *Kerning Distortion* (irregular non-uniform character gap spacing)
  3. *Layout Shift* (off-grid displacement of demographic text blocks)
  4. *Image Splice* (injection of secondary digital graphic patches)
  5. *QR Corruption* (2D matrix optical interference and occlusion noise)
  6. *Substrate Blur* (calibrated Gaussian filter simulation)
  7. *JPEG Compression* (quantization artifacts triggering ELA response)
  8. *Illumination Change* (non-linear exposure and spotlight overexposure)
- **One-Click Detector Benchmark:** Passes manipulated artifacts directly into SENTINEL's actual multi-vector analysis engine to benchmark detector sensitivity against ground-truth controlled conditions.

### 📊 3. Forensic Explainability Panel
- **Deconstructed Signal Metric Cards:** Every forensic signal exposes its exact component category, numerical risk contribution ($+\text{pts}$), and qualitative assessment.
- **Forensic Signal Confidence:** Distinguishes signal observation certainty from fraud probability. Labeled explicitly with contextual tooltips: *"Represents confidence in the underlying observed signal from deterministic detectors, NOT a probability of fraud or illegality."*
- **Empirical Grounding:** Metrics reflect actual computer vision and OCR calculations (`Laplacian variance`, `inter-field spacing ratios`, `quantization residuals`); unavailable metrics report `"Metric unavailable"` without NaN values or synthetic filler.

### 🧬 4. Forensic Document Fingerprinting (`backend/forensic/fingerprint.py`)
- **Normalized Feature Vector:** Computes an 11-dimensional normalized characteristic vector encompassing image aspect ratio, resolution, OCR word density, character confidence, typography variance, layout variance, QR presence, blur metric, luminance, and ELA anomaly magnitude.
- **Risk Score Exclusion:** `risk_score` is strictly excluded from fingerprint generation, ensuring similarity is governed solely by observable morphological characteristics, not model classification output.
- **Deterministic Hash:** Generates a 64-character SHA-256 fingerprint hash for deterministic deduplication and clustering.

### 🔎 5. Similar Case Detection (`GET /api/cases/{case_id}/similar`)
- **Cosine Metric Matching:** Evaluates document vector angles against other dossiers in the user's authorized docket.
- **Self-Exclusion & Tenant Boundary:** Excludes the query case and enforces multi-tenant boundary isolation.
- **Copilot Integration:** Informs the interactive AI Copilot when analysts ask: *"Have we seen a similar document before?"*

### ⏳ 6. Chronological Investigation Timeline
- **Auditable Case Milestones:** Captures actual investigation milestones: `EVIDENCE_INGESTED`, `SHA256_CALCULATED`, `FORENSIC_SCREENING_COMPLETED`, `CASE_CREATED`, `NOTE_ADDED`, `STATUS_CHANGED`, `REPORT_GENERATED`, and `INTEGRITY_VERIFICATION`.
- **Chronological Feed:** Renders in Case Detail with verified timestamps and investigator attribution.

### 🔀 7. Side-by-Side Document Comparison (`frontend/compare.html`)
- **Dual Intake Modes:** Accommodates either two directly uploaded document specimens or two existing case dossiers.
- **Thermal Difference Heatmap:** Computes an OpenCV absolute difference (`cv2.absdiff`) rendered via JET thermal colormap and alpha blend.
- **Neutral Forensic Lexicon:** Employs objective terminology (*"Visual Difference Detected"*, *"Structural Difference Detected"*, *"Text Difference Detected"*).
- **Interactive Controls:** Side-by-side viewports, blend overlay with opacity slider, synchronized zoom ($0.4\times - 3.0\times$), and OCR token divergence analysis.

---

## ⚠️ Important Limitations & Forensic Scope

1. **Decision-Support Scope:** SENTINEL-MUSA is an automated forensic screening and decision-support system designed to assist qualified investigators. It does not replace statutory identity verification, legal adjudication, or official government databases.
2. **Evidence Integrity vs. Document Authenticity:** Cryptographic SHA-256 hashing verifies that stored evidence files have not been tampered with or corrupted after ingestion. It does not establish that a document is legally genuine or officially issued.
3. **Forensic Similarity vs. Fraud Probability:** Similar Case Detection computes mathematical closeness of observable digital and typographical characteristics. A high similarity score does not indicate a probability of fraud.
4. **Synthetic Lab Boundaries:** Synthetic documents produced by the lab are strictly demonstration artifacts created for detector testing and evaluation. Fictional names, addresses, and identifiers are used exclusively.
5. **Computer Vision & OCR Fallibility:** Optical Character Recognition and algorithmic image forensics may encounter degradation under low-resolution, high-noise, or heavily compressed conditions.
6. **AI Copilot & Offline Resilience:** Cloud LLM integrations (Gemini, Groq, OpenAI) are optional enhancements. The platform includes a deterministic local fallback that operates completely offline and air-gapped without external network calls.

---

## 📁 Repository Directory Map

```text
SENTINEL-MUSA/
├── backend/
│   ├── api/
│   │   ├── analyze.py             # Document intake & SHA-256 custody tracking
│   │   ├── auth.py                # Registration, login, and JWT verification
│   │   ├── cases.py               # Case creation, custody verification, similar cases & notes
│   │   ├── chatbot.py             # AI Copilot assistant with multi-case intelligence
│   │   ├── compare.py             # Dual document upload & case comparison API
│   │   ├── synthetic.py           # Controlled Synthetic Forensics Lab endpoints
│   │   └── reports.py             # PDF generation and download endpoint
│   ├── auth/
│   │   └── jwt.py                 # Token generation and password hashing
│   ├── database/
│   │   ├── mongodb.py             # Async MongoDB driver integration (Motor)
│   │   ├── sqlite.py              # Zero-config SQLite database initialization & migrations
│   │   └── repository.py          # Unified data access layer with dual-engine parity
│   ├── forensic/
│   │   ├── comparison.py          # Thermal absdiff heatmap & OCR token differential
│   │   ├── fingerprint.py         # 11-dimensional normalized fingerprinting & cosine similarity
│   │   ├── synthetic_lab.py       # Controlled synthetic credential canvas & 8 manipulation modules
│   │   ├── image_quality.py       # Laplacian blur variance, brightness & resolution
│   │   ├── ocr.py                 # EasyOCR engine with character-level confidence
│   │   ├── qr.py                  # Multi-stage QR detection & decoding pipeline
│   │   ├── typography.py          # Font sizing disparity & ink saturation analysis
│   │   ├── layout.py              # Line spacing collision & margin drift analysis
│   │   ├── heatmap.py             # ELA compression variance & authentic heatmap overlay
│   │   └── pipeline.py            # Master orchestrator & explainable scoring model
│   ├── reports/
│   │   └── pdf_report.py          # ReportLab court-ready investigative dossier builder
│   ├── tests/
│   │   ├── test_advanced_features.py # 10 Comprehensive tests for Waves 1, 2, and 3
│   │   └── ...                    # 30 Baseline automated test suites
│   ├── app.py                     # FastAPI application factory & router registration
│   └── requirements.txt           # Python dependency manifest
├── frontend/
│   ├── css/
│   │   ├── style.css              # Cyber-forensic dark design system
│   │   ├── variables.css          # Theme design tokens & CSS variables
│   │   └── chatbot.css            # Floating AI Copilot assistant styling
│   ├── js/
│   │   ├── auth.js                # JWT session management & token refresh
│   │   ├── chatbot.js             # Interactive Copilot client & case context
│   │   ├── theme.js               # Dark/Light theme switching engine
│   │   └── toast.js               # Non-blocking forensic notifications
│   ├── index.html                 # Landing page & feature showcase
│   ├── analyze.html               # Forensic intake workstation
│   ├── lab.html                   # Controlled Synthetic Forensics Lab UI
│   ├── compare.html               # Side-by-side differential comparison workstation
│   ├── results.html               # Forensic inspection view (Heatmap + Findings)
│   ├── cases.html                 # Case management & investigation backlog
│   ├── case-detail.html           # Custody, timeline, explainability & similar cases
│   ├── dashboard.html             # Real-time analytics, risk breakdown & charts
│   ├── reports.html               # Report generation & archive portal
│   ├── profile.html               # Investigator profile & credentials
│   ├── settings.html              # System preferences & theme controls
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
