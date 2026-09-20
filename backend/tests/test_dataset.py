import pytest
import os
import csv
import json
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from fastapi.testclient import TestClient
from app import app
from auth.jwt import create_access_token
import io

client = TestClient(app)

DATASET_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "sentinel_dataset")
DOCS_DIR = os.path.join(DATASET_DIR, "documents")
LABELS_FILE = os.path.join(DATASET_DIR, "labels.csv")
METADATA_FILE = os.path.join(DATASET_DIR, "metadata.json")

@pytest.fixture
def auth_token():
    return create_access_token(data={"sub": "testuser", "id": "user123"})

@pytest.fixture
def auth_headers(auth_token):
    return {"Authorization": f"Bearer {auth_token}"}

def test_dataset_exists():
    assert os.path.exists(DATASET_DIR), "Dataset directory missing"
    assert os.path.exists(DOCS_DIR), "Documents directory missing"
    assert os.path.exists(LABELS_FILE), "labels.csv missing"
    assert os.path.exists(METADATA_FILE), "metadata.json missing"
    
    # Check 10 files
    files = [f for f in os.listdir(DOCS_DIR) if f.endswith('.jpg')]
    assert len(files) == 10, "Expected exactly 10 synthetic documents"

def test_metadata_structure():
    with open(METADATA_FILE, 'r') as f:
        meta = json.load(f)
    assert len(meta) == 10
    
    ids = [m["synthetic_id"] for m in meta]
    assert len(set(ids)) == 10, "Synthetic IDs must be unique"
    
    for m in meta:
        assert m["label"] in ["LIKELY_AUTHENTIC", "REVIEW_REQUIRED", "HIGH_SUSPICION"]
        assert "filename" in m

def test_dataset_analysis(auth_headers):
    # Just test the first sample to ensure the pipeline works
    with open(METADATA_FILE, 'r') as f:
        meta = json.load(f)
        
    sample = meta[0]
    filepath = os.path.join(DOCS_DIR, sample["filename"])
    
    assert os.path.exists(filepath), f"File {filepath} not found"
    
    with open(filepath, "rb") as img:
        files = {"file": (sample["filename"], img, "image/jpeg")}
        response = client.post("/api/analyze/", files=files, headers=auth_headers)
        
    assert response.status_code == 200
    res = response.json()
    assert "data" in res
    data = res["data"]
    assert "risk_score" in data
    assert "classification" in data
    assert "evidence" in data
    assert isinstance(data["evidence"], list)
