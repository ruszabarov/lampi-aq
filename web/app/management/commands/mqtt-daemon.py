import re
from paho.mqtt.client import Client
from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.conf import settings
from app.models import Lampi, SensorReading
import json


MQTT_BROKER_RE_PATTERN = (r'\$sys\/broker\/connection\/'
                          r'(?P<device_id>[0-9a-f]*)_broker/state')

SENSOR_DATA_TOPIC_PATTERN = 'devices/+/lampi/changed'

class Command(BaseCommand):
    help = 'Long-running Daemon Process to Integrate MQTT Messages with Django'

    def _create_default_user_if_needed(self):
        # make sure the user account exists that holds all new devices
        try:
            User.objects.get(username=settings.DEFAULT_USER)
        except User.DoesNotExist:
            print("Creating user {} to own new LAMPI devices".format(
                settings.DEFAULT_USER))
            new_user = User()
            new_user.username = settings.DEFAULT_USER
            new_user.password = '123456'
            new_user.is_active = False
            new_user.save()

    def _on_connect(self, client, userdata, flags, rc):
        self.client.message_callback_add('$SYS/broker/connection/+/state',
                                         self._device_broker_status_change)
        self.client.subscribe('$SYS/broker/connection/+/state')
        
        self.client.message_callback_add(SENSOR_DATA_TOPIC_PATTERN, self._handle_sensor_reading)
        self.client.subscribe(SENSOR_DATA_TOPIC_PATTERN)

    def _handle_sensor_reading(self, client, userdata, message):
        print(f"RECV: Sensor data on '{message.topic}': {message.payload}")
        
        device_id = message.topic.split('/')[1]
        
        try:
            payload = json.loads(message.payload.decode('utf-8'))
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            print(f"Error decoding payload: {e}")
            return
        
        try:
            lampi = Lampi.objects.get(device_id=device_id)
        except Lampi.DoesNotExist:
            print(f"No Lampi found with device ID {device_id}")
            return
        
        # Create a new SensorReading
        SensorReading.objects.create(
            pressure=payload.get('pressure'),
            temperature=payload.get('temperature'),
            humidity=payload.get('humidity'),
            altitude=payload.get('altitude'),
            pm25=payload.get('pm25'),
            pm10=payload.get('pm10'),
            lampi=lampi
        )
        print("Successfully created SensorReading")

    def _create_mqtt_client_and_loop_forever(self):
        self.client = Client()
        self.client.on_connect = self._on_connect
        self.client.connect('localhost', port=50001)
        self.client.loop_forever()

    def _device_broker_status_change(self, client, userdata, message):
        print("RECV: '{}' on '{}'".format(message.payload, message.topic))
        # message payload has to treated as type "bytes" in Python 3
        if message.payload == b'1':
            # broker connected
            results = re.search(MQTT_BROKER_RE_PATTERN, message.topic.lower())
            device_id = results.group('device_id')
            try:
                device = Lampi.objects.get(device_id=device_id)
                print("Found {}".format(device))
            except Lampi.DoesNotExist:
                # this is a new device - create new record for it
                new_device = Lampi(device_id=device_id)
                uname = settings.DEFAULT_USER
                new_device.user = User.objects.get(username=uname)
                new_device.save()
                print("Created {}".format(new_device))
                # send association MQTT message
                new_device.publish_unassociated_msg()

    def handle(self, *args, **options):
        self._create_default_user_if_needed()
        self._create_mqtt_client_and_loop_forever()
