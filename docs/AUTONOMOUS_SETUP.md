# Autonomous ESP32 Setup Plan

This document is written for a Claude Code agent.
Execute all steps autonomously. Only pause when a manual action is explicitly required (marked with 🔴 MANUAL).

---

## Goal

Flash the ESP32-S3 N16R8 board with ESP-CSI firmware, connect it to the local WiFi,
verify CSI data output, and connect it to the running RoomSense backend.

---

## IMPORTANT: Known Gotchas (learned from first setup)

1. **Firmware-Beispiel:** Nutze `~/esp/esp-csi/examples/get-started/csi_recv_router` — NICHT `console_test` (existiert nicht mehr in neueren ESP-CSI Versionen)
2. **SSID genau prüfen:** Der User hat `FRITZ!Box` (mit `!`), nicht `FRITZ.Box` (mit `.`). Screenshot vom Mac-WLAN-Einstellungen prüfen!
3. **WiFi Auth:** FritzBox nutzt WPA2. Setze `CONFIG_EXAMPLE_WIFI_AUTH_WPA_WPA2_PSK=y` in `sdkconfig.defaults`
4. **Retries erhöhen:** `CONFIG_EXAMPLE_WIFI_CONN_MAX_RETRY=20` — der Standard (6) ist zu niedrig bei schwachem Signal
5. **sdkconfig löschen:** Nach Änderungen an `sdkconfig.defaults` muss die alte `sdkconfig` gelöscht werden (`rm -f sdkconfig`), dann `idf.py set-target` erneut ausführen
6. **Baud Rate:** Serial-Kommunikation läuft mit **921600** Baud, nicht 115200
7. **CSI Format:** IQ-Daten stehen in eckigen Klammern `"[i0,q0,i1,q1,...]"` am Ende der Zeile
8. **ESP-IDF source:** In bash-Subshell ausführen: `bash -c 'export IDF_PATH=... && . $IDF_PATH/export.sh && idf.py ...'`
9. **Backend ohne --reload starten:** `python3 -u -m uvicorn main:app --port 8000` (--reload kann Serial-Verbindung unterbrechen)
10. **Board Boot-Modus:** Wenn Port `/dev/cu.usbmodem101` nicht erscheint → User muss BOOT+RST drücken und macOS Popup "Verbinden" bestätigen

---

## Pre-Checks (run first, autonomously)

```bash
# Check if ESP-IDF already installed
ls ~/esp/esp-idf 2>/dev/null && echo 'ESP-IDF EXISTS' || echo 'NEEDS INSTALL'

# Check if ESP-CSI already cloned
ls ~/esp/esp-csi 2>/dev/null && echo 'ESP-CSI EXISTS' || echo 'NEEDS CLONE'

# Check if board is connected (look for usbmodem, NOT just Bluetooth)
ls /dev/cu.usbmodem* 2>/dev/null && echo 'BOARD FOUND' || echo 'BOARD NOT FOUND'

# Check if brew is installed
brew --version 2>/dev/null && echo 'BREW OK' || echo 'BREW MISSING'

# Check Python
python3 --version 2>/dev/null

# Check if .env exists in project
ls ~/Vibe/roomsense/.env 2>/dev/null && echo 'ENV EXISTS' || echo 'ENV MISSING'

# Check if backend is running
curl -s http://localhost:8000/status 2>/dev/null && echo 'BACKEND RUNNING' || echo 'BACKEND NOT RUNNING'

# Check if frontend is running
curl -s http://localhost:3000 >/dev/null 2>&1 && echo 'FRONTEND RUNNING' || echo 'FRONTEND NOT RUNNING'
```

Based on output: skip steps that are already done. Continue with what is missing.

---

## Step 1 – Install Dependencies (skip if already installed)

```bash
brew install cmake ninja dfu-util python3
```

---

## Step 2 – Install ESP-IDF (skip if ~/esp/esp-idf exists)

```bash
mkdir -p ~/esp
cd ~/esp
git clone --recursive https://github.com/espressif/esp-idf.git
cd esp-idf
git checkout v5.2
git submodule update --init --recursive --force
./install.sh esp32s3
```

Note: `./install.sh` can take 5–10 minutes. Wait for completion.

---

## Step 3 – Clone ESP-CSI (skip if ~/esp/esp-csi exists)

```bash
cd ~/esp
git clone https://github.com/espressif/esp-csi.git
```

---

## Step 4 – Configure WiFi Credentials

🔴 MANUAL: Ask user for WiFi SSID and Password. Verify SSID spelling carefully (e.g. `!` vs `.`).

Create `sdkconfig.defaults` with credentials:

```bash
cd ~/esp/esp-csi/examples/get-started/csi_recv_router

cat >> sdkconfig.defaults << 'EOF'

# WiFi Credentials
CONFIG_EXAMPLE_WIFI_SSID="EXACT_SSID_HERE"
CONFIG_EXAMPLE_WIFI_PASSWORD="PASSWORD_HERE"
CONFIG_EXAMPLE_CONNECT_WIFI=y
CONFIG_EXAMPLE_WIFI_AUTH_WPA_WPA2_PSK=y
CONFIG_EXAMPLE_WIFI_CONN_MAX_RETRY=20
CONFIG_EXAMPLE_WIFI_SCAN_METHOD_ALL_CHANNEL=y
CONFIG_ESP_WIFI_CSI_ENABLED=y
EOF
```

Then delete old config and reconfigure:
```bash
rm -f sdkconfig
```

---

