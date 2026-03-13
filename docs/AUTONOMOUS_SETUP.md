# Autonomous ESP32 Setup Plan

This document is written for a Claude Code agent.
Execute all steps autonomously. Only pause when a manual action is explicitly required (marked with 🔴 MANUAL).

---

## Goal

Flash the ESP32-S3 N16R8 board with ESP-CSI firmware, connect it to the local WiFi,
verify CSI data output, and connect it to the running RoomSense backend.

---

## Pre-Checks (run first, autonomously)

```bash
# Check if ESP-IDF already installed
ls ~/esp/esp-idf 2>/dev/null && echo 'ESP-IDF EXISTS' || echo 'NEEDS INSTALL'

# Check if ESP-CSI already cloned
ls ~/esp/esp-csi 2>/dev/null && echo 'ESP-CSI EXISTS' || echo 'NEEDS CLONE'

# Check if board is connected
ls /dev/cu.* 2>/dev/null

# Check if brew is installed
brew --version 2>/dev/null && echo 'BREW OK' || echo 'BREW MISSING'

# Check Python
python3 --version 2>/dev/null

# Check if .env exists in project
ls ~/roomsense/.env 2>/dev/null && echo 'ENV EXISTS' || echo 'ENV MISSING'
```

Based on output: skip steps that are already done. Continue with what is missing.

---

## Step 1 – Install Dependencies (skip if already installed)

```bash
brew install cmake ninja dfu-util python3
```

If brew is missing:
```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

---

## Step 2 – Install ESP-IDF (skip if ~/esp/esp-idf exists)

```bash
mkdir -p ~/esp
cd ~/esp
git clone --recursive https://github.com/espressif/esp-idf.git
cd esp-idf
git checkout v5.2
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

```bash
# Source ESP-IDF environment
source ~/esp/esp-idf/export.sh

# Go to the console_test example
cd ~/esp/esp-csi/examples/console_test

# Open menuconfig to set WiFi SSID and Password
idf.py menuconfig
```

🔴 MANUAL ACTION REQUIRED:
In the menuconfig TUI that opens:
1. Navigate to: `Example Configuration`
2. Set `WiFi SSID` → enter the FritzBox WiFi name
3. Set `WiFi Password` → enter the FritzBox WiFi password
4. Press `S` to save, then `Q` to quit

After user confirms menuconfig is done, continue.

Alternative (if menuconfig is hard): create sdkconfig.defaults:
```bash
cat > sdkconfig.defaults << 'EOF'
CONFIG_EXAMPLE_WIFI_SSID="FRITZBOX_NAME_HERE"
CONFIG_EXAMPLE_WIFI_PASSWORD="FRITZBOX_PASSWORD_HERE"
EOF
```
🔴 MANUAL: Ask user for WiFi SSID and Password, fill in above, then continue.

---

## Step 5 – Set Target and Build

```bash
source ~/esp/esp-idf/export.sh
cd ~/esp/esp-csi/examples/console_test
idf.py set-target esp32s3
idf.py build
```

Build takes 2–5 minutes. Wait for `Project build complete` message.

---

## Step 6 – Detect Board Port

```bash
ls /dev/cu.* 
```

🔴 MANUAL ACTION REQUIRED (only if board not found):
- Make sure USB-C cable is plugged into the board AND the Mac
- Use a DATA cable, not a charge-only cable
- If still not found: hold BOOT button, press RST, release BOOT
- Run `ls /dev/cu.*` again

Expected output example: `/dev/cu.usbmodem1234` or `/dev/cu.SLAB_USBtoUART`

Save the port name for next steps.

---

## Step 7 – Flash Firmware

```bash
source ~/esp/esp-idf/export.sh
cd ~/esp/esp-csi/examples/console_test

# Replace PORT with actual port from Step 6
idf.py -p PORT flash
```

If error `Failed to connect`:
```bash
# Try with manual boot mode
# 1. Hold BOOT button on board
# 2. Run the flash command
# 3. Release BOOT when upload starts
idf.py -p PORT flash
```

---

## Step 8 – Verify CSI Output

```bash
source ~/esp/esp-idf/export.sh
cd ~/esp/esp-csi/examples/console_test
idf.py -p PORT monitor
```

Wait 10–15 seconds for WiFi connection.

Expected output (success):
```
I (1234) wifi: connected to AP
CSI_DATA,0,AA:BB:CC:DD:EE:FF,1,6,1,1,0,0,64,[10 12 -3 5 ...]
CSI_DATA,0,AA:BB:CC:DD:EE:FF,1,6,1,1,0,0,64,[11 10 -2 6 ...]
```

If you see `CSI_DATA` lines → SUCCESS ✅
If you only see boot logs but no CSI → wait 30s more, router may be slow
If WiFi fails → repeat Step 4 with correct credentials

Press Ctrl+] to exit monitor.

---

## Step 9 – Connect Board to RoomSense Backend

```bash
# Find exact port
PORT=$(ls /dev/cu.usbmodem* 2>/dev/null || ls /dev/cu.SLAB* 2>/dev/null | head -1)
echo "Board port: $PORT"

# Update .env in roomsense project
cd ~/roomsense  # or wherever the project is cloned

# Check current .env
cat .env

# Update SERIAL_PORT and INPUT_MODE
sed -i '' 's|INPUT_MODE=.*|INPUT_MODE=serial|' .env
sed -i '' "s|SERIAL_PORT=.*|SERIAL_PORT=$PORT|" .env

# Verify
cat .env
```

---

## Step 10 – Restart Backend and Verify Live Data

```bash
# If running with docker-compose
cd ~/roomsense
docker-compose restart backend

# If running locally with Python
# Kill existing backend process and restart
pkill -f uvicorn
cd ~/roomsense/backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8000 &
```

Wait 5 seconds, then check:
```bash
curl http://localhost:8000/status
```

Expected response:
```json
{"presence": false, "intensity": 0, "activity": "still", "breathing_rate": null}
```

If you get a valid JSON response → backend is running ✅

Open browser: http://localhost:3000
The CSI graph should now show live data (non-zero values, moving lines).

---

## Step 11 – Quick Smoke Test

1. Wave your hand in front of the board
2. Check dashboard at http://localhost:3000
3. `presence` should flip to `YES`
4. `intensity` should jump above 0
5. CSI graph lines should move

If all 3 work → Setup complete ✅

---

## Troubleshooting

| Problem | Solution |
|---|---|
| Board not detected | Try different USB-C cable (must be data cable) |
| Flash fails | Hold BOOT while running `idf.py flash` |
| No CSI data | Check WiFi credentials in menuconfig |
| Backend not receiving data | Check SERIAL_PORT in .env matches actual port |
| Permission denied on port | `sudo chmod 666 /dev/cu.usbmodem*` |
| ESP-IDF command not found | Run `source ~/esp/esp-idf/export.sh` first |

---

## Success Criteria

- [ ] Board detected on `/dev/cu.*`
- [ ] Firmware flashed without errors
- [ ] CSI_DATA lines visible in serial monitor
- [ ] Backend `/status` returns valid JSON
- [ ] Dashboard shows live CSI graph
- [ ] Hand wave triggers presence detection
