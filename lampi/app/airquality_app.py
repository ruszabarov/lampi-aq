import json
import pigpio

from kivy.app import App
from kivy.properties import NumericProperty, BooleanProperty, StringProperty
from kivy.clock import Clock
from kivy.uix.popup import Popup
from kivy.uix.label import Label
from paho.mqtt.client import Client
from kivy.uix.boxlayout import BoxLayout


from air_quality_common import *
import app.lampi_util

MQTT_CLIENT_ID = "lampi_ui"

class Card(BoxLayout):
    sensor_title = StringProperty("")
    sensor_reading = StringProperty("")
    
class AirQualityApp(App):
    # Define sensor properties
    pm25 = NumericProperty(0)      # for PM2.5 readings
    pm10 = NumericProperty(0)      # for PM10 readings
    temperature = NumericProperty(0)
    humidity = NumericProperty(0)
    pressure = NumericProperty(0)

    # Properties for device status and GPIO monitoring
    device_associated = BooleanProperty(True)
    gpio17_pressed = BooleanProperty(False)

    def on_start(self):
        self.mqtt_broker_bridged = False
        self._associated = True
        self.association_code = None
        self.mqtt = Client(client_id=MQTT_CLIENT_ID)
        self.mqtt.enable_logger()
        self.mqtt.will_set(client_state_topic(MQTT_CLIENT_ID), "0",
                           qos=2, retain=True)
        self.mqtt.on_connect = self.on_connect
        self.mqtt.connect(MQTT_BROKER_HOST, port=MQTT_BROKER_PORT,
                          keepalive=MQTT_BROKER_KEEP_ALIVE_SECS)
        self.mqtt.loop_start()

        # Set up GPIO and device status popup
        self.set_up_gpio_and_device_status_popup()
        self.associated_status_popup = self._build_associated_status_popup()
        self.associated_status_popup.bind(on_open=self.update_popup_associated)
        Clock.schedule_interval(self._poll_associated, 0.1)

    def _build_associated_status_popup(self):
        return Popup(
            title='Associate your Device',
            content=Label(text='Association message goes here', font_size='30sp'),
            size_hint=(1, 1),
            auto_dismiss=False
        )

    def on_connect(self, client, userdata, flags, rc):
        # Indicate that this UI client is online.
        self.mqtt.publish(client_state_topic(MQTT_CLIENT_ID), b"1",
                          qos=2, retain=True)
        # Subscribe to the sensor change notifications from the sensor publishing script.
        self.mqtt.message_callback_add(TOPIC_LAMPI_CHANGE_NOTIFICATION, self.receive_sensor_data)
        # Subscribe to the MQTT bridge connection status and association topics.
        self.mqtt.message_callback_add(broker_bridge_connection_topic(),
                                       self.receive_bridge_connection_status)
        self.mqtt.message_callback_add(TOPIC_LAMPI_ASSOCIATED,
                                       self.receive_associated)

        self.mqtt.subscribe(broker_bridge_connection_topic(), qos=1)
        self.mqtt.subscribe(TOPIC_LAMPI_CHANGE_NOTIFICATION, qos=1)
        self.mqtt.subscribe(TOPIC_LAMPI_ASSOCIATED, qos=2)

    def _poll_associated(self, dt):
        # Synchronize changes from MQTT callbacks (in a different thread) to the UI.
        self.device_associated = self._associated

    def receive_associated(self, client, userdata, message):
        # This callback is invoked when the association status changes.
        new_associated = json.loads(message.payload.decode('utf-8'))
        if self._associated != new_associated['associated']:
            if not new_associated['associated']:
                self.association_code = new_associated['code']
            else:
                self.association_code = None
            self._associated = new_associated['associated']

    def on_device_associated(self, instance, value):
        if value:
            self.associated_status_popup.dismiss()
        else:
            self.associated_status_popup.open()

    def update_popup_associated(self, instance):
        code = self.association_code[0:6] if self.association_code else "N/A"
        instance.content.text = (
            "Please use the\n"
            "following code\n"
            "to associate\n"
            "your device\n"
            f"on the Web\n{code}"
        )

    def receive_bridge_connection_status(self, client, userdata, message):
        # Update the MQTT bridge connection status
        self.mqtt_broker_bridged = (message.payload == b"1")

    def receive_sensor_data(self, client, userdata, message):
        # Process incoming sensor data.
        new_state = json.loads(message.payload.decode('utf-8'))
        Clock.schedule_once(lambda dt: self._update_ui(new_state), 0.01)

    def _update_ui(self, new_state):
        if 'pm25' in new_state:
            self.pm25 = new_state['pm25']
        if 'pm10' in new_state:
            self.pm10 = new_state['pm10']
        if 'temperature' in new_state:
            self.temperature = new_state['temperature']
        if 'humidity' in new_state:
            self.humidity = new_state['humidity']
        if 'pressure' in new_state:
            self.pressure = new_state['pressure']

    def set_up_gpio_and_device_status_popup(self):
        self.pi = pigpio.pi()
        # GPIO17 can be used as a hardware trigger for showing the network status.
        self.pi.set_mode(17, pigpio.INPUT)
        self.pi.set_pull_up_down(17, pigpio.PUD_UP)
        Clock.schedule_interval(self._poll_gpio, 0.05)
        self.network_status_popup = self._build_network_status_popup()
        self.network_status_popup.bind(on_open=self.update_popup_ip_address)

    def _build_network_status_popup(self):
        return Popup(
            title='Device Status',
            content=Label(text='IP ADDRESS WILL GO HERE'),
            size_hint=(1, 1),
            auto_dismiss=False
        )

    def update_popup_ip_address(self, instance):
        """Update the popup with the current IP address and device information."""
        interface = "wlan0"
        ipaddr = app.lampi_util.get_ip_address(interface)
        deviceid = app.lampi_util.get_device_id()
        msg = (
            f"Version: {''}\n"  # Insert version information if needed
            f"{interface}: {ipaddr}\n"
            f"DeviceID: {deviceid}\n"
            f"Broker Bridged: {self.mqtt_broker_bridged}"
        )
        instance.content.text = msg

    def on_gpio17_pressed(self, instance, value):
        """Open or dismiss the network status popup based on the button state."""
        if value:
            self.network_status_popup.open()
        else:
            self.network_status_popup.dismiss()

    def _poll_gpio(self, _delta_time):
        # GPIO17 is used as a hardware button.
        self.gpio17_pressed = not self.pi.read(17)


if __name__ == '__main__':
    AirQualityApp().run()
