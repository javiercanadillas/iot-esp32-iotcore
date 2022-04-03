# Copyright 2019 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
import machine
import esp32
from third_party import string
import network
import socket
import os
import utime
import ssl
from third_party import rsa
from umqtt.simple import MQTTClient
from ubinascii import b2a_base64
from machine import RTC, Pin
import ntptime
import ujson
import config

wlan = network.WLAN(network.STA_IF)
led_pin = machine.Pin(config.device_config['led_pin'], Pin.OUT, value=1)

def on_message(topic, message):
    print((topic,message))

def connect():
    """
    Establishes WLAN connectivity on boot
    """
    wlan.active(True)
    if not wlan.isconnected():
        print('connecting to network...')
        wlan.active(True)
        wlan.connect(config.wifi_config['ssid'], config.wifi_config['password'])
        while not wlan.isconnected():
            pass
    print(f'network config: {wlan.ifconfig()}')

def set_time():
    """
    Set local time in the MCU
    """
    ntptime.settime()
    tm = utime.localtime()
    tm = tm[0:3] + (0,) + tm[3:6] + (0,)
    machine.RTC().datetime(tm)
    print(f'current time: {utime.localtime()}')

def b42_urlsafe_encode(payload):
    """
    Encodes the URL in URL safe escape characters
    """
    # Translating the dashes and underscores in the payload
    return string.translate(b2a_base64(payload)[:-1].decode('utf-8'),{ ord('+'):'-', ord('/'):'_' })

def create_jwt(project_id, private_key, algorithm, token_ttl):
    """
    Creates and signs JWT token required by IoT Core 
    """
    print("Creating JWT...")
    private_key = rsa.PrivateKey(*private_key)

    # Epoch_offset is needed because micropython epoch is 2000-1-1 and unix is 1970-1-1. Adding 946684800 (30 years)
    epoch_offset = 946684800
    claims = {
            # The time that the token was issued at
            'iat': utime.time() + epoch_offset,
            # The time the token expires.
            'exp': utime.time() + epoch_offset + token_ttl,
            # The audience field should always be set to the GCP project id.
            'aud': project_id
    }

    #This only supports RS256 at this time.
    header = { "alg": algorithm, "typ": "JWT" }
    content = b42_urlsafe_encode(ujson.dumps(header).encode('utf-8'))
    content = content + '.' + b42_urlsafe_encode(ujson.dumps(claims).encode('utf-8'))
    signature = b42_urlsafe_encode(rsa.sign(content,private_key,'SHA-256'))
    return content+ '.' + signature #signed JWT

def get_mqtt_client(project_id, cloud_region, registry_id, device_id, jwt):
    """
    Create our MQTT client. The client_id is a unique string that identifies
    this device. For Google Cloud IoT Core, it must be in the format below.
    """
    client_id = f'projects/{project_id}/locations/{cloud_region}/registries/{registry_id}/devices/{device_id}'
    print(f'Sending message with password {jwt}')
    client = MQTTClient(
        client_id.encode('utf-8'),
        server=config.google_cloud_config['mqtt_bridge_hostname'],
        port=config.google_cloud_config['mqtt_bridge_port'],
        user=b'ignored',
        password=jwt.encode('utf-8'),
        ssl=True)
    client.set_callback(on_message)
    client.connect()
    client.subscribe(f'/devices/{device_id}/config', 1)
    client.subscribe(f'/devices/{device_id}/commands/#', 1)
    return client

# Connect to LAN network
connect()
# Need to be connected to the internet before setting the local RTC.
set_time()

jwt = create_jwt(
    config.google_cloud_config['project_id'],
    config.jwt_config['private_key'],
    config.jwt_config['algorithm'],
    config.jwt_config['token_ttl'])
client = get_mqtt_client(
    config.google_cloud_config['project_id'],
    config.google_cloud_config['cloud_region'],
    config.google_cloud_config['registry_id'],
    config.google_cloud_config['device_id'],
    jwt)

# Main loop
while True:
    message = {
        "device_id": config.google_cloud_config['device_id'],
        "temp": esp32.raw_temperature()
    }
    print("Publishing message "+str(ujson.dumps(message)))
    led_pin.value(1)
    mqtt_topic = f'/devices/{config.google_cloud_config["device_id"]}/events'
    client.publish(mqtt_topic.encode('utf-8'), ujson.dumps(message).encode('utf-8'))
    led_pin.value(0)

    client.check_msg() # Check for new messages on subscription
    utime.sleep(10)  # Delay for 10 seconds.