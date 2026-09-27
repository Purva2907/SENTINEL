import os
import zlib
import json
import pytest
import numpy as np
import cv2
import qrcode
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import hashes, serialization
from cryptography import x509
from cryptography.x509.oid import NameOID
import datetime
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from forensic.qr import (
    analyze_qr,
    validate_url,
    mask_aadhaar_number,
    mask_mobile_number,
    mask_email_address,
    parse_aadhaar_payload,
    verify_aadhaar_cryptographic_signature,
    cross_check_qr_with_ocr
)

def create_qr_image_file(tmp_path, payload: str, filename: str = "test_qr.png", box_size: int = 6, border: int = 4) -> str:
    """Helper to generate a real, high-quality decodable QR code image file."""
    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=box_size,
        border=border
    )
    qr.add_data(payload)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white").convert('RGB')
    file_path = str(tmp_path / filename)
    img.save(file_path)
    return file_path

# ==============================================================================
# 1. VALID URL QR & HTTPS URL
# ==============================================================================
def test_valid_https_url_qr(tmp_path):
    """Test 1 & 8: Valid HTTPS URL QR payload is classified as URL, safe_url=True, DECODED_URL."""
    url = "https://sentinel.gov.in/verify?doc_id=DOC-2026-7788"
    file_path = create_qr_image_file(tmp_path, url, "url_qr.png")
    
    res = analyze_qr(file_path)
    assert res["detected"] is True
    assert res["decoded"] is True
    assert res["status"] == "DECODED_URL"
    assert res["payload_type"] == "URL"
    assert res["url"] == url
    assert res["safe_url"] is True
    assert res["is_safe_url"] is True
    assert res["risk_contribution"] == 0
    assert any("Web URL identified" in f for f in res["findings"])

def test_valid_http_url_qr(tmp_path):
    """Test: Valid HTTP URL QR."""
    url = "http://example.com/check/credential"
    file_path = create_qr_image_file(tmp_path, url, "http_qr.png")
    
    res = analyze_qr(file_path)
    assert res["status"] == "DECODED_URL"
    assert res["payload_type"] == "URL"
    assert res["safe_url"] is True
    assert res["url"] == url

# ==============================================================================
# 2. PLAIN-TEXT QR (NEVER FABRICATE A URL)
# ==============================================================================
def test_plain_text_qr_no_url_fabrication(tmp_path):
    """Test 2 & 15: Plain text QR must NOT fabricate a URL, must return TEXT."""
    text_payload = "SENTINEL-SPECIMEN-ID-990022"
    file_path = create_qr_image_file(tmp_path, text_payload, "text_qr.png")
    
    res = analyze_qr(file_path)
    assert res["detected"] is True
    assert res["decoded"] is True
    assert res["status"] == "DECODED_UNVERIFIED"
    assert res["payload_type"] == "TEXT"
    assert res["url"] is None
    assert res["safe_url"] is False
    assert res["payload"] == text_payload
    assert res["risk_contribution"] == 0

# ==============================================================================
# 3. JSON QR
# ==============================================================================
def test_json_qr_payload(tmp_path):
    """Test 3: JSON payload is identified as JSON, status=DECODED_UNVERIFIED."""
    json_data = json.dumps({"specimen_id": "SYN-100", "issuer": "SENTINEL_DEMO", "valid": True})
    file_path = create_qr_image_file(tmp_path, json_data, "json_qr.png")
    
    res = analyze_qr(file_path)
    assert res["detected"] is True
    assert res["decoded"] is True
    assert res["status"] == "DECODED_UNVERIFIED"
    assert res["payload_type"] == "JSON"
    assert res["url"] is None
    assert res["safe_url"] is False

# ==============================================================================
# 4. UNREADABLE QR (BLURRED / NOISY)
# ==============================================================================
def test_unreadable_qr(tmp_path):
    """Test 4: Unreadable heavily degraded QR is caught gracefully without crash."""
    file_path = create_qr_image_file(tmp_path, "TEST-UNREADABLE-DATA", "unreadable_base.png")
    img = cv2.imread(file_path)
    # Apply severe Gaussian blur so bits cannot resolve
    blurred = cv2.GaussianBlur(img, (55, 55), 30)
    blurred_path = str(tmp_path / "blurred_qr.png")
    cv2.imwrite(blurred_path, blurred)
    
    res = analyze_qr(blurred_path)
    assert res["decoded"] is False
    assert res["status"] in ("DETECTED_NOT_DECODED", "NOT_DETECTED")
    assert res["payload"] == ""

# ==============================================================================
# 5. QR-LIKE BLACK PATTERN WITH NO DECODABLE QR
# ==============================================================================
def test_qr_like_black_pattern_detected_not_decoded(tmp_path):
    """Test 5 & 14: Checkered matrix pattern with no QR timing/finders returns DETECTED_NOT_DECODED."""
    canvas = np.ones((400, 400), dtype=np.uint8) * 255
    # Create alternating dense square checkerboard (resembles dense matrix without QR alignment)
    for y in range(80, 280, 5):
        for x in range(80, 280, 5):
            if ((x // 5) + (y // 5)) % 2 == 0:
                canvas[y:y+5, x:x+5] = 0
                
    pattern_path = str(tmp_path / "matrix_pattern.png")
    cv2.imwrite(pattern_path, canvas)
    
    res = analyze_qr(pattern_path)
    assert res["detected"] is True
    assert res["decoded"] is False
    assert res["status"] == "DETECTED_NOT_DECODED"
    assert res["risk_contribution"] <= 5  # Evidence-aware: undecoded pattern does not add arbitrary fraud penalties
    assert res["payload"] == ""

# ==============================================================================
# 6. MULTIPLE QR CODES
# ==============================================================================
def test_multiple_qr_codes_on_canvas(tmp_path):
    """Test 6: Multiple QR codes placed on single canvas are isolated into codes array."""
    # Generate QR 1
    qr1 = qrcode.QRCode(box_size=4, border=2)
    qr1.add_data("https://first.example.com/id1")
    qr1.make(fit=True)
    img1 = np.array(qr1.make_image(fill_color="black", back_color="white").convert('RGB'))
    
    # Generate QR 2
    qr2 = qrcode.QRCode(box_size=4, border=2)
    qr2.add_data("SENTINEL-SECONDARY-QR-PAYLOAD")
    qr2.make(fit=True)
    img2 = np.array(qr2.make_image(fill_color="black", back_color="white").convert('RGB'))
    
    canvas = np.ones((600, 800, 3), dtype=np.uint8) * 255
    h1, w1 = img1.shape[:2]
    h2, w2 = img2.shape[:2]
    canvas[50:50+h1, 50:50+w1] = img1
    canvas[350:350+h2, 450:450+w2] = img2
    
    multi_path = str(tmp_path / "multi_qr.png")
    cv2.imwrite(multi_path, canvas)
    
    res = analyze_qr(multi_path)
    assert res["detected"] is True
    assert res["decoded"] is True
    assert len(res["codes"]) >= 1
    assert "detected_count" in res
    assert res["detected_count"] >= 1

# ==============================================================================
# 7. UNSAFE URL SCHEMES REJECTED
# ==============================================================================
@pytest.mark.parametrize("unsafe_payload", [
    "javascript:alert(document.cookie)",
    "data:text/html,<script>alert(1)</script>",
    "file:///etc/passwd",
    "vbscript:msgbox(1)"
])
def test_unsafe_url_schemes_rejected(tmp_path, unsafe_payload):
    """Test 7: Malicious URL schemes are rejected, safe_url=False, risk penalty applied."""
    file_path = create_qr_image_file(tmp_path, unsafe_payload, "unsafe_qr.png")
    res = analyze_qr(file_path)
    
    assert res["decoded"] is True
    assert res["safe_url"] is False
    assert res["is_safe_url"] is False
    assert res["url"] is None  # Never expose executable schemes as clickable URLs
    assert res["status"] == "DECODED_UNVERIFIED"
    assert res["payload_type"] == "UNSAFE_URL"
    assert res["risk_contribution"] >= 20

# ==============================================================================
# 9 & 10. AADHAAR SYNTHETIC SECURE QR & UNVERIFIED STATE
# ==============================================================================
def create_synthetic_aadhaar_secure_payload():
    """Generates synthetic Aadhaar Secure QR BigInteger string for authorized tests."""
    fields = [
        b'0', # Flag
        b'998820260926', # Reference ID (last 4 digits 9988)
        b'PRIYA SHARMA', # Name
        b'15-08-1992', # DOB
        b'F', # Gender
        b'D/O ANIL SHARMA', # Care of
        b'MUMBAI', # District
        b'NEAR METRO', # Landmark
        b'402', # House
        b'ANDHERI WEST', # Location
        b'400053', # Pincode
        b'ANDHERI', # Post Office
        b'MAHARASHTRA', # State
        b'LINK ROAD', # Street
        b'MUMBAI SUBURBAN', # Sub-district
        b'MUMBAI' # VTC
    ]
    delimited = b'\xff'.join(fields)
    synthetic_sig = b'\xaa' * 256
    full_bytes = delimited + b'\xff' + synthetic_sig
    compressed = zlib.compress(full_bytes)
    big_int = int.from_bytes(compressed, 'big')
    return str(big_int)

def test_aadhaar_secure_qr_decoding_and_unverified_state(tmp_path):
    """Test 9 & 10: Synthetic Aadhaar Secure QR decoded, demographics extracted, returns DECODED_UNVERIFIED."""
    payload_str = create_synthetic_aadhaar_secure_payload()
    file_path = create_qr_image_file(tmp_path, payload_str, "aadhaar_qr.png", box_size=5, border=4)
    
    res = analyze_qr(file_path)
    assert res["detected"] is True
    assert res["decoded"] is True
    assert res["status"] == "DECODED_UNVERIFIED"
    assert res["payload_type"] == "AADHAAR_SECURE_QR"
    assert res["verification"]["performed"] is False
    assert res["verification"]["status"] == "NOT_PERFORMED"
    
    # Demographics check
    demo = res["demographics"]
    assert demo["name"] == "PRIYA SHARMA"
    assert demo["dob"] == "15-08-1992"
    assert demo["gender"] == "F"
    assert "XXXX" in demo["masked_aadhaar"]
    
    # Findings must clearly disclose unverified cryptographic state
    assert any("Cryptographic UIDAI signature verification was not performed" in f for f in res["findings"])

# ==============================================================================
# 11 & 12. QR ↔ OCR CROSS-CHECK (CONSISTENT vs INCONSISTENT)
# ==============================================================================
def test_qr_ocr_cross_check_consistent(tmp_path):
    """Test 11: Decoded demographic fields match OCR extracted text -> CONSISTENT."""
    payload_str = create_synthetic_aadhaar_secure_payload()
    file_path = create_qr_image_file(tmp_path, payload_str, "aadhaar_match.png")
    
    ocr_data = {
        "extracted_text": "GOVERNMENT OF INDIA PRIYA SHARMA DOB: 15/08/1992 FEMALE MAHARASHTRA",
        "detections": ["PRIYA SHARMA", "15/08/1992", "FEMALE"]
    }
    
    res = analyze_qr(file_path, ocr_data=ocr_data)
    assert res["ocr_cross_check"]["status"] == "CONSISTENT"
    assert any("QR/OCR fields consistent" in f for f in res["findings"])
    assert res["risk_contribution"] == 0

def test_qr_ocr_cross_check_inconsistent_tamper(tmp_path):
    """Test 12: Decoded QR name differs from OCR extracted name -> INCONSISTENT, high risk."""
    payload_str = create_synthetic_aadhaar_secure_payload() # Name is PRIYA SHARMA
    file_path = create_qr_image_file(tmp_path, payload_str, "aadhaar_mismatch.png")
    
    # OCR shows completely different name (e.g. forged front text)
    ocr_data = {
        "extracted_text": "GOVERNMENT OF INDIA VIKRAM VERMA DOB: 01/01/1980 MALE DELHI",
        "detections": ["VIKRAM VERMA", "01/01/1980", "MALE"]
    }
    
    res = analyze_qr(file_path, ocr_data=ocr_data)
    assert res["ocr_cross_check"]["status"] == "INCONSISTENT"
    assert any("inconsistent" in f.lower() for f in res["findings"])
    assert res["risk_contribution"] >= 25

# ==============================================================================
# 13. NOT_DETECTED STATE
# ==============================================================================
def test_not_detected_state(tmp_path):
    """Test 13: Canvas without QR code returns NOT_DETECTED."""
    blank = np.ones((400, 500, 3), dtype=np.uint8) * 255
    blank_path = str(tmp_path / "blank.png")
    cv2.imwrite(blank_path, blank)
    
    res = analyze_qr(blank_path, expected_qr=True)
    assert res["detected"] is False
    assert res["decoded"] is False
    assert res["status"] == "NOT_DETECTED"
    assert res["payload"] == ""
    assert res["risk_contribution"] == 15

# ==============================================================================
# 16 & 17. GENUINE CRYPTOGRAPHIC VERIFICATION (SIGNATURE_VERIFIED vs INVALID)
# ==============================================================================
def test_genuine_cryptographic_signature_verified_and_invalid(tmp_path):
    """
    Test 16 & 17:
    Generate real RSA-2048 keypair and test X.509 certificate.
    16. Valid signature over payload -> SIGNATURE_VERIFIED, authority=UIDAI.
    17. Tampered payload -> SIGNATURE_INVALID, risk penalty applied.
    """
    # 1. Generate RSA Keypair & Self-Signed Test Certificate
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    subject = issuer = x509.Name([
        x509.NameAttribute(NameOID.COUNTRY_NAME, "IN"),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Unique Identification Authority of India"),
        x509.NameAttribute(NameOID.COMMON_NAME, "UIDAI Test Signer Authority")
    ])
    cert = x509.CertificateBuilder().subject_name(
        subject
    ).issuer_name(
        issuer
    ).public_key(
        private_key.public_key()
    ).serial_number(
        x509.random_serial_number()
    ).not_valid_before(
        datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=1)
    ).not_valid_after(
        datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=365)
    ).sign(private_key, hashes.SHA256())
    
    cert_path = str(tmp_path / "test_uidai_cert.pem")
    with open(cert_path, "wb") as f:
        f.write(cert.public_bytes(serialization.Encoding.PEM))

    # 2. Build signed Aadhaar payload
    fields = [
        b'0', b'776620260926', b'AMIT PATEL', b'10-10-1990', b'M',
        b'S/O KANUBHAI', b'AHMEDABAD', b'NEAR BRIDGE', b'101', b'VASTRAPUR',
        b'380015', b'VASTRAPUR', b'GUJARAT', b'DRIVE IN RD', b'AHMEDABAD', b'AHMEDABAD'
    ]
    delimited = b'\xff'.join(fields)
    
    # Real signature generated using private key
    genuine_signature = private_key.sign(delimited, padding.PKCS1v15(), hashes.SHA256())
    assert len(genuine_signature) == 256
    
    # Test 16: Genuine Verification
    verif_res = verify_aadhaar_cryptographic_signature(
        delimited, genuine_signature, cert_path=cert_path
    )
    assert verif_res["performed"] is True
    assert verif_res["status"] == "SIGNATURE_VERIFIED"
    assert verif_res["authority"] == "UIDAI"

    # Test 17: Tampered signed data with genuine signature
    tampered_data = delimited.replace(b'AMIT PATEL', b'SNEHA DESAI')
    invalid_res = verify_aadhaar_cryptographic_signature(
        tampered_data, genuine_signature, cert_path=cert_path
    )
    assert invalid_res["performed"] is True
    assert invalid_res["status"] == "SIGNATURE_INVALID"
    assert "compromise suspected" in invalid_res["reason"].lower()

# ==============================================================================
# PRIVACY & SENSITIVE DATA MASKING
# ==============================================================================
def test_sensitive_aadhaar_number_and_pii_masking():
    """Verify Aadhaar numbers, mobile numbers, and emails are never exposed raw."""
    assert mask_aadhaar_number("123456789012") == "XXXX XXXX 9012"
    assert mask_aadhaar_number("1234 5678 9012") == "XXXX XXXX 9012"
    assert mask_mobile_number("9876543210") == "XXXXXX3210"
    assert mask_email_address("john.doe@example.com") == "j***e@example.com"