## Step 5 – Set Target and Build

```bash
bash -c 'export IDF_PATH=~/esp/esp-idf && . $IDF_PATH/export.sh && \
  cd ~/esp/esp-csi/examples/get-started/csi_recv_router && \
  idf.py set-target esp32s3 && \
  idf.py build'
```

Build takes 2–5 minutes. Wait for `Project build complete` message.

Verify WiFi credentials are in the generated sdkconfig:
```bash
grep "WIFI_SSID\|WIFI_PASSWORD\|WIFI_AUTH" ~/esp/esp-csi/examples/get-started/csi_recv_router/sdkconfig
```

---

## Step 6 – Detect Board Port

```bash
ls /dev/cu.usbmodem* 2>/dev/null
```

🔴 MANUAL ACTION REQUIRED (only if board not found):
- Make sure USB-C cable is plugged into the board AND the Mac
- Use a DATA cable, not a charge-only cable
- Hold BOOT button, press RST, release BOOT
- Accept macOS "Allow Accessory" popup
- Run `ls /dev/cu.usbmodem*` again

Expected: `/dev/cu.usbmodem101` or similar.

---

## Step 7 – Flash Firmware

```bash
bash -c 'export IDF_PATH=~/esp/esp-idf && . $IDF_PATH/export.sh && \
  cd ~/esp/esp-csi/examples/get-started/csi_recv_router && \
  idf.py -p /dev/cu.usbmodem101 erase-flash && \
  idf.py -p /dev/cu.usbmodem101 flash'
```

Note: `erase-flash` first clears old NVS data (prevents stale WiFi configs).

If `Failed to connect` error: user must hold BOOT button during flash command.

---

## Step 8 – Verify CSI Output

```python
python3 -c "
import serial, time, re
ser = serial.Serial('/dev/cu.usbmodem101', 921600, timeout=1)
start = time.time()
csi_count = 0
while time.time() - start < 35:
    line = ser.readline().decode(errors='ignore').strip()
    if line:
        clean = re.sub(r'\x1b\[[0-9;]*m', '', line)
        if 'CSI_DATA' in clean:
            csi_count += 1
            if csi_count <= 3:
                print(clean[:150])
            if csi_count >= 5:
                break
        elif any(k in clean.lower() for k in ['connect', 'got ip', 'wifi:', 'reason']):
            print(clean)
ser.close()
print(f'CSI packets: {csi_count}')
print('SUCCESS' if csi_count > 0 else 'FAILED - check WiFi credentials')
"
```

If SUCCESS → continue. If FAILED:
- Check WiFi credentials (SSID spelling!)
- Check WiFi auth mode (WPA2 vs WPA3)
- Try `CONFIG_EXAMPLE_WIFI_AUTH_WPA2_WPA3_PSK=y` instead
- Rebuild and reflash

---

## Step 9 – Connect Board to RoomSense Backend

```bash
# Update .env in project
cd ~/Vibe/roomsense
sed -i '' 's|SERIAL_PORT=.*|SERIAL_PORT=/dev/cu.usbmodem101|' .env
sed -i '' 's|INPUT_MODE=.*|INPUT_MODE=serial|' .env
cat .env
```

---

## Step 10 – Start Backend and Verify Live Data

```bash
pkill -f uvicorn 2>/dev/null
sleep 1
cd ~/Vibe/roomsense/backend
python3 -u -m uvicorn main:app --port 8000 &
sleep 5
curl http://localhost:8000/status
```

Expected: JSON with real values (intensity > 0 if someone is in the room):
```json
{"presence": true, "activity": "sitting", "intensity": 19.7, "breathing_rate": null}
```

If intensity is always 0.0 and presence is always false:
- Check that Serial Baud in `main.py` is **921600** (not 115200)
- Check that `csi_parser.py` uses regex `\[([^\]]+)\]` to extract IQ data from brackets

Frontend should already be running at http://localhost:3000.
If not: `cd ~/Vibe/roomsense/frontend && npm run dev`

---

## Step 11 – Quick Smoke Test

1. Wave your hand in front of the board
2. Check dashboard at http://localhost:3000
3. `presence` should show `YES`
4. `intensity` should jump above 0
5. CSI graph lines should move

If all work → Setup complete ✅

---

## Troubleshooting

| Problem | Solution |
|---|---|
| Board not detected | Try different USB-C cable (must be data cable), accept macOS popup |
| Flash fails | Hold BOOT while running flash command |
| `waiting for download` in serial | Board stuck in boot mode — press RST once (without BOOT) |
| WiFi won't connect | Check SSID spelling (! vs .), check auth mode, increase retry count |
| No CSI data but WiFi connected | Wait 30s, router may be slow to respond |
| Backend intensity always 0 | Check Baud (921600) and CSI parser (bracket regex) |
| Backend not receiving data | Check SERIAL_PORT in .env matches actual port |
| Permission denied on port | `sudo chmod 666 /dev/cu.usbmodem*` |
| ESP-IDF command not found | Use bash subshell: `bash -c '. ~/esp/esp-idf/export.sh && idf.py ...'` |
| `--reload` breaks serial | Don't use `--reload` with serial input, use plain `uvicorn` |

---

## Success Criteria

- [x] Board detected on `/dev/cu.usbmodem101`
- [x] Firmware flashed without errors
- [x] CSI_DATA lines visible in serial monitor
- [x] Backend `/status` returns valid JSON with real values
- [x] Dashboard shows live CSI graph
- [x] Hand wave triggers presence detection
