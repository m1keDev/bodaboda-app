from flask import Flask, request, jsonify, render_template
from prometheus_flask_exporter import PrometheusMetrics
from prometheus_client import Counter, Gauge
import paho.mqtt.client as mqtt
import json
import threading
import datetime

app = Flask(__name__)
metrics = PrometheusMetrics(app)

# ── Custom Prometheus metrics ──────────────────────────────────────────
ride_requests_total = Counter(
    'bodaconnect_ride_requests_total',
    'Total number of ride requests submitted'
)
active_trips_gauge = Gauge(
    'bodaconnect_active_trips',
    'Number of trips currently in the system'
)

# ── In-memory storage ──────────────────────────────────────────────────
trips = []
rider_trips = [
    {"id": 1, "pickup": "Nyerere Square", "destination": "UDOM", "status": "In Progress", "customer": "Amina"},
    {"id": 2, "pickup": "Majengo", "destination": "Miyuji", "status": "Completed", "customer": "Baraka"},
]
active_trips_gauge.set(len(rider_trips))

# Latest ride status received from driver
latest_status = {}

# ══════════════════════════════════════════════════════════════════════
# MQTT SETUP
# ══════════════════════════════════════════════════════════════════════

MQTT_BROKER = "mosquitto"
MQTT_PORT   = 1883

mqtt_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="bodaconnect-backend")


def on_connect(client, userdata, flags, reason_code, properties):
    """Called when the backend connects to the broker."""
    if reason_code == 0:
        print("[MQTT] Backend connected to Mosquitto broker")
        client.subscribe("ride/status")
        print("[MQTT] Subscribed to topic: ride/status")
    else:
        print(f"[MQTT] Connection failed with code {reason_code}")


def on_message(client, userdata, msg):
    """Called when a message arrives on a subscribed topic."""
    global latest_status
    try:
        payload = json.loads(msg.payload.decode())
        print(f"[MQTT] Message received on {msg.topic}: {payload}")

        if msg.topic == "ride/status":
            latest_status = payload
            ride_id    = payload.get("ride_id")
            new_status = payload.get("status")
            for trip in rider_trips:
                if trip["id"] == ride_id:
                    trip["status"] = new_status
                    print(f"[MQTT] Trip {ride_id} status updated to: {new_status}")
                    break
    except Exception as e:
        print(f"[MQTT] Error processing message: {e}")


def on_disconnect(client, userdata, flags, reason_code, properties):
    print(f"[MQTT] Disconnected from broker (code: {reason_code})")


mqtt_client.on_connect    = on_connect
mqtt_client.on_message    = on_message
mqtt_client.on_disconnect = on_disconnect


def start_mqtt():
    """Connect to broker and start the background network loop."""
    try:
        mqtt_client.connect(MQTT_BROKER, MQTT_PORT, keepalive=60)
        mqtt_client.loop_start()
        print("[MQTT] Background loop started")
    except Exception as e:
        print(f"[MQTT] Could not connect to broker: {e}")


threading.Thread(target=start_mqtt, daemon=True).start()


# ══════════════════════════════════════════════════════════════════════
# FLASK ROUTES
# ══════════════════════════════════════════════════════════════════════

@app.route("/")
def home():
    return render_template("index.html")


@app.route("/request-ride", methods=["POST"])
def request_ride():
    data        = request.json
    pickup      = data.get("pickup")
    destination = data.get("destination")
    customer    = data.get("customer", "Anonymous")

    if not pickup or not destination:
        return jsonify({"error": "Pickup and destination are required"}), 400

    trip = {
        "id":          len(rider_trips) + 1,
        "message":     "Ride request received! A rider will be assigned shortly.",
        "pickup":      pickup,
        "destination": destination,
        "customer":    customer,
        "status":      "Pending",
        "timestamp":   datetime.datetime.now().isoformat()
    }
    trips.append(trip)
    rider_trips.append(trip)

    ride_requests_total.inc()
    active_trips_gauge.set(len(rider_trips))

    mqtt_payload = json.dumps({
        "ride_id":     trip["id"],
        "customer":    trip["customer"],
        "pickup":      trip["pickup"],
        "destination": trip["destination"],
        "status":      trip["status"],
        "timestamp":   trip["timestamp"]
    })
    result = mqtt_client.publish("ride/request", mqtt_payload)
    if result.rc == mqtt.MQTT_ERR_SUCCESS:
        print(f"[MQTT] Published ride request #{trip['id']} to ride/request")
    else:
        print(f"[MQTT] Failed to publish ride request (rc={result.rc})")

    return jsonify(trip), 201


@app.route("/rider-dashboard")
def rider_dashboard():
    return jsonify({
        "rider":             "John Mwangi",
        "status":            "Online",
        "assigned_trips":    rider_trips,
        "total_trips_today": len(rider_trips),
        "new_requests":      len([t for t in rider_trips if t["status"] == "Pending"]),
        "earnings_today":    "TZS 12,500"
    })


@app.route("/trips")
def get_trips():
    return jsonify({"total": len(trips), "trips": trips})


@app.route("/ride-status")
def ride_status():
    """Frontend polls this to get the latest status update from the driver."""
    return jsonify(latest_status)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)