"""
Tests for /api/contact endpoint
"""
import pytest
from fastapi.testclient import TestClient
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app import app

client = TestClient(app)

def test_contact_validation_missing_fields():
    response = client.post("/api/contact", json={"name": "A"})
    assert response.status_code == 422 # FastAPI Pydantic validation error

def test_contact_validation_invalid_email():
    response = client.post("/api/contact", json={
        "name": "Jane Investigator",
        "email": "not-an-email",
        "organization": "Cyber Security Lab",
        "subject": "Evaluation",
        "message": "Testing invalid email handling."
    })
    assert response.status_code == 422

def test_contact_valid_submission():
    response = client.post("/api/contact", json={
        "name": "Forensic Officer",
        "email": "officer@forensic-lab.org",
        "organization": "National Forensic Unit",
        "subject": "SENTINEL Demonstration Request",
        "phone": "+91 9876543210",
        "message": "We would like to schedule a demonstration of the 3D forensic screening platform."
    })
    assert response.status_code == 200
    data = response.json()
    assert data.get("success") is True
    assert "Message sent successfully" in data.get("message", "")
