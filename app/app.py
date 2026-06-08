from flask import Flask, request, jsonify, render_template
from prometheus_flask_exporter import PrometheusMetrics

app = Flask(__name__)
metrics = PrometheusMetrics(app)

# Custom application-level metrics
ride_counter = metrics.counter(
    'bodaconnect_ride_requests_total', 'Total number of ride requests submitted'
)
active_trips_gauge = metrics.gauge(
    'bodaconnect_active_trips', 'Number of trips currently in the system'
)

# In-memory trip storage (resets on restart — no DB needed for this exercise)
trips = []
rider_trips = [
    {"id": 1, "pickup": "Nyerere Square", "destination": "UDOM",
        "status": "In Progress", "customer": "Amina"},
    {"id": 2, "pickup": "Majengo", "destination": "Miyuji",
        "status": "Completed", "customer": "Baraka"},
]


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/request-ride", methods=["POST"])
def request_ride():
    data = request.json
    pickup = data.get("pickup")
    destination = data.get("destination")
    customer = data.get("customer", "Anonymous")

    if not pickup or not destination:
        return jsonify({"error": "Pickup and destination are required"}), 400

    trip = {
        "id": len(rider_trips) + 1,
        "message": "Ride request received! A rider will be assigned shortly.",
        "pickup": pickup,
        "destination": destination,
        "customer": customer,
        "status": "Pending"
    }
    trips.append(trip)
    rider_trips.append(trip)
    return jsonify(trip), 201


@app.route("/rider-dashboard")
def rider_dashboard():
    return jsonify({
        "rider": "John Mwangi",
        "status": "Online",
        "assigned_trips": rider_trips,
        "total_trips_today": len(rider_trips),
        "new_requests": len([t for t in rider_trips if t["status"] == "Pending"]),
        "earnings_today": "TZS 12,500"
    })


@app.route("/trips")
def get_trips():
    return jsonify({"total": len(trips), "trips": trips})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
