# API Reference – RoomSense Backend

Base URL: `http://localhost:8000`

## REST Endpoints

### GET /status
Returns current sensor status.

```json
{
  "presence": true,
  "intensity": 42,
  "activity": "sitting",
  "breathing_rate": 14,
  "timestamp": "2026-03-13T11:00:00Z"
}
```

### GET /history?limit=100
Returns last N events from SQLite.

```json
[
  {
    "id": 1,
    "timestamp": "2026-03-13T10:00:00Z",
    "presence": true,
    "intensity": 20,
    "activity": "sitting",
    "breathing_rate": 13
  }
]
```

### POST /calibrate
Store calibration snapshot.

Request body:
```json
{
  "label": "sitting",
  "duration_seconds": 30
}
```

Response:
```json
{ "status": "ok", "samples_recorded": 3000 }
```

### GET /calibration/status
Returns which activity labels have been calibrated.

```json
{
  "calibrated": ["still", "sitting"],
  "missing": ["walking", "lying"]
}
```

## WebSocket

### WS /ws
Streams live status at ~2Hz.

Each message is JSON identical to GET /status.

Connect from frontend:
```js
const ws = new WebSocket('ws://localhost:8000/ws')
ws.onmessage = (e) => {
  const data = JSON.parse(e.data)
  // data.presence, data.intensity, data.activity, data.breathing_rate
}
```
