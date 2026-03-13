# RoomSense

WiFi CSI-based room sensing dashboard using ESP32-S3.
Detects presence, activity status, movement intensity and breathing rate — no camera, no wearable.

## Tech Stack

- **ESP32-S3 N16R8** – CSI data source (Espressif ESP-CSI firmware)
- **Python 3.11+ / FastAPI** – Backend, WebSocket, CSI parsing
- **SQLite** – Local history storage (swap to PostgreSQL for production)
- **Next.js 14 (App Router)** – Frontend dashboard
- **Docker + Docker Compose** – Deployment via Coolify

## Docs

- [Agent Roadmap](docs/AGENT_ROADMAP.md) – Build order and instructions for coding agents
- [Architecture](docs/ARCHITECTURE.md) – System overview
- [ESP32 Setup](docs/ESP32_SETUP.md) – Flash and configure the board
- [API Reference](docs/API.md) – Backend endpoints and WebSocket events
- [Calibration](docs/CALIBRATION.md) – How calibration works

## Quick Start

```bash
git clone https://github.com/allanhamduws-alt/roomsense
cd roomsense
cp .env.example .env
docker-compose up
```

Frontend: http://localhost:3000  
Backend: http://localhost:8000
