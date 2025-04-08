import paho.mqtt.client

DEVICE_ID_FILENAME = '/sys/class/net/eth0/address'

TOPIC_SET_SENSOR_DATA = "lampi/set_sensor_data"
TOPIC_LAMPI_CHANGE_NOTIFICATION = "lampi/changed"
TOPIC_LAMPI_ASSOCIATED = "lampi/associated"

def get_device_id():
    with open(DEVICE_ID_FILENAME) as f:
        mac_addr = f.read().strip()
    return mac_addr.replace(':', '')

def client_state_topic(client_id):
    return 'lampi/connection/{}/state'.format(client_id)

def broker_bridge_connection_topic():
    device_id = get_device_id()
    return '$SYS/broker/connection/{}_broker/state'.format(device_id)

# MQTT Broker Connection Info
MQTT_VERSION = paho.mqtt.client.MQTTv311
MQTT_BROKER_HOST = "localhost"
MQTT_BROKER_PORT = 1883
MQTT_BROKER_KEEP_ALIVE_SECS = 60
