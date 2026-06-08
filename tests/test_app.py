import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'app'))

import pytest
import json
import threading
import time
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
    assert response.status_code == 200


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


# ── Test 5: Ride status endpoint exists ───────────────────────────────
def test_ride_status_endpoint(client):
    """GET /ride-status should return 200."""
    response = client.get('/ride-status')
    assert response.status_code == 200


# ── Test 6: MQTT broker connection ────────────────────────────────────
def test_mqtt_broker_connection():
    """
    Verify we can connect to the MQTT broker,
    publish a message, and receive it back.
    Requires MQTT_BROKER env var or defaults to localhost.
    """
    import paho.mqtt.client as mqtt

    broker   = os.environ.get("MQTT_BROKER", "localhost")
    port     = 1883
    topic    = "test/ci"
    message  = json.dumps({"test": "ci-pipeline", "status": "ok"})
    received = []
    connected = threading.Event()
    msg_event = threading.Event()

    def on_connect(client, userdata, flags, reason_code, properties):
        if reason_code == 0:
            connected.set()
            client.subscribe(topic)

    def on_message(client, userdata, msg):
        received.append(json.loads(msg.payload.decode()))
        msg_event.set()

    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="ci-test-client")
    client.on_connect = on_connect
    client.on_message = on_message

    client.connect(broker, port, keepalive=10)
    client.loop_start()

    # Wait for connection
    assert connected.wait(timeout=10), "Could not connect to MQTT broker within 10 seconds"

    # Publish a test message
    client.publish(topic, message)

    # Wait for it to come back
    assert msg_event.wait(timeout=10), "Did not receive MQTT message within 10 seconds"

    # Verify the message content
    assert len(received) > 0
    assert received[0]["test"] == "ci-pipeline"
    assert received[0]["status"] == "ok"

    client.loop_stop()
    client.disconnect()