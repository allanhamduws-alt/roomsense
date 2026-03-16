# RoomSense

WiFi CSI-based room sensing dashboard using ESP32-S3.
Detects presence, activity status, movement intensity and breathing rate — no camera, no wearable.

## Tech Stack

- **ESP32-S3 N16R8** – CSI data source (Espressif ESP-CSI `csi_recv_router` firmware)
- **Python 3.9+ / FastAPI** – Backend, WebSocket, CSI parsing
- **SQLite** – Local history storage
- **Next.js 14 (App Router)** – Frontend dashboard with Tailwind CSS (dark theme)
- **Recharts** – Real-time charts
- **Docker + Docker Compose** – Deployment (Coolify-compatible)

## Current State (V1 – Live & Working)

- [x] ESP32-S3 geflasht mit `csi_recv_router` Firmware (ESP-IDF v5.2, UDP-Output)
- [x] Board verbunden mit FritzBox via WPA2 (2.4 GHz) — läuft kabellos, nur Strom nötig
- [x] Backend empfängt CSI per UDP Broadcast (Port 5005), Serial als Fallback
- [x] CSI-Parser extrahiert IQ-Daten aus `"[...]"` Bracket-Format
- [x] Detector liefert Presence, Activity, Intensity, Breathing Rate (V1.1: temporal variance + auto-baseline)
- [x] Vital Monitor: Pulsierendes Herz-SVG mit geschätztem Puls via WiFi-Sensing (Demo-Feature)
- [x] Frontend zeigt Live-Dashboard mit WebSocket-Updates
- [x] Demo-Modus wenn kein ESP32 angeschlossen

## Quick Start (Lokal ohne Docker)

```bash
# Terminal 1 – Backend
cd backend && pip install -r requirements.txt
cp ../.env.example ../.env  # dann SERIAL_PORT anpassen
python3 -u -m uvicorn main:app --port 8000

# Terminal 2 – Frontend
cd frontend && npm install
npm run dev
```

- Frontend: http://localhost:3000
- Backend: http://localhost:8000
- Status-Check: `curl http://localhost:8000/status`

## Quick Start (Docker)

```bash
cp .env.example .env
docker-compose up
```

## Projektstruktur

```
roomsense/
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── main.py              # FastAPI App, UDP/Serial Reader, WebSocket broadcast
│   ├── csi_parser.py         # Raw CSI → Amplitude[64] (regex auf "[i,q,...]" Brackets)
│   ├── detector.py           # Presence, Intensity, Breathing (FFT), Activity
│   ├── calibration.py        # Baseline Recording + Threshold Berechnung
│   └── database.py           # SQLite (events + calibration Tabellen)
├── frontend/
│   ├── Dockerfile
│   ├── package.json
│   ├── next.config.js        # standalone output
│   ├── tailwind.config.ts
│   ├── app/
│   │   ├── layout.tsx        # Nav + Dark Theme
│   │   ├── globals.css
│   │   ├── page.tsx          # Dashboard (WebSocket → alle Karten)
│   │   ├── calibrate/page.tsx # 30s Recording pro Label
│   │   └── history/page.tsx  # Charts + Tabelle
│   └── components/
│       ├── LiveCSIGraph.tsx   # 64 Subcarrier Liniendiagramm
│       ├── PresenceCard.tsx   # YES/NO mit Farbe
│       ├── ActivityCard.tsx   # Icon + Label
│       ├── BreathingCard.tsx  # BPM + Trend-Sparkline
│       ├── BreathingVisualizer.tsx # Pulsierendes Herz-SVG (geschätzter Puls)
│       └── IntensityMeter.tsx # Fortschrittsbalken 0–100
├── docker-compose.yml
├── .env.example
├── .gitignore
└── docs/
    ├── AGENT_ROADMAP.md      # Build-Reihenfolge für Coding-Agents
    ├── ARCHITECTURE.md       # System-Architektur + Detection-Logik
    ├── API.md                # REST + WebSocket Referenz
    ├── CALIBRATION.md        # Kalibrierungs-Anleitung
    ├── ESP32_SETUP.md        # Board Flash + Konfiguration
    └── AUTONOMOUS_SETUP.md   # Agent-gesteuertes Setup (Schritt-für-Schritt)
```

## Hinweise für Agents

- **Projekt-Root:** `/Users/allanha/Vibe/roomsense`
- **ESP-IDF:** `~/esp/esp-idf` (v5.2), ESP-CSI: `~/esp/esp-csi`
- **Firmware-Beispiel:** `~/esp/esp-csi/examples/get-started/csi_recv_router` (NICHT `console_test`)
- **Transport:** UDP Broadcast auf Port 5005 (Standard), Serial 921600 Baud (Fallback)
- **Board läuft kabellos** — nur Strom nötig, verbindet sich automatisch mit WLAN
- **CSI-Datenformat:** `CSI_DATA,...,"[i0,q0,i1,q1,...]"` — IQ-Werte in eckigen Klammern
- **Detector V1.1:** Temporal Variance + Auto-Baseline + Smoothing + Hysteresis (NICHT `np.var(amplitudes)` pro Frame)
- Python 3.9 auf dem System → Type-Hints: `Optional[X]`, `List[X]`, `Dict[X]` aus `typing`
- Backend startet automatisch im Demo-Modus wenn keine UDP-Daten/kein Serial verfügbar
- Frontend nutzt `NEXT_PUBLIC_BACKEND_URL` env var (default: http://localhost:8000)
- Backend starten: `python3 -u -m uvicorn main:app --port 8000`
</content>
</invoke>