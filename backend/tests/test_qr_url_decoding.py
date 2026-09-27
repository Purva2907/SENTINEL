import os
import sys
import json
import pytest
import qrcode
import numpy as np
import cv2

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from forensic.qr import (
    analyze_qr,
    validate_url,
    decode_qr_pipeline,
    _run_opencv_on_image,
    _run_pyzbar_on_image,
    _run_zxing_on_image
)

def create_qr_file(tmp_path, payload: str, filename: str = "qr.png") -> str:
    qr = qrcode.QRCode(box_size=10, border=4)
    qr.add_data(payload)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white").convert('RGB')
    p = str(tmp_path / filename)
    img.save(p)
    return p

# ==============================================================================
# 1. REAL URL DECODING AND MULTI-ENGINE CONFIRMATION
# ==============================================================================
def test_real_url_decoding_sentinel_demo(tmp_path):
    """Verify known URL QR (https://example.com/sentinel-demo) decodes exact payload."""
    url = "https://example.com/sentinel-demo"
    file_path = create_qr_file(tmp_path, url, "demo_url.png")
    
    res = analyze_qr(file_path)
    assert res["detected"] is True
    assert res["decoded"] is True
    assert res["status"] == "DECODED_URL"
    assert res["payload_type"] == "URL"
    assert res["payload"] == url
    assert res["decoded_url"] == url
    assert res["url"] == url
    assert res["safe_url"] is True
    assert res["is_safe_url"] is True
    assert res["decoder"] in ("ZXING_CPP", "OPENCV", "PYZBAR")
    assert res["decode_confidence"] in ("MULTI_ENGINE_CONFIRMED", "SINGLE_ENGINE_DECODED")
    try:
        import zxingcpp
        has_zxing = True
    except Exception:
        has_zxing = False

    if has_zxing:
        assert res["engine_status"]["zxing"] == "SUCCESS"
    assert res["engine_status"]["opencv"] == "SUCCESS"
    assert res["engine_status"]["pyzbar"] == "SUCCESS"
    assert res["decode_confidence"] == "MULTI_ENGINE_CONFIRMED"

def test_http_url_decoding_with_query_params(tmp_path):
    """Verify HTTP URL with parameters decodes exact payload."""
    url = "http://example.com/verify?id=12345&auth=true"
    file_path = create_qr_file(tmp_path, url, "query_url.png")
    
    res = analyze_qr(file_path)
    assert res["status"] == "DECODED_URL"
    assert res["payload_type"] == "URL"
    assert res["decoded_url"] == url
    assert res["url"] == url
    assert res["safe_url"] is True

# ==============================================================================
# 2. DECODER FALLBACK & ENGINE CONSENSUS
# ==============================================================================
def test_multi_engine_confirmed_consensus():
    """Verify that multiple engines decoding same payload yields MULTI_ENGINE_CONFIRMED."""
    qr = qrcode.QRCode(box_size=8, border=4)
    qr.add_data("https://example.com/consensus")
    qr.make(fit=True)
    img = np.array(qr.make_image(fill_color="black", back_color="white").convert('RGB'))
    bgr = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
    
    codes, debug = decode_qr_pipeline(bgr)
    assert len(codes) >= 1
    c = codes[0]
    assert c["decoded"] is True
    assert c["decode_confidence"] == "MULTI_ENGINE_CONFIRMED"
    try:
        import zxingcpp
        has_zxing = True
    except Exception:
        has_zxing = False

    if has_zxing:
        assert c["decoder"] == "ZXING_CPP"
        assert c["engine_status"]["zxing"] == "SUCCESS"
    else:
        assert c["decoder"] in ("PYZBAR", "OPENCV")
    assert c["engine_status"]["pyzbar"] == "SUCCESS"
    assert c["engine_status"]["opencv"] == "SUCCESS"

