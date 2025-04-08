import paho.mqtt.client

DEVICE_ID_FILENAME = '/sys/class/net/eth0/address'

# MQTT Topic Names for the Air Quality Monitor Service
TOPIC_SET_SENSOR_DATA = "air_quality_monitor/set_sensor_data"
TOPIC_SENSOR_CHANGE_NOTIFICATION = "air_quality_monitor/sensor_change_notification"
TOPIC_AIR_QUALITY_ASSOCIATED = "air_quality_monitor/associated"  # Optional, if needed

def get_device_id():
    with open(DEVICE_ID_FILENAME) as f:
        mac_addr = f.read().strip()
    return mac_addr.replace(':', '')

def client_state_topic(client_id):
    return 'air_quality_monitor/connection/{}/state'.format(client_id)

def broker_bridge_connection_topic():
    device_id = get_device_id()
    return '$SYS/broker/connection/{}_broker/state'.format(device_id)

# MQTT Broker Connection Info
MQTT_VERSION = paho.mqtt.client.MQTTv311
MQTT_BROKER_HOST = "localhost"
MQTT_BROKER_PORT = 1883
MQTT_BROKER_KEEP_ALIVE_SECS = 60
