#!/usr/bin/env python3
import time
import json
import pigpio
import paho.mqtt.client as mqtt
import shelve

from air_quality_common import *

PIN_R = 19
PIN_G = 26
PIN_B = 13
PINS = [PIN_R, PIN_G, PIN_B]
PWM_RANGE = 1000
PWM_FREQUENCY = 1000
SENSOR_STATE_FILENAME = "sensor_state"
MQTT_CLIENT_ID = "lampi"
MAX_STARTUP_WAIT_SECS = 10.0

class InvalidSensorData(Exception):
    pass

class LampDriver:
    def __init__(self):
        self._gpio = pigpio.pi()
        for pin in PINS:
            self._gpio.set_mode(pin, pigpio.OUTPUT)
            self._gpio.set_PWM_frequency(pin, PWM_FREQUENCY)
            self._gpio.set_PWM_range(pin, PWM_RANGE)
            self._gpio.set_PWM_dutycycle(pin, 0)

    def change_color(self, red_dc, green_dc, blue_dc):
        for pin, dc in zip(PINS, (red_dc, green_dc, blue_dc)):
            self._gpio.set_PWM_dutycycle(pin, dc)


class AirQualityService:
    def __init__(self):
        # thresholds (µg/m3 for PM, % for humidity)
        self.PM25_DANGER = 75.0
        self.PM10_DANGER = 150.0
        self.HUMIDITY_WARNING = 80.0

        # lamp controller
        self.lamp = LampDriver()

        # MQTT client
        self._client = self._create_and_configure_broker_client()

        # persistent state store
        self.db = shelve.open(SENSOR_STATE_FILENAME, writeback=True)
        for key in ('pm25', 'pm10', 'temperature', 'humidity',
                    'pressure', 'altitude'):
            if key not in self.db:
                self.db[key] = 0.0

        # publish initial state & lamp colour
        self.publish_state()
        self._update_lamp_color()

    def _create_and_configure_broker_client(self):
        client = mqtt.Client(client_id=MQTT_CLIENT_ID,
                             protocol=MQTT_VERSION)
        client.will_set(client_state_topic(MQTT_CLIENT_ID),
                        "0", qos=2, retain=True)
        client.enable_logger()
        client.on_connect = self.on_connect

        client.message_callback_add(
            TOPIC_SET_SENSOR_DATA,
            self.on_message_sensor_data
        )
        client.on_message = self.default_on_message
        return client

    def serve(self):
        start = time.time()
        while True:
            try:
                self._client.connect(
                    MQTT_BROKER_HOST,
                    port=MQTT_BROKER_PORT,
                    keepalive=MQTT_BROKER_KEEP_ALIVE_SECS
                )
                print("Connected to broker")
                break
            except ConnectionRefusedError:
                elapsed = time.time() - start
                if elapsed < MAX_STARTUP_WAIT_SECS:
                    print(f"Retrying MQTT connect (delay={elapsed:.0f}s)")
                    time.sleep(1)
                else:
                    raise

        self._client.loop_forever()

    def on_connect(self, client, userdata, flags, rc):
        self._client.publish(
            client_state_topic(MQTT_CLIENT_ID),
            "1", qos=2, retain=True
        )
        self._client.subscribe(TOPIC_SET_SENSOR_DATA, qos=1)
        self.publish_state()
        self._update_lamp_color()

    def default_on_message(self, client, userdata, msg):
        print(f"Unexpected msg on {msg.topic}: {msg.payload!r}")

    def on_message_sensor_data(self, client, userdata, msg):
        try:
            payload = msg.payload.decode('utf-8')
            new_data = json.loads(payload)

            required = ('pm25', 'pm10', 'temperature',
                        'humidity', 'pressure', 'altitude')
            for k in required:
                if k not in new_data:
                    raise InvalidSensorData(f"Missing key {k}")
                new_data[k] = float(new_data[k])

            for k in required:
                self.db[k] = round(new_data[k], 2)

            self.db.sync()
            self.publish_state()
            self._update_lamp_color()

        except (json.JSONDecodeError, InvalidSensorData) as e:
            print("Error processing sensor data:", e)

    def publish_state(self):
        state = {k: self.db[k] for k in (
            'pm25', 'pm10', 'temperature',
            'humidity', 'pressure', 'altitude'
        )}
        self._client.publish(
            TOPIC_LAMPI_CHANGE_NOTIFICATION,
            json.dumps(state).encode('utf-8'),
            qos=1, retain=True
        )

    def _update_lamp_color(self):
        h = self.db['humidity']
        p25 = self.db['pm25']
        p10 = self.db['pm10']

        # Humidity warning (yellow)
        if h > self.HUMIDITY_WARNING:
            colour = (PWM_RANGE, PWM_RANGE, 0)
        # Danger from particulates (red)
        elif p25 > self.PM25_DANGER or p10 > self.PM10_DANGER:
            colour = (PWM_RANGE, 0, 0)
        # All good (green)
        else:
            colour = (0, PWM_RANGE, 0)

        self.lamp.change_color(*colour)


if __name__ == '__main__':
    AirQualityService().serve()
