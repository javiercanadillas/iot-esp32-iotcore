#!/bin/false
# Make shellcheck shut up about /bin/false
# shellcheck shell=bash disable=SC1008

# Set the latest Micropython ESP32 firmware URL
export MICROPYTHON_URL="https://micropython.org/resources/firmware/esp32-20220117-v1.18.bin"

# Enter here the right port, which is device-dependent
# Mac OS X example: /dev/cu.usbserial-02J1JMFH
SERIALPORT="/dev/$(ls /dev/ | grep -i "tty" | grep -i "usb")"
echo "Serial port var set to $SERIALPORT"
echo "If this is not correct, please edit the env.sh file and source it again."

# Exports different USB serial communication program startup options
export MINICOM="-D ${SERIALPORT}"
export ESPTOOL_PORT="${SERIALPORT}"
export AMPY_PORT="${SERIALPORT}"
export AMPYY_BAUD=115200
export RSHELL_PORT="${SERIALPORT}"

# Exports Cloud IoT Core configuration values
export IOT_REGION="europe-west1"
export IOT_REGISTRY="sw4iotreg"
export IOT_PUBSUB_TOPIC="sw4iotpub"
export IOT_PUBSUB_TOPIC_SUB="sw4iotsub"