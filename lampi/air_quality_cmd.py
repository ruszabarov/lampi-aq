#!/usr/bin/env python3
import json
import sys
import argparse
import time
import paho.mqtt.client as mqtt
from air_quality_common import (
    MQTT_BROKER_HOST,
    MQTT_BROKER_PORT,
    MQTT_BROKER_KEEP_ALIVE_SECS,
    TOPIC_SENSOR_CHANGE_NOTIFICATION,
    TOPIC_SET_SENSOR_DATA
)

MQTT_CLIENT_ID = 'air_quality_cmd'

class AirQualityCmd:
    def __init__(self):
        self.received_sensor_state = None
        self.client = mqtt.Client(client_id=MQTT_CLIENT_ID)
        self.client.enable_logger()
        self.client.on_connect = self.on_connect
        self.client.connect(MQTT_BROKER_HOST,
                            port=MQTT_BROKER_PORT,
                            keepalive=MQTT_BROKER_KEEP_ALIVE_SECS)
        self._wait_for_sensor_state()
        self.client.loop_start()

    def build_argument_parser(self):
        parser = argparse.ArgumentParser(
            description="Update and view the air quality sensor state."
        )
        parser.add_argument('--pm1_0', type=float, default=None,
                            help='PM1.0 sensor reading')
        parser.add_argument('--pm2_5', type=float, default=None,
                            help='PM2.5 sensor reading')
        parser.add_argument('--pm10', type=float, default=None,
                            help='PM10 sensor reading')
        parser.add_argument('--temperature', type=float, default=None,
                            help='Temperature reading')
        parser.add_argument('--humidity', type=float, default=None,
                            help='Humidity reading')
        parser.add_argument('--pressure', type=float, default=None,
                            help='Pressure reading')
        return parser

    def _receive_sensor_state(self, client, userdata, message):
        self.received_sensor_state = json.loads(message.payload.decode('utf-8'))

    def _print_sensor_state(self):
        if not self.received_sensor_state:
            print("No sensor state available.")
            return
        print("PM1.0: {pm1_0}, PM2.5: {pm2_5}, PM10: {pm10}, Temperature: {temperature}, Humidity: {humidity}, Pressure: {pressure}".format(
            **self.received_sensor_state
        ))

    def on_connect(self, client, userdata, flags, rc):
        client.message_callback_add(TOPIC_SENSOR_CHANGE_NOTIFICATION,
                                    self._receive_sensor_state)
        client.subscribe(TOPIC_SENSOR_CHANGE_NOTIFICATION, qos=1)

    def update_sensor_state(self):
        args = self.build_argument_parser().parse_args()

        # Update state with any provided sensor values
        if args.pm1_0 is not None:
            self.received_sensor_state['pm1_0'] = args.pm1_0
        if args.pm2_5 is not None:
            self.received_sensor_state['pm2_5'] = args.pm2_5
        if args.pm10 is not None:
            self.received_sensor_state['pm10'] = args.pm10
        if args.temperature is not None:
            self.received_sensor_state['temperature'] = args.temperature
        if args.humidity is not None:
            self.received_sensor_state['humidity'] = args.humidity
        if args.pressure is not None:
            self.received_sensor_state['pressure'] = args.pressure

        # Optionally indicate the source client for tracking
        self.received_sensor_state['client'] = MQTT_CLIENT_ID

        # Publish the updated sensor state
        self.client.publish(TOPIC_SET_SENSOR_DATA,
                            json.dumps(self.received_sensor_state).encode('utf-8'),
                            qos=1)
        # Allow time for the message to publish, then shut down the loop
        time.sleep(0.1)
        self.client.loop_stop()

    def _wait_for_sensor_state(self):
        # Wait up to 0.5 seconds (in 10 steps) for the initial sensor state
        for _ in range(10):
            if self.received_sensor_state:
                return
            self.client.loop(timeout=0.05)
        raise Exception("Timeout waiting for sensor state")

def main():
    aq_cmd = AirQualityCmd()
    if len(sys.argv) > 1:
        aq_cmd.update_sensor_state()
    else:
        aq_cmd._print_sensor_state()

if __name__ == '__main__':
    main()
