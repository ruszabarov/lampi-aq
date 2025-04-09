#!/usr/bin/env python3
import time
import random
import json
import paho.mqtt.client as mqtt
from air_quality_common import (
    TOPIC_SET_SENSOR_DATA,
    MQTT_BROKER_HOST,
    MQTT_BROKER_PORT,
    MQTT_BROKER_KEEP_ALIVE_SECS,
    MQTT_VERSION
)

MQTT_CLIENT_ID = "sensor_simulator"

# Define plausible ranges and delta settings for continuous variation.
SENSOR_CONFIG = {
    "pm25": {"min": 0.0, "max": 100.0, "delta": 1.0, "start": 10.0},
    "pm10": {"min": 0.0, "max": 150.0, "delta": 1.5, "start": 20.0},
    "temperature": {"min": 15.0, "max": 30.0, "delta": 0.2, "start": 22.0},
    "humidity": {"min": 20.0, "max": 70.0, "delta": 0.5, "start": 45.0},
    "pressure": {"min": 950.0, "max": 1050.0, "delta": 0.8, "start": 1013.0}
}

def clamp(value, minimum, maximum):
    return max(minimum, min(maximum, value))

class ContinuousSensorSimulator:
    def __init__(self):
        # Set initial state for each sensor based on config.
        self.state = {key: cfg["start"] for key, cfg in SENSOR_CONFIG.items()}

    def update_state(self):
        """
        For each sensor value, update by adding a small delta chosen at random
        from a uniform distribution within [-delta, delta]. The new value is clamped
        to the defined min and max ranges.
        """
        for key, cfg in SENSOR_CONFIG.items():
            delta = random.uniform(-cfg["delta"], cfg["delta"])
            new_value = self.state[key] + delta
            self.state[key] = round(clamp(new_value, cfg["min"], cfg["max"]), 2)
        # Optionally include an identifier for the sensor source.
        self.state["client"] = MQTT_CLIENT_ID
        return self.state

def on_connect(client, userdata, flags, rc):
    print("Connected with result code:", rc)

def main():
    # Create and configure the MQTT client.
    client = mqtt.Client(client_id=MQTT_CLIENT_ID, protocol=MQTT_VERSION)
    client.on_connect = on_connect
    client.enable_logger()

    # Connect to the MQTT broker.
    client.connect(MQTT_BROKER_HOST,
                   port=MQTT_BROKER_PORT,
                   keepalive=MQTT_BROKER_KEEP_ALIVE_SECS)
    client.loop_start()  # Start the MQTT network loop in the background.

    simulator = ContinuousSensorSimulator()

    try:
        # Publish sensor readings indefinitely at a short interval (e.g., 1 second).
        while True:
            sensor_data = simulator.update_state()
            payload = json.dumps(sensor_data).encode('utf-8')
            client.publish(TOPIC_SET_SENSOR_DATA, payload, qos=1)
            print("Published sensor data:", sensor_data)
            time.sleep(1)
    except KeyboardInterrupt:
        print("Exiting sensor simulator...")
    finally:
        client.loop_stop()

if __name__ == '__main__':
    main()
