# Agent Roadmap – RoomSense

This file is the single source of truth for any coding agent building this project.
Read this first. Build in order. Do not skip steps.

---

## Project Goal

Build a local + cloud-deployable web app that reads WiFi CSI data from an ESP32-S3 board
and displays real-time presence, activity, movement intensity and breathing rate in a dashboard.

---

## Build Status

| Step | Description | Status |
|------|------------|--------|
| Step 1 | Repository Structure | DONE |
| Step 2 | Backend (FastAPI) | DONE |
| Step 3 | Frontend (Next.js 14) | DONE |
| Step 4 | Docker Setup | DONE |
| Step 5 | ESP32 Docs | DONE (docs/ESP32_SETUP.md + esp32/config.h.example) |

**All V1 steps are complete.** The app is runnable locally and via Docker.

---

## Build Order

### Step 1 – Repository Structure

Create the following folder structure:

```
roomsense/
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── main.py
│   ├── csi_parser.py
│   ├── detector.py
│   ├── calibration.py
│   └── database.py
├── frontend/
│   ├── Dockerfile
│   ├── package.json
│   └── app/
│       ├── page.tsx
│       ├── history/page.tsx
│       └── calibrate/page.tsx
│   └── components/
│       ├── LiveCSIGraph.tsx
│       ├── PresenceCard.tsx
│       ├── ActivityCard.tsx
│       ├── BreathingCard.tsx
│       └── IntensityMeter.tsx
├── esp32/
│   ├── README.md
│   └── config.h.example
├── docker-compose.yml
├── .env.example
└── README.md
```

---

### Step 2 – Backend (FastAPI)

Build in this order:

1. `database.py` – SQLite setup, tables: `events` (timestamp, presence, activity, intensity, breathing_rate)
2. `csi_parser.py` – Parse raw CSI string from ESP32 serial/UDP into amplitude array (64 subcarriers)
3. `detector.py` – Feature extraction from amplitude array:
   - Presence: variance threshold on subcarrier amplitudes
   - Intensity: normalized variance score 0–100
   - Breathing rate: FFT on slow-varying subcarriers (0.1–0.5 Hz band)
   - Activity: rule-based on intensity + variance pattern (still/sitting/walking/lying)
4. `calibration.py` – Store baseline CSI snapshots per activity label, compute thresholds
5. `main.py` – FastAPI app:
   - `GET /status` – current presence, activity, intensity, breathing
   - `POST /calibrate` – receive label + CSI snapshot
   - `GET /history` – last N events from SQLite
   - `WebSocket /ws` – stream live status at ~2Hz
   - Serial/UDP reader loop that feeds csi_parser → detector → broadcast

---

### Step 3 – Frontend (Next.js 14)

Build in this order:

1. `components/LiveCSIGraph.tsx` – Real-time line chart of 64 subcarrier amplitudes using Recharts or Chart.js
2. `components/PresenceCard.tsx` – Large YES/NO indicator with color (green/red)
3. `components/IntensityMeter.tsx` – Animated progress bar 0–100
4. `components/ActivityCard.tsx` – Icon + label: still / sitting / walking / lying
5. `components/BreathingCard.tsx` – BPM number + small trend graph
6. `app/page.tsx` – Main dashboard, WebSocket connection, renders all components
7. `app/calibrate/page.tsx` – Calibration UI: buttons for each activity label, sends to backend
8. `app/history/page.tsx` – Chart of presence/activity over time from /history endpoint

Use **Tailwind CSS** for styling. Dark theme preferred.
Use **shadcn/ui** for cards and UI components.

---

### Step 4 – Docker Setup

1. `backend/Dockerfile` – Python 3.11 slim, install requirements, run uvicorn on port 8000
2. `frontend/Dockerfile` – Node 20 alpine, build Next.js, serve on port 3000
3. `docker-compose.yml` – Two services: backend + frontend, shared network, env_file .env
4. `.env.example` – Variables: `SERIAL_PORT`, `WIFI_UDP_PORT`, `DATABASE_URL`

Must be Coolify-compatible: no hardcoded ports, use environment variables.

---

### Step 5 – ESP32 Docs

`esp32/README.md` – Complete flash instructions for Mac:
1. Install ESP-IDF (brew + idf.py)
2. Clone https://github.com/espressif/esp-csi
3. Set target: `idf.py set-target esp32s3`
4. Configure WiFi credentials in config.h
5. Flash: `idf.py flash monitor`
6. Verify CSI output in serial monitor
7. Point backend SERIAL_PORT to the device

`esp32/config.h.example` – Template with WIFI_SSID, WIFI_PASSWORD, UDP_SERVER_IP, UDP_PORT

---

## Important Constraints

- **No external APIs or cloud services** – everything runs locally or on own server
- **No authentication for V1** – keep it simple
- **SQLite for V1** – do not use PostgreSQL yet
- **Serial OR UDP** – backend should support both input modes via env var `INPUT_MODE=serial|udp`
- **No ML training required** – use rule-based thresholds + FFT only for V1
- **Calibration is simple** – record 30s baseline per activity, compute mean/std, store in SQLite
- **ESP32-S3 N16R8 specific** – 64 subcarriers, 2.4GHz, 1x1 MIMO
- **Do not over-engineer** – V1 must be runnable in one `docker-compose up`
- **Python 3.9 compatibility** – use `typing.Optional`, `typing.List`, `typing.Dict` instead of `X | None`, `list[x]`, `dict[x]`

---

## Implementation Notes

- Backend falls back to **demo mode** (synthetic CSI data) when no ESP32 is connected
- Frontend uses `NEXT_PUBLIC_BACKEND_URL` env var (default: `http://localhost:8000`)
- WebSocket clients must send periodic messages ("ping") to keep connection alive
- Events are written to DB every ~5 seconds (every 10th frame) to avoid flooding
- Breathing rate returns `null` until ~32 seconds of data buffer is filled
- Next.js uses `output: "standalone"` for Docker deployment

---

## V2 / Future (do not build now)

- Multi-room support (multiple ESP32 nodes)
- Person identification (WhoFi-style)
- Sleep report (nightly summary)
- LLM daily briefing
- PostgreSQL migration
- Authentication
