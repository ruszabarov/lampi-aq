#!/usr/bin/env python3
import time
import json
import serial
import board
from adafruit_bme280 import basic as adafruit_bme280
import paho.mqtt.client as mqtt

from air_quality_common import (
    TOPIC_SET_SENSOR_DATA,
    MQTT_BROKER_HOST,
    MQTT_BROKER_PORT,
    MQTT_BROKER_KEEP_ALIVE_SECS,
    MQTT_VERSION
)

MQTT_CLIENT_ID = "sensor_reader"

class RealSensorReader:
    def __init__(self,
                 serial_port: str = '/dev/ttyUSB0',
                 i2c_address: int = 0x76,
                 sea_level_pressure: float = 1013.25):
        # Serial port for PM sensor
        self.ser = serial.Serial(serial_port, timeout=1)
        # I²C BME280 for T/H/P/Altitude
        i2c = board.I2C()  # uses board.SCL + board.SDA
        self.bme280 = adafruit_bme280.Adafruit_BME280_I2C(i2c, address=i2c_address)
        self.bme280.sea_level_pressure = sea_level_pressure

    def read_all(self) -> dict:
        # Read the BME280
        temperature = round(self.bme280.temperature, 2)
        humidity    = round(self.bme280.relative_humidity, 2)
        pressure    = round(self.bme280.pressure, 2)
        altitude    = round(self.bme280.altitude, 2)

        # Read 10 bytes from the PM sensor
        buf = self.ser.read(10)
        # bytes 2–3 little-endian → PM2.5, bytes 4–5 → PM10
        pm25 = int.from_bytes(buf[2:4], byteorder='little') / 10
        pm10 = int.from_bytes(buf[4:6], byteorder='little') / 10

        return {
            "temperature": temperature,
            "humidity":    humidity,
            "pressure":    pressure,
            "altitude":    altitude,
            "pm25":        round(pm25, 2),
            "pm10":        round(pm10, 2),
            "client":      MQTT_CLIENT_ID
        }

def on_connect(client, userdata, flags, rc):
    print("Connected to MQTT broker, result code =", rc)

def main():
    # MQTT setup
    client = mqtt.Client(client_id=MQTT_CLIENT_ID, protocol=MQTT_VERSION)
    client.on_connect = on_connect
    client.enable_logger()
    client.connect(MQTT_BROKER_HOST, MQTT_BROKER_PORT, MQTT_BROKER_KEEP_ALIVE_SECS)
    client.loop_start()

    sensor = RealSensorReader()

    try:
        while True:
            data = sensor.read_all()
            payload = json.dumps(data).encode('utf-8')
            client.publish(TOPIC_SET_SENSOR_DATA, payload, qos=1)
            print("Published:", data)
            time.sleep(1)
    except KeyboardInterrupt:
        print("Shutting down...")
    finally:
        client.loop_stop()

if __name__ == '__main__':
    main()
