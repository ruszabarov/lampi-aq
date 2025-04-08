#!/usr/bin/env python3
import time
import json
import paho.mqtt.client as mqtt
import shelve

# You might have some common MQTT constants defined in lamp_common.
# For this updated service, either update lamp_common accordingly or
# define the needed constants here.
from lamp_common import (  # adjust the import as needed, or duplicate definitions below
    MQTT_BROKER_HOST,
    MQTT_BROKER_PORT,
    MQTT_BROKER_KEEP_ALIVE_SECS,
    MQTT_VERSION,
    client_state_topic
)

# New topic names for the air quality monitor service.
TOPIC_SET_SENSOR_DATA = "air_quality_monitor/set_sensor_data"
TOPIC_SENSOR_CHANGE_NOTIFICATION = "air_quality_monitor/sensor_change_notification"

# File to store sensor data persistently
SENSOR_STATE_FILENAME = "sensor_state"

# MQTT client ID
MQTT_CLIENT_ID = "air_quality_monitor"

# Maximum wait time for MQTT connection retries
MAX_STARTUP_WAIT_SECS = 10.0

# Exception used if invalid sensor data is received
class InvalidSensorData(Exception):
    pass

class AirQualityMonitor(object):
    def __init__(self):
        # Create and configure the MQTT client
        self._client = self._create_and_configure_broker_client()
        
        # Open the shelve database for persistent sensor state.
        # We initialize with default values if not already set.
        self.db = shelve.open(SENSOR_STATE_FILENAME, writeback=True)
        if 'pm1_0' not in self.db:
            self.db['pm1_0'] = 0.0
        if 'pm2_5' not in self.db:
            self.db['pm2_5'] = 0.0
        if 'pm10' not in self.db:
            self.db['pm10'] = 0.0
        if 'temperature' not in self.db:
            self.db['temperature'] = 0.0
        if 'humidity' not in self.db:
            self.db['humidity'] = 0.0
        if 'pressure' not in self.db:
            self.db['pressure'] = 0.0

        # Publish the initial sensor state to the MQTT notification topic.
        self.publish_state()

    def _create_and_configure_broker_client(self):
        """
        Create an MQTT client, configure the necessary callbacks,
        and set a will message for unexpected disconnects.
        """
        client = mqtt.Client(client_id=MQTT_CLIENT_ID, protocol=MQTT_VERSION)
        client.will_set(client_state_topic(MQTT_CLIENT_ID),
                        "0", qos=2, retain=True)
        client.enable_logger()
        client.on_connect = self.on_connect
        
        # Subscribe to sensor data updates published from the sensor script.
        client.message_callback_add(TOPIC_SET_SENSOR_DATA,
                                    self.on_message_sensor_data)
        # Default callback for any unexpected messages.
        client.on_message = self.default_on_message

        return client

    def serve(self):
        """
        Connect to the MQTT broker (with retries),
        then loop forever to handle MQTT messages.
        """
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
        """
        When connected, signal the online state and subscribe to the sensor update topic.
        Publish the current sensor state.
        """
        self._client.publish(client_state_topic(MQTT_CLIENT_ID),
                             "1", qos=2, retain=True)
        self._client.subscribe(TOPIC_SET_SENSOR_DATA, qos=1)
        # Publish current sensor state on connection.
        self.publish_state()

    def default_on_message(self, client, userdata, msg):
        """
        Log any unexpected MQTT messages.
        """
        print("Received unexpected message on topic " +
              msg.topic + " with payload '" + str(msg.payload) + "'")

    def on_message_sensor_data(self, client, userdata, msg):
        """
        Callback when the sensor script publishes new sensor data.
        The expected JSON payload should include:
          - pm1_0
          - pm2_5
          - pm10
          - temperature
          - humidity
          - pressure
        """
        try:
            new_data = json.loads(msg.payload.decode('utf-8'))
            
            # Required keys for sensor data.
            required_keys = ['pm1_0', 'pm2_5', 'pm10', 'temperature', 'humidity', 'pressure']
            for key in required_keys:
                if key not in new_data:
                    raise InvalidSensorData(f"Missing key: {key}")
                # Convert and validate the value to a float.
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
        """
        Sync the shelve database to disk.
        """
        self.db.sync()

    def publish_state(self):
        """
        Publish the current sensor state to the notification MQTT topic.
        """
        state = {
            'pm1_0': self.db['pm1_0'],
            'pm2_5': self.db['pm2_5'],
            'pm10': self.db['pm10'],
            'temperature': self.db['temperature'],
            'humidity': self.db['humidity'],
            'pressure': self.db['pressure']
        }
        self._client.publish(TOPIC_SENSOR_CHANGE_NOTIFICATION,
                             json.dumps(state).encode('utf-8'),
                             qos=1, retain=True)

if __name__ == '__main__':
    aq_monitor = AirQualityMonitor()
    aq_monitor.serve()
