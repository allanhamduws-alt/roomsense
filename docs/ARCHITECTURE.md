# Architecture – RoomSense

## Data Flow

```
ESP32-S3 (ESP-CSI firmware)
  │
  ├── USB Serial (local dev)
  └── WiFi UDP (production)
        │
        ▼
  FastAPI Backend (Python 3.9+)
  ├── main.py             → Serial/UDP/Demo reader loop, FastAPI app, WebSocket broadcast
  ├── csi_parser.py       → raw CSI string → amplitude[64] (I/Q pairs → magnitude)
  ├── detector.py         → amplitude → presence, intensity, activity, breathing
  ├── calibration.py      → baseline thresholds per activity label
  ├── database.py         → SQLite (aiosqlite), events + calibration tables
  └── WebSocket /ws       → broadcast status at ~2Hz to all connected clients
        │
        ▼
  Next.js 14 Frontend (Tailwind CSS, Dark Theme)
  ├── WebSocket client    → receives live status JSON
  ├── LiveCSIGraph        → 64 subcarrier amplitudes (Recharts LineChart)
  ├── PresenceCard        → YES / NO with color indicator
  ├── ActivityCard        → icon + label: empty/still/sitting/walking/lying
  ├── BreathingCard       → BPM number + sparkline trend
  └── IntensityMeter      → animated progress bar 0–100
```

## Input Modes

Configured via `INPUT_MODE` env var:
- `serial` – reads from USB serial port (default). Falls back to demo mode if port unavailable.
- `udp` – listens on `WIFI_UDP_PORT` for UDP packets from ESP32.
- Any other value → demo mode with synthetic data.

## Demo Mode

Automatically activated when:
- `INPUT_MODE=serial` but serial port is not available
- No ESP32 hardware connected

Generates synthetic CSI data (sine waves + noise) at ~2Hz for testing the full pipeline.

## Detection Logic (V1, rule-based)

### Presence
- Compute variance across all 64 subcarrier amplitudes
- If calibrated: compare against empty-room baseline
- Threshold: variance > 5.0 (default) or calibrated threshold

### Intensity (0–100)
- Normalized variance score
- Max variance for normalization: 50.0

### Breathing Rate
- Rolling buffer of 64 samples (~32 seconds at 2Hz)
- FFT on mean amplitude time series
- Extract dominant frequency in 0.1–0.5 Hz band (= 6–30 BPM)
- Only reported if signal-to-noise ratio > 2x median
- Returns `null` until buffer is full

### Activity Classification
- `empty`: no presence detected
- `lying`: presence + intensity < 5 + low variance stability
- `still`: presence + intensity < 5
- `sitting`: presence + intensity 5–25
- `walking`: presence + intensity > 25

## Database Schema (SQLite)

### events
| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER PK | Auto-increment |
| timestamp | TEXT | ISO 8601 |
| presence | INTEGER | 0 or 1 |
| activity | TEXT | empty/still/sitting/walking/lying |
| intensity | REAL | 0.0–100.0 |
| breathing_rate | REAL | BPM or NULL |

### calibration
| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER PK | Auto-increment |
| label | TEXT | Activity label |
| mean_amplitudes | TEXT | JSON array of 64 floats |
| std_amplitudes | TEXT | JSON array of 64 floats |
| threshold | REAL | Computed threshold |
| created_at | TEXT | ISO 8601 |

Events are inserted every ~5 seconds (every 10th CSI frame).

## Deployment

- **Local dev**: Two terminals – uvicorn + npm run dev
- **Docker**: `docker-compose up` (backend port 8000, frontend port 3000)
- **Coolify**: Import repo, set env vars, ports via `BACKEND_PORT`/`FRONTEND_PORT`
- Serial mode: ESP32 connected via USB-C to server/Mac
- UDP mode: ESP32 on same WiFi network, sends UDP packets to backend IP

## Key Dependencies

### Backend
- fastapi 0.111, uvicorn 0.30, numpy 1.26, aiosqlite 0.20, pyserial 3.5, python-dotenv

### Frontend
- next 14.2, react 18.3, recharts 2.12, lucide-react, tailwindcss 3.4
