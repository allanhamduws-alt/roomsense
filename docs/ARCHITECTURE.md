# Architecture – RoomSense

## Data Flow

```
ESP32-S3 (ESP-CSI firmware)
  │
  ├── USB Serial (local dev)
  └── WiFi UDP (production)
        │
        ▼
  FastAPI Backend (Python)
  ├── csi_parser.py     → raw string → amplitude[64]
  ├── detector.py       → amplitude → presence, intensity, activity, breathing
  ├── calibration.py    → baseline thresholds per activity
  ├── database.py       → SQLite, store events
  └── WebSocket /ws     → broadcast status at ~2Hz
        │
        ▼
  Next.js Frontend
  ├── WebSocket client  → receives live status
  ├── LiveCSIGraph      → 64 subcarrier amplitudes
  ├── PresenceCard      → YES / NO
  ├── ActivityCard      → still / sitting / walking / lying
  ├── BreathingCard     → breaths per minute
  └── IntensityMeter    → 0–100
```

## Detection Logic (V1, rule-based)

### Presence
- Compute variance across all 64 subcarrier amplitudes
- Compare to calibrated baseline (empty room)
- If variance > baseline + 2*std → presence = true

### Intensity
- Normalize variance to 0–100 scale based on calibration range

### Breathing Rate
- Use slow-varying subcarriers (select 10 most stable)
- Apply FFT on 30s sliding window
- Find dominant frequency in 0.1–0.5 Hz band (= 6–30 breaths/min)
- Only valid when intensity < 10 (person is still)

### Activity Status
- still: intensity < 5
- lying: intensity < 5 AND breathing rate valid AND time > 22:00 or < 08:00
- sitting: intensity 5–30
- walking: intensity > 30

## Deployment

- Local: `docker-compose up`
- Coolify: import repo, set env vars, deploy both services
- Serial mode: ESP32 connected via USB-C to server/Mac
- UDP mode: ESP32 on same WiFi network, sends UDP packets to backend IP
