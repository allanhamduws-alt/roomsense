# ESP32-S3 Setup Guide

## Hardware

- **Board:** ESP32-S3 N16R8 (16MB Flash, 8MB PSRAM)
- **Connection:** USB-C (data cable, not charge-only!)
- **Antenna:** Internal PCB antenna, 2.4GHz only
- **Board Port (Mac):** `/dev/cu.usbmodem101` (kann variieren)

## Firmware: csi_recv_router

Wir nutzen das `csi_recv_router` Beispiel aus ESP-CSI (modifiziert für UDP). Dieses Beispiel:
- Verbindet sich als WiFi STA mit dem Router
- Pingt das Gateway periodisch (100 Hz)
- Extrahiert CSI aus den Router-Antworten
- **Sendet CSI-Daten per UDP Broadcast** an `255.255.255.255:5005`
- Board braucht **nur Strom** (USB-Netzteil reicht) — kein USB-Kabel zum Mac nötig
- WiFi-Credentials sind in die Firmware eingebrannt, Board verbindet sich automatisch

**Pfad:** `~/esp/esp-csi/examples/get-started/csi_recv_router`

> **Hinweis:** `console_test` existiert in neueren ESP-CSI Versionen nicht mehr. Immer `csi_recv_router` verwenden.

## Prerequisites (Mac)

```bash
brew install cmake ninja dfu-util python3

# ESP-IDF v5.2
mkdir -p ~/esp && cd ~/esp
git clone --recursive https://github.com/espressif/esp-idf.git
cd esp-idf && git checkout v5.2
git submodule update --init --recursive --force
./install.sh esp32s3
```

## WiFi Konfiguration

WiFi-Credentials werden über `sdkconfig.defaults` gesetzt (nicht menuconfig):

```bash
cd ~/esp/esp-csi/examples/get-started/csi_recv_router

# Am Ende der Datei hinzufügen:
cat >> sdkconfig.defaults << 'EOF'

CONFIG_EXAMPLE_WIFI_SSID="DEINE_SSID"
CONFIG_EXAMPLE_WIFI_PASSWORD="DEIN_PASSWORT"
CONFIG_EXAMPLE_CONNECT_WIFI=y
CONFIG_EXAMPLE_WIFI_AUTH_WPA_WPA2_PSK=y
CONFIG_EXAMPLE_WIFI_CONN_MAX_RETRY=20
CONFIG_EXAMPLE_WIFI_SCAN_METHOD_ALL_CHANNEL=y
CONFIG_ESP_WIFI_CSI_ENABLED=y
EOF
```

**Wichtig:**
- SSID exakt wie im Router/Mac angezeigt (auf `!` vs `.` achten!)
- Nach Änderungen: `rm -f sdkconfig` und Target neu setzen
- Auth-Modus passend zum Router wählen (FritzBox: `WPA_WPA2_PSK`)

## Build und Flash

```bash
bash -c 'export IDF_PATH=~/esp/esp-idf && . $IDF_PATH/export.sh && \
  cd ~/esp/esp-csi/examples/get-started/csi_recv_router && \
  rm -f sdkconfig && \
  idf.py set-target esp32s3 && \
  idf.py build && \
  idf.py -p /dev/cu.usbmodem101 erase-flash && \
  idf.py -p /dev/cu.usbmodem101 flash'
```

## Board in Flash-Modus bringen

Wenn das Board nicht erkannt wird oder `/dev/cu.usbmodem*` fehlt:

1. Halte **BOOT** Button
2. Drücke kurz **RST** Button
3. Lasse **BOOT** los
4. macOS Popup "Zubehör verbinden" → **Erlauben** klicken
5. Board sollte als `/dev/cu.usbmodem101` erscheinen

Nach dem Flash: **RST** einmal drücken (ohne BOOT) um normal zu booten.

## UDP Output prüfen

Board an beliebiges USB-Netzteil anschließen (oder USB-C am Mac). Nach ~3-5 Sekunden sendet es CSI per WiFi:

```python
python3 -c "
import socket
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
sock.bind(('0.0.0.0', 5005))
sock.settimeout(8)
try:
    data, addr = sock.recvfrom(4096)
    print(f'FROM: {addr}')
    print(f'DATA: {data[:200].decode(errors=\"ignore\")}')
except socket.timeout:
    print('TIMEOUT - Board sendet nicht (WLAN-Verbindung prüfen)')
finally:
    sock.close()
"
```

Erwartete Ausgabe:
```
FROM: ('192.168.178.79', ...)
DATA: CSI_DATA,12345,60:b5:8d:9a:44:df,-75,11,1,5,...,128,0,"[0,0,6,11,6,10,...]"
```

## Serial Output prüfen (Fallback / Debug)

Nur nötig wenn Board per USB angeschlossen ist:

```python
python3 -c "
import serial
ser = serial.Serial('/dev/cu.usbmodem101', 921600, timeout=1)
for i in range(10):
    line = ser.readline().decode(errors='ignore').strip()
    if line: print(line[:150])
ser.close()
"
```

## CSI Data Format

```
CSI_DATA,<id>,<MAC>,<rssi>,<rate>,<sig_mode>,<mcs>,<bandwidth>,<smoothing>,
<not_sounding>,<aggregation>,<stbc>,<fec_coding>,<sgi>,<noise_floor>,
<ampdu_cnt>,<channel>,<sec_channel>,<timestamp>,<ant>,<sig_len>,
<rx_state>,<len>,<first_word>,"[i0,q0,i1,q1,...,i63,q63]"
```

- 128 IQ-Werte in eckigen Klammern = 64 Subcarrier × (I + Q)
- Amplitude pro Subcarrier: `sqrt(I² + Q²)`

## Backend verbinden

In `~/Vibe/roomsense/.env`:
```
INPUT_MODE=udp
WIFI_UDP_PORT=5005
```

Für Serial-Fallback (USB-Kabel):
```
INPUT_MODE=serial
SERIAL_PORT=/dev/cu.usbmodem101
```

Backend starten:
```bash
cd ~/Vibe/roomsense/backend
python3 -u -m uvicorn main:app --port 8000
```

Prüfen: `curl http://localhost:8000/status`

## Aktuelle Hardware-Konfiguration

| Parameter | Wert |
|-----------|------|
| Board | ESP32-S3 N16R8 |
| ESP-IDF | v5.2 |
| Firmware | csi_recv_router (modifiziert, UDP) |
| WiFi | FRITZ!Box 7530 YB (2.4 GHz, Kanal 11) |
| Auth | WPA/WPA2 PSK |
| Board IP | 192.168.178.79 (DHCP) |
| CSI Output | UDP Broadcast 255.255.255.255:5005 |
| Serial Port | /dev/cu.usbmodem101 (nur Flashing) |
| Baud Rate | 921600 |
| Subcarriers | 64 (128 IQ-Werte) |
| CSI Sample Rate | ~100 Hz (ping frequency) |
| Betrieb | Kabellos — nur USB-Netzteil für Strom |
