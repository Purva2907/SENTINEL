# SENTINEL-MUSA

SENTINEL-MUSA is a comprehensive forensic analysis, evidence management, and reporting system. It is designed to assist investigators in managing cases, analyzing digital and physical evidence (such as images, barcodes, and text via OCR), and generating automated forensic reports.

## Features

- **Case Management:** Create, track, and manage investigative cases.
- **Forensic Analysis:**
  - Optical Character Recognition (OCR) using `easyocr`.
  - Barcode and QR code scanning using `pyzbar`.
  - Image processing and analysis via OpenCV.
- **Automated Reporting:** Generate comprehensive PDF reports for case files using `reportlab`.
- **AI Chatbot Assistant:** Integrated chatbot for assisting with investigations or system navigation, powered by OpenAI.
- **Analytics Dashboard:** Visual insights and statistics on cases and analyses.
- **Secure Authentication:** User authentication and authorization (JWT, bcrypt).

## Project Structure

The project is split into a separated frontend and backend architecture:

- **`backend/`**: Python/FastAPI backend containing business logic, database models, AI integration, and forensic analysis modules.
- **`frontend/`**: Vanilla HTML, CSS, and JavaScript frontend for a responsive and lightweight user experience.
- **`data/`**: Directory for storing data or sample files.

### Backend Tech Stack

- **Framework:** FastAPI
- **Database:** MongoDB (Async via `motor`)
- **Computer Vision & OCR:** OpenCV, Pillow, EasyOCR, PyZbar
- **Reporting:** ReportLab
- **AI/ML:** OpenAI API
- **Auth:** Passlib, bcrypt, python-jose

### Frontend Tech Stack

- HTML5, CSS3 (Vanilla), JavaScript

## Getting Started

### Prerequisites

- Python 3.8+
- Node.js (Optional, if you plan to serve the frontend via a local dev server)
- MongoDB running locally or a MongoDB Atlas connection string.
- OpenAI API Key (for chatbot features)

### Backend Setup

1. Navigate to the backend directory:
   ```bash
   cd backend
   ```

2. Create a virtual environment and activate it:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Set up environment variables:
   Copy `.env.example` (if present) to `.env` and fill in your details:
   ```
   MONGODB_URL=your_mongodb_connection_string
   OPENAI_API_KEY=your_openai_api_key
   SECRET_KEY=your_jwt_secret_key
   ```

5. Run the FastAPI development server:
   ```bash
   uvicorn app:app --reload
   ```
   The backend will be available at `http://localhost:8000`. You can view the API documentation at `http://localhost:8000/docs`.

### Frontend Setup

Since the frontend is built with vanilla web technologies, you can serve it using any simple HTTP server.

1. Navigate to the frontend directory:
   ```bash
   cd frontend
   ```

2. Serve the files locally:
   Using Python:
   ```bash
   python -m http.server 3000
   ```
   Or using Node.js (e.g., `serve`):
   ```bash
   npx serve -l 3000
   ```

3. Open your browser and navigate to `http://localhost:3000/index.html`.

## License

This project is licensed under the MIT License.
