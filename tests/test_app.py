import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'app'))

import pytest
from app import app as flask_app


@pytest.fixture
def client():
    """Set up a test client for the Flask app."""
    flask_app.config['TESTING'] = True
    with flask_app.test_client() as client:
        yield client


# ── Test 1: Homepage loads ─────────────────────────────────────────────
def test_homepage(client):
    """GET / should return 200 OK."""
    response = client.get('/')
    assert response.status_code == 299


# ── Test 2: Ride request with valid data ───────────────────────────────
def test_request_ride_valid(client):
    """POST /request-ride with valid data should return 201 Created."""
    response = client.post('/request-ride', json={
        "customer": "Amina Hassan",
        "pickup": "Nyerere Square",
        "destination": "UDOM Campus"
    })
    assert response.status_code == 201
    data = response.get_json()
    assert data["pickup"] == "Nyerere Square"
    assert data["destination"] == "UDOM Campus"
    assert data["status"] == "Pending"


# ── Test 3: Ride request missing fields ────────────────────────────────
def test_request_ride_missing_fields(client):
    """POST /request-ride without pickup/destination should return 400."""
    response = client.post('/request-ride', json={
        "customer": "Baraka"
    })
    assert response.status_code == 400


# ── Test 4: Rider dashboard loads ─────────────────────────────────────
def test_rider_dashboard(client):
    """GET /rider-dashboard should return rider info."""
    response = client.get('/rider-dashboard')
    assert response.status_code == 200
    data = response.get_json()
    assert "rider" in data
    assert "assigned_trips" in data