# Agent Roadmap – RoomSense

This file is the single source of truth for any coding agent building this project.
Read this first. Then read ARCHITECTURE.md for technical details.

---

## Project Goal

Local + cloud-deployable web app that reads WiFi CSI data from an ESP32-S3 board
and displays real-time presence, activity, movement intensity and breathing rate in a dashboard.

---

## Current State: V1 COMPLETE + HARDWARE LIVE

| Component | Status | Notes |
|-----------|--------|-------|
| ESP32-S3 Firmware | ✅ DONE | `csi_recv_router`, UDP broadcast to 255.255.255.255:5005 |
| Backend (FastAPI) | ✅ DONE | UDP listener, CSI parser, detector (V1.1 temporal), calibration |
| Frontend (Next.js) | ✅ DONE | Dashboard, calibrate, history pages |
| Docker Setup | ✅ DONE | docker-compose.yml, Dockerfiles |
| UDP Integration | ✅ DONE | Board sendet kabellos per WiFi, kein USB nötig |
| Serial Integration | ✅ DONE | 921600 Baud, bracket-format IQ parser (Fallback) |
| Live Data Flow | ✅ DONE | ESP32 → UDP/WiFi → Backend → WebSocket → Frontend |

---

## Environment Info

| Item | Path / Value |
|------|-------------|
| Project Root | `/Users/allanha/Vibe/roomsense` |
| ESP-IDF | `~/esp/esp-idf` (v5.2) |
| ESP-CSI | `~/esp/esp-csi` |
| Firmware Example | `~/esp/esp-csi/examples/get-started/csi_recv_router` |
| Board Port | `/dev/cu.usbmodem101` (nur für Flashing) |
| Board IP | `192.168.178.79` (DHCP, kann variieren) |
| UDP Port | `5005` (CSI Broadcast) |
| Backend URL | `http://localhost:8000` |
| Frontend URL | `http://localhost:3000` |
| Python | 3.9+ (system), 3.14 (brew) |
| Node | via npm in `frontend/` |

---

## Critical Implementation Details

### CSI Data Format
The ESP32-S3 `csi_recv_router` outputs lines like:
```
CSI_DATA,55533,60:b5:8d:9a:44:df,-76,11,1,4,...,128,0,"[0,0,-5,7,...]"
```
- IQ values are inside **square brackets** `"[...]"` at the end
- 128 values = 64 subcarriers × 2 (I, Q)
- Parser uses: `re.search(r'\[([^\]]+)\]', data)`

### Data Transport (UDP – Standard)
- Firmware sendet CSI per **UDP Broadcast** an `255.255.255.255:5005`
- Backend lauscht auf `0.0.0.0:5005` (non-blocking async socket)
- Board braucht nur Strom (USB-Netzteil), kein USB-Kabel zum Mac
- Board verbindet sich automatisch mit WLAN beim Hochfahren
- Konfigurierbar in Firmware: `CONFIG_UDP_TARGET_IP`, `CONFIG_UDP_TARGET_PORT`

### Serial Communication (Fallback)
- Baud rate: **921600** (not 115200!)
- Port: `/dev/cu.usbmodem101`
- Backend reads via daemon thread + queue pattern
- Don't use `--reload` flag with serial (breaks connection)
- Nur zum Flashen oder Debugging nötig

### WiFi Configuration (ESP32)
- Credentials in `sdkconfig.defaults`, NOT menuconfig
- Must delete `sdkconfig` after changing defaults: `rm -f sdkconfig`
- Auth mode: `CONFIG_EXAMPLE_WIFI_AUTH_WPA_WPA2_PSK=y` for FritzBox
- Retry count: `CONFIG_EXAMPLE_WIFI_CONN_MAX_RETRY=20`

### ESP-IDF Commands
Always run in bash subshell:
```bash
bash -c 'export IDF_PATH=~/esp/esp-idf && . $IDF_PATH/export.sh && idf.py ...'
```

---

## Build Order (for new agent starting from scratch)

### Step 1 – Repository Structure
See README.md for full tree.

### Step 2 – Backend (FastAPI)
Build in this order:
1. `database.py` – SQLite setup, tables: events + calibration
2. `csi_parser.py` – Parse CSI bracket format `"[i,q,i,q,...]"` → amplitude[64]
3. `detector.py` – Temporal-variance presence, intensity, FFT breathing, rule-based activity, auto-baseline
4. `calibration.py` – Baseline recording + threshold computation
5. `main.py` – FastAPI app with UDP/serial reader, WebSocket broadcast, REST endpoints

### Step 3 – Frontend (Next.js 14)
Build in this order:
1. `components/LiveCSIGraph.tsx` – 64 subcarrier Recharts LineChart
2. `components/PresenceCard.tsx` – YES/NO with green/red
3. `components/IntensityMeter.tsx` – Progress bar 0–100
4. `components/ActivityCard.tsx` – Icon + label
5. `components/BreathingCard.tsx` – BPM + sparkline
6. `components/BreathingVisualizer.tsx` – Pulsierendes Herz-SVG mit geschätztem Puls (Demo-Wow-Feature)
7. `app/page.tsx` – Dashboard with WebSocket connection (includes BreathingVisualizer)
7. `app/calibrate/page.tsx` – 30s recording per label
8. `app/history/page.tsx` – Chart from /history endpoint

### Step 4 – Docker Setup
- `backend/Dockerfile` – Python 3.11, uvicorn on 8000
- `frontend/Dockerfile` – Node 20, Next.js standalone on 3000
- `docker-compose.yml` – Two services, env_file .env

### Step 5 – ESP32 Flash
See `docs/AUTONOMOUS_SETUP.md` for agent-executable steps.

---

## Important Constraints

- **No external APIs or cloud services** – everything runs locally or on own server
- **No authentication for V1**
- **SQLite for V1** – no PostgreSQL yet
- **UDP (Standard) oder Serial (Fallback)** – via `INPUT_MODE` env var
- **No ML** – rule-based thresholds + FFT only for V1
- **Detector nutzt zeitliche Varianz** – NICHT `np.var(amplitudes)` pro Frame (das war der V1.0 Bug). Stattdessen Frame-zu-Frame-Differenzen + Auto-Baseline
- **Raumwechsel** – Auto-Baseline hilft, aber Neukalibrierung empfohlen für beste Ergebnisse
- **Python 3.9 compatibility** – use `typing.Optional`, `typing.List`, `typing.Dict`
- **ESP32-S3 specific** – 64 subcarriers, 2.4GHz only

---

## V2 / Future (do not build now)

- Multi-room support (multiple ESP32 nodes)
- Person identification (WhoFi-style)
- Sleep report (nightly summary)
- LLM daily briefing
- PostgreSQL migration
- Authentication
- ML-based activity classification (replace rule-based)
