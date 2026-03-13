# RoomSense

WiFi CSI-based room sensing dashboard using ESP32-S3.
Detects presence, activity status, movement intensity and breathing rate — no camera, no wearable.

## Tech Stack

- **ESP32-S3 N16R8** – CSI data source (Espressif ESP-CSI firmware)
- **Python 3.9+ / FastAPI** – Backend, WebSocket, CSI parsing
- **SQLite** – Local history storage
- **Next.js 14 (App Router)** – Frontend dashboard with Tailwind CSS (dark theme)
- **Recharts** – Real-time charts
- **Docker + Docker Compose** – Deployment (Coolify-compatible)

## Status (V1 – Implementiert)

- [x] Backend: FastAPI mit Serial/UDP/Demo Reader, CSI Parser, Detector, Calibration
- [x] Frontend: Dashboard, Calibrate, History Seiten
- [x] Docker: Backend + Frontend Dockerfiles, docker-compose.yml
- [x] Demo-Modus: Synthetische CSI-Daten wenn kein ESP32 angeschlossen

## Docs

- [Agent Roadmap](docs/AGENT_ROADMAP.md) – Build order and instructions for coding agents
- [Architecture](docs/ARCHITECTURE.md) – System overview
- [ESP32 Setup](docs/ESP32_SETUP.md) – Flash and configure the board
- [API Reference](docs/API.md) – Backend endpoints and WebSocket events
- [Calibration](docs/CALIBRATION.md) – How calibration works

## Quick Start (Lokal ohne Docker)

```bash
# Terminal 1 – Backend
cd backend && pip install -r requirements.txt
cp ../.env.example ../.env
python3 -m uvicorn main:app --host 0.0.0.0 --port 8000

# Terminal 2 – Frontend
cd frontend && npm install
npm run dev
```

Frontend: http://localhost:3000
Backend: http://localhost:8000

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
│   ├── main.py              # FastAPI App, Reader-Loops, WebSocket
│   ├── csi_parser.py         # Raw CSI String → Amplitude Array (64)
│   ├── detector.py            # Presence, Intensity, Breathing, Activity
│   ├── calibration.py         # Baseline Recording + Threshold Berechnung
│   └── database.py            # SQLite (events + calibration Tabellen)
├── frontend/
│   ├── Dockerfile
│   ├── package.json
│   ├── next.config.js         # standalone output
│   ├── tailwind.config.ts
│   ├── app/
│   │   ├── layout.tsx         # Nav + Dark Theme
│   │   ├── globals.css
│   │   ├── page.tsx           # Dashboard (WebSocket → alle Karten)
│   │   ├── calibrate/page.tsx # 30s Recording pro Label
│   │   └── history/page.tsx   # Charts + Tabelle
│   └── components/
│       ├── LiveCSIGraph.tsx    # 64 Subcarrier Liniendiagramm
│       ├── PresenceCard.tsx    # YES/NO mit Farbe
│       ├── ActivityCard.tsx    # Icon + Label
│       ├── BreathingCard.tsx   # BPM + Trend-Sparkline
│       └── IntensityMeter.tsx  # Fortschrittsbalken 0–100
├── esp32/
│   └── config.h.example
├── docker-compose.yml
├── .env.example
└── docs/
```

## Hinweise für Agents

- Python 3.9 auf dem System (macOS) → alle Type-Hints verwenden `Optional[X]`, `List[X]`, `Dict[X]` aus `typing`
- Backend startet automatisch im Demo-Modus wenn kein ESP32/Serial verfügbar
- Frontend nutzt `NEXT_PUBLIC_BACKEND_URL` env var (default: http://localhost:8000)
- Docker-Dockerfile für Frontend nutzt `output: "standalone"` in next.config.js
