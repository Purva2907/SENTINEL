import os
import sys
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from forensic.pipeline import process_document
from forensic.fictional_detector import is_fictional_document

SAMPLE_CLEAN = "data/samples/fictional_aadhaar_sodhi.jpg"
SAMPLE_DEMO = "data/samples/fictional_aadhaar_demo_marked.jpg"


def test_fictional_sample_clean_detection():
    """Verify clean fictional sample gets low authenticity score and high risk score."""
    if not os.path.exists(SAMPLE_CLEAN):
        pytest.skip(f"Sample file {SAMPLE_CLEAN} not found")

    is_fictional, reason = is_fictional_document(SAMPLE_CLEAN)
    assert is_fictional is True, f"Expected fictional detection, got reason: {reason}"

    res = process_document(SAMPLE_CLEAN)

    assert res["authenticity_score"] <= 20, f"Expected authenticity <= 20, got {res['authenticity_score']}"
    assert res["risk_score"] >= 80, f"Expected risk >= 80, got {res['risk_score']}"
    assert res["authenticity_score"] + res["risk_score"] == 100, "Authenticity and risk must be strictly coupled"
    assert res["classification"] == "High Suspicion"
    assert res["is_high_suspicion_eligible"] is True
    assert "Fictional identity" in res["gate_reason"]
    assert len(res["evidence_table"]) == 15
    assert len(res["heatmap"]) > 1000
    assert res["risk_breakdown"]["image_forensics"] >= 25


def test_fictional_sample_demo_marked_detection():
    """Verify demonstration marked fictional sample gets low authenticity score and high risk score."""
    if not os.path.exists(SAMPLE_DEMO):
        pytest.skip(f"Sample file {SAMPLE_DEMO} not found")

    is_fictional, reason = is_fictional_document(SAMPLE_DEMO)
    assert is_fictional is True, f"Expected fictional detection, got reason: {reason}"

    res = process_document(SAMPLE_DEMO)

    assert res["authenticity_score"] <= 20, f"Expected authenticity <= 20, got {res['authenticity_score']}"
    assert res["risk_score"] >= 80, f"Expected risk >= 80, got {res['risk_score']}"
    assert res["authenticity_score"] + res["risk_score"] == 100, "Authenticity and risk must be strictly coupled"
    assert res["classification"] == "High Suspicion"
    assert res["is_high_suspicion_eligible"] is True
    assert "Fictional identity" in res["gate_reason"]
    assert len(res["evidence_table"]) == 15
    assert len(res["heatmap"]) > 1000
    assert any("DEMONSTRATION" in ev for ev in res["negative_evidence"])


def test_regular_sample_not_flagged_as_fictional():
    """Verify regular non-fictional sample is not falsely flagged."""
    real_sample = "data/sentinel_dataset/documents/SYN-TEST-0001.jpg"
    if not os.path.exists(real_sample):
        pytest.skip(f"Sample file {real_sample} not found")

    is_fictional, _ = is_fictional_document(real_sample)
    assert is_fictional is False, "Regular dataset image must NOT be flagged as fictional"
