# API Reference – RoomSense Backend

Base URL: `http://localhost:8000`

Quick test: `curl http://localhost:8000/status`

## REST Endpoints

### GET /status
Returns current sensor status.

```json
{
  "presence": true,
  "intensity": 42.5,
  "activity": "sitting",
  "breathing_rate": 14.2
}
```

Note: `breathing_rate` is `null` until ~32 seconds of data is collected (buffer filling).

### GET /history?limit=100
Returns last N events from SQLite (newest first).

```json
[
  {
    "id": 1,
    "timestamp": "2026-03-13T10:00:00.123456",
    "presence": 1,
    "intensity": 20.3,
    "activity": "sitting",
    "breathing_rate": 13.5
  }
]
```

Events are stored every ~5 seconds (every 10th CSI frame at 2Hz).

### POST /calibrate
Record calibration data for an activity label.

Request body:
```json
{
  "label": "sitting",
  "snapshots": [[10.2, 5.1, ...], [9.8, 4.9, ...]]
}
```

- `label`: one of `empty`, `still`, `sitting`, `walking`, `lying`
- `snapshots`: array of amplitude arrays (each 64 floats), collected by frontend over 30 seconds

Response:
```json
{
  "label": "sitting",
  "samples": 60,
  "threshold": 12.34
}
```

## WebSocket

### WS /ws
Streams live status at ~2Hz.

Each message is JSON:
```json
{
  "presence": true,
  "activity": "sitting",
  "intensity": 42.5,
  "breathing_rate": 14.2,
  "amplitudes": [10.2, 5.1, 8.7, ...]
}
```

`amplitudes` is an array of 64 floats (one per subcarrier).

Client must send periodic messages (e.g. "ping") to keep the connection alive:
```js
const ws = new WebSocket('ws://localhost:8000/ws')
ws.onopen = () => ws.send('ping')
ws.onmessage = (e) => {
  const data = JSON.parse(e.data)
  // data.presence, data.intensity, data.activity, data.breathing_rate, data.amplitudes
}
// Send ping every 5s
setInterval(() => ws.send('ping'), 5000)
```

## CORS

All origins allowed (`*`). No authentication in V1.
