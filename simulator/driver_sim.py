"""
BodaConnect — Driver Simulator
================================
Simulates a bodaboda driver that:
  1. Subscribes to ride/request
  2. Automatically accepts and progresses each ride
  3. Publishes status updates to ride/status

Runs as a standalone Docker container.
"""

import paho.mqtt.client as mqtt
import json
import time
import datetime
import threading

MQTT_BROKER = "mosquitto"
MQTT_PORT   = 1883
DRIVER_NAME = "John Mwangi"

# Track which rides we are already handling
# so we don't process the same ride twice
handled_rides = set()


def publish_status(client, ride_id, status):
    """Publish a ride status update to ride/status."""
    payload = json.dumps({
        "ride_id":   ride_id,
        "status":    status,
        "driver":    DRIVER_NAME,
        "timestamp": datetime.datetime.now().isoformat()
    })
    client.publish("ride/status", payload)
    print(f"[DRIVER] Published status for ride #{ride_id}: {status}")


def handle_ride(client, ride):
    """
    Simulate a driver handling a ride.
    Runs in a background thread so the simulator
    can handle multiple rides concurrently.
    """
    ride_id     = ride.get("ride_id")
    customer    = ride.get("customer", "Unknown")
    pickup      = ride.get("pickup")
    destination = ride.get("destination")

    print(f"\n[DRIVER] New ride request received")
    print(f"[DRIVER] Ride ID    : #{ride_id}")
    print(f"[DRIVER] Customer   : {customer}")
    print(f"[DRIVER] Pickup     : {pickup}")
    print(f"[DRIVER] Destination: {destination}")

    # Stage 1 — Accept the ride after a short delay
    time.sleep(3)
    publish_status(client, ride_id, "Accepted")

    # Stage 2 — Mark as In Progress (driver has picked up passenger)
    time.sleep(5)
    publish_status(client, ride_id, "In Progress")

    # Stage 3 — Mark as Completed (trip done)
    time.sleep(8)
    publish_status(client, ride_id, "Completed")

    print(f"[DRIVER] Ride #{ride_id} completed.\n")


def on_connect(client, userdata, flags, reason_code, properties):
    """Called when the simulator connects to the broker."""
    if reason_code == 0:
        print(f"[DRIVER] Connected to Mosquitto broker at {MQTT_BROKER}:{MQTT_PORT}")
        client.subscribe("ride/request")
        print("[DRIVER] Subscribed to topic: ride/request")
        print("[DRIVER] Waiting for ride requests...\n")
    else:
        print(f"[DRIVER] Connection failed (rc={reason_code})")


def on_message(client, userdata, msg):
    """Called when a new ride request arrives."""
    try:
        ride    = json.loads(msg.payload.decode())
        ride_id = ride.get("ride_id")

        # Avoid handling the same ride twice
        if ride_id in handled_rides:
            return
        handled_rides.add(ride_id)

        # Handle the ride in a background thread
        # so we don't block the MQTT loop
        thread = threading.Thread(
            target=handle_ride,
            args=(client, ride),
            daemon=True
        )
        thread.start()

    except Exception as e:
        print(f"[DRIVER] Error processing message: {e}")


def on_disconnect(client, userdata, flags, reason_code, properties):
    print(f"[DRIVER] Disconnected (rc={reason_code}). Reconnecting...")


def main():
    print("=" * 50)
    print("  BodaConnect Driver Simulator")
    print(f"  Driver: {DRIVER_NAME}")
    print(f"  Broker: {MQTT_BROKER}:{MQTT_PORT}")
    print("=" * 50 + "\n")

    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="bodaconnect-driver-sim")
    client.on_connect    = on_connect
    client.on_message    = on_message
    client.on_disconnect = on_disconnect

    # Keep trying to connect in case broker isn't ready yet
    while True:
        try:
            client.connect(MQTT_BROKER, MQTT_PORT, keepalive=60)
            # loop_forever blocks here and handles reconnects automatically
            client.loop_forever()
        except Exception as e:
            print(f"[DRIVER] Could not connect: {e}. Retrying in 5 seconds...")
            time.sleep(5)


if __name__ == "__main__":
    main()