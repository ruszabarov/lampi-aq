#!/usr/bin/env python3
import time
import json
import paho.mqtt.client as mqtt
import shelve

from air_quality_common import *

SENSOR_STATE_FILENAME = "sensor_state"

MQTT_CLIENT_ID = "lampi"

MAX_STARTUP_WAIT_SECS = 10.0

class InvalidSensorData(Exception):
    pass

class AirQualityService(object):
    def __init__(self):
        # Create and configure the MQTT client using the parameters from common.
        self._client = self._create_and_configure_broker_client()
        
        # Open the shelve database for persistent sensor state.
        # Initialize with default values if not already set.
        self.db = shelve.open(SENSOR_STATE_FILENAME, writeback=True)
        for key in ['pm25', 'pm10', 'temperature', 'humidity', 'pressure']:
            if key not in self.db:
                self.db[key] = 0.0

        # Publish the initial sensor state to the MQTT notification topic.
        self.publish_state()

    def _create_and_configure_broker_client(self):
        client = mqtt.Client(client_id=MQTT_CLIENT_ID, protocol=MQTT_VERSION)
        client.will_set(client_state_topic(MQTT_CLIENT_ID),
                        "0", qos=2, retain=True)
        client.enable_logger()
        client.on_connect = self.on_connect
        
        # Subscribe to sensor data updates published by the sensor script.
        client.message_callback_add(TOPIC_SET_SENSOR_DATA,
                                    self.on_message_sensor_data)
        client.on_message = self.default_on_message

        return client

    def serve(self):
        start_time = time.time()
        while True:
            try:
                self._client.connect(MQTT_BROKER_HOST,
                                     port=MQTT_BROKER_PORT,
                                     keepalive=MQTT_BROKER_KEEP_ALIVE_SECS)
                print("Connected to broker")
                break
            except ConnectionRefusedError as e:
                current_time = time.time()
                delay = current_time - start_time
                if delay < MAX_STARTUP_WAIT_SECS:
                    print("Error connecting to broker; delaying and retrying; delay={:.0f}".format(delay))
                    time.sleep(1)
                else:
                    raise e
        self._client.loop_forever()

    def on_connect(self, client, userdata, rc, unknown):
        self._client.publish(client_state_topic(MQTT_CLIENT_ID),
                             "1", qos=2, retain=True)
        self._client.subscribe(TOPIC_LAMPI_CHANGE_NOTIFICATION, qos=1)
        # Publish current sensor state upon connection.
        self.publish_state()

    def default_on_message(self, client, userdata, msg):
        print("Received unexpected message on topic " + msg.topic + " with payload '" + str(msg.payload) + "'")

    def on_message_sensor_data(self, client, userdata, msg):
        """
        Callback when new sensor data is received.
        Expected JSON payload includes:
          - pm25
          - pm10
          - temperature
          - humidity
          - pressure
        """
        try:
            new_data = json.loads(msg.payload.decode('utf-8'))
            
            # Define the required sensor keys.
            required_keys = ['pm25', 'pm10', 'temperature', 'humidity', 'pressure']
            for key in required_keys:
                if key not in new_data:
                    raise InvalidSensorData(f"Missing key: {key}")
                try:
                    new_data[key] = float(new_data[key])
                except ValueError:
                    raise InvalidSensorData(f"Invalid value for {key}: {new_data[key]}")

            # Update the database with new values (rounding to 2 decimal places).
            for key in required_keys:
                self.db[key] = round(new_data[key], 2)
            self.write_current_settings_to_storage()
            self.publish_state()
        except (json.JSONDecodeError, InvalidSensorData) as e:
            print("Error processing sensor data: " + str(e))

    def write_current_settings_to_storage(self):
        self.db.sync()

    def publish_state(self):
        state = {
            'pm25': self.db['pm25'],
            'pm10': self.db['pm10'],
            'temperature': self.db['temperature'],
            'humidity': self.db['humidity'],
            'pressure': self.db['pressure']
        }
        self._client.publish(TOPIC_LAMPI_CHANGE_NOTIFICATION,
                             json.dumps(state).encode('utf-8'),
                             qos=1, retain=True)

if __name__ == '__main__':
    aq_monitor = AirQualityService()
    aq_monitor.serve()
