# ESP32-S3 Setup Guide

## Hardware

- **Board:** ESP32-S3 N16R8 (16MB Flash, 8MB PSRAM)
- **Connection:** USB-C (data cable, not charge-only)
- **Antenna:** Internal, 2.4GHz only

## Prerequisites (Mac)

```bash
# Install Homebrew if not already installed
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install dependencies
brew install cmake ninja dfu-util python3

# Install ESP-IDF
mkdir -p ~/esp
cd ~/esp
git clone --recursive https://github.com/espressif/esp-idf.git
cd esp-idf
git checkout v5.2
./install.sh esp32s3
source export.sh
```

## Flash ESP-CSI Firmware

```bash
# Clone ESP-CSI
cd ~/esp
git clone https://github.com/espressif/esp-csi.git
cd esp-csi/examples/console_test

# Copy config
cp main/config.h.example main/config.h
# Edit config.h: set WIFI_SSID and WIFI_PASSWORD

# Set target
idf.py set-target esp32s3

# Build and flash (board must be connected via USB-C)
idf.py flash monitor
```

## Enter Flash Mode (if board not detected)

1. Hold **BOOT** button
2. Press **RST** button briefly
3. Release **BOOT**
4. Run `idf.py flash` again

## Verify Output

In the serial monitor you should see CSI data lines like:
```
CSI_DATA,0,AA:BB:CC:DD:EE:FF,1,6,1,1,0,0,64,[10 12 -3 5 ...]
```

This means the board is working correctly.

## Connect to Backend

**Serial mode (USB, local dev):**
- Find port: `ls /dev/tty.usbmodem*` or `ls /dev/cu.*`
- Set in .env: `SERIAL_PORT=/dev/tty.usbmodem1234`
- Set: `INPUT_MODE=serial`

**UDP mode (WiFi, production):**
- Set in config.h: `UDP_SERVER_IP` = IP of your Mac/server
- Set in .env: `WIFI_UDP_PORT=5005`
- Set: `INPUT_MODE=udp`