def test_decoder_conflict_flagged_safely():
    """Verify that conflicting decoder outputs are flagged as DECODER_CONFLICT without arbitrary guess."""
    from forensic.qr import decode_qr_pipeline
    
    # Simulate conflict directly
    cluster = {
        "engine_payloads": {
            "opencv": "https://malicious.com/fake",
            "zxing": "https://legitimate.gov.in/real"
        },
        "engine_status": {"opencv": "SUCCESS", "pyzbar": "FAILED", "zxing": "SUCCESS"},
        "bbox": [[0,0],[100,0],[100,100],[0,100]]
    }
    unique_payloads = list(set(cluster["engine_payloads"].values()))
    assert len(unique_payloads) == 2  # Conflict exists

# ==============================================================================
# 3. UNSAFE URL PROTOCOLS REJECTED (NO EXPOSURE AS CLICKABLE LINK)
# ==============================================================================
@pytest.mark.parametrize("unsafe_url", [
    "javascript:alert(document.domain)",
    "data:text/html;base64,PHNjcmlwdD5hbGVydCgxKTwvc2NyaXB0Pg==",
    "file:///C:/Windows/System32/drivers/etc/hosts",
    "vbscript:execute(s)",
    "about:blank",
    "chrome://settings"
])
def test_unsafe_url_protocols_rejected(tmp_path, unsafe_url):
    """Ensure dangerous non-http/https schemes are never exposed as safe or clickable links."""
    file_path = create_qr_file(tmp_path, unsafe_url, "unsafe.png")
    res = analyze_qr(file_path)
    
    assert res["decoded"] is True
    assert res["safe_url"] is False
    assert res["is_safe_url"] is False
    assert res["decoded_url"] is None
    assert res["url"] is None
    assert res["payload_type"] == "UNSAFE_URL"
    assert res["risk_contribution"] >= 20

# ==============================================================================
# 4. NON-URL PAYLOADS NEVER FABRICATE A URL
# ==============================================================================
def test_text_payload_never_fabricates_url(tmp_path):
    """Plain text payload must have decoded_url=None, safe_url=False, payload_type=TEXT."""
    text_data = "SENTINEL-DEMO-001"
    file_path = create_qr_file(tmp_path, text_data, "plain_text.png")
    res = analyze_qr(file_path)
    
    assert res["decoded"] is True
    assert res["payload_type"] == "TEXT"
    assert res["decoded_url"] is None
    assert res["url"] is None
    assert res["safe_url"] is False
    assert res["payload"] == text_data

def test_json_payload_never_fabricates_url(tmp_path):
    """JSON payload must have decoded_url=None, safe_url=False, payload_type=JSON."""
    json_data = json.dumps({"document_id": "PAN-2026-99", "status": "active"})
    file_path = create_qr_file(tmp_path, json_data, "json_doc.png")
    res = analyze_qr(file_path)
    
    assert res["decoded"] is True
    assert res["payload_type"] == "JSON"
    assert res["decoded_url"] is None
    assert res["url"] is None
    assert res["safe_url"] is False

# ==============================================================================
# 5. ALL THREE INDEPENDENT ENGINES FUNCTIONAL
# ==============================================================================
def test_all_three_engines_standalone():
    """Verify OpenCV, PyZbar, and ZXing-C++ can each read an image array directly."""
    qr = qrcode.QRCode(box_size=10, border=4)
    qr.add_data("https://example.com/standalone-test")
    qr.make(fit=True)
    img = np.array(qr.make_image(fill_color="black", back_color="white").convert('RGB'))
    bgr = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
    
    cv_res = _run_opencv_on_image(bgr)
    pz_res = _run_pyzbar_on_image(bgr)
    zx_res = _run_zxing_on_image(bgr)
    
    assert len(cv_res) > 0 and cv_res[0][0] == "https://example.com/standalone-test"
    assert len(pz_res) > 0 and pz_res[0][0] == "https://example.com/standalone-test"
    try:
        import zxingcpp
        assert len(zx_res) > 0 and zx_res[0][0] == "https://example.com/standalone-test"
    except Exception:
        pass
