# Architecture – RoomSense

## Data Flow

```
ESP32-S3 N16R8 (ESP-CSI csi_recv_router firmware)
  │ UDP Broadcast @ 255.255.255.255:5005 (WiFi, kabellos)
  │ Board IP: 192.168.178.79 (DHCP via FritzBox)
  │ CSI rate: ~100Hz from router pings
  │ Fallback: USB-C Serial @ 921600 Baud (INPUT_MODE=serial)
  │
  ▼
FastAPI Backend (Python 3.9+, uvicorn port 8000)
  ├── main.py             → UDP listener (Standard) oder Thread-based serial reader
  │                         Throttled to ~2Hz, WebSocket push every 500ms
  ├── csi_parser.py       → regex extracts IQ values from "[...]" brackets → amplitude[64]
  ├── detector.py         → amplitude → presence, intensity, activity, breathing (FFT)
  ├── calibration.py      → baseline thresholds per activity label (stored in SQLite)
  ├── database.py         → SQLite (aiosqlite), events + calibration tables
  ├── GET /status         → current detection state (JSON)
  ├── POST /calibrate     → receive 30s of amplitude snapshots for a label
  ├── GET /history        → last N events from SQLite
  └── WS /ws              → push latest_status at ~2Hz to each connected client
        │
        ▼
Next.js 14 Frontend (Tailwind CSS, Dark Theme, port 3000)
  ├── WebSocket client    → receives live status JSON at ~2Hz
  ├── LiveCSIGraph        → 64 subcarrier amplitudes (Recharts LineChart)
  ├── PresenceCard        → YES / NO with color indicator
  ├── ActivityCard        → icon + label: empty/still/sitting/walking/lying
  ├── BreathingCard       → BPM number + sparkline trend
  ├── BreathingVisualizer → Pulsierendes Herz-SVG mit geschätztem Puls (breathing_rate × 4.2)
  └── IntensityMeter      → animated progress bar 0–100
```

## ESP32-S3 Firmware

- **Beispiel:** `~/esp/esp-csi/examples/get-started/csi_recv_router`
- **NICHT** `console_test` (existiert in neueren ESP-CSI Versionen nicht mehr)
- Board verbindet sich per WiFi (STA-Modus) zum Router und pingt das Gateway (~100Hz)
- **CSI-Output: UDP Broadcast** an `255.255.255.255:5005` (konfigurierbar via `CONFIG_UDP_TARGET_IP` / `CONFIG_UDP_TARGET_PORT` in `app_main.c`)
- Board braucht **nur Strom** (USB-Netzteil reicht) — keine USB-Datenverbindung zum Mac nötig
- WiFi-Credentials sind in die Firmware eingebrannt (`sdkconfig.defaults`)
- Board verbindet sich automatisch beim Hochfahren mit dem WLAN
- Relevante Kconfig-Optionen:
  ```
  CONFIG_EXAMPLE_WIFI_SSID="FRITZ!Box 7530 YB"
  CONFIG_EXAMPLE_WIFI_PASSWORD="..."
  CONFIG_EXAMPLE_WIFI_AUTH_WPA_WPA2_PSK=y
  CONFIG_EXAMPLE_WIFI_CONN_MAX_RETRY=20
  CONFIG_EXAMPLE_WIFI_SCAN_METHOD_ALL_CHANNEL=y
  CONFIG_ESP_WIFI_CSI_ENABLED=y
  ```

## CSI Data Format (UDP / Serial Output)

```
CSI_DATA,<id>,<MAC>,<rssi>,<rate>,<sig_mode>,<mcs>,<bandwidth>,<smoothing>,
<not_sounding>,<aggregation>,<stbc>,<fec_coding>,<sgi>,<noise_floor>,
<ampdu_cnt>,<channel>,<secondary_channel>,<timestamp>,<ant>,<sig_len>,
<rx_state>,<len>,<first_word>,"[i0,q0,i1,q1,...,i63,q63]"
```

- IQ-Werte in **eckigen Klammern** `"[...]"` am Ende der Zeile
- 128 Werte = 64 Subcarrier x 2 (I + Q)
- Parser: `re.search(r'\[([^\]]+)\]', data)`

## Serial Reader Architecture (IMPORTANT)

Das serielle Lesen war das schwierigste Problem. Key Learnings:

1. **run_in_executor blockiert WebSocket:** Der naive Ansatz (`await loop.run_in_executor(None, readline)`) blockiert den asyncio Event-Loop bei 100Hz Datenrate. WebSocket-Broadcasts kommen nie durch.

2. **Starlette WebSocket Limitation:** Concurrent send/receive auf dem gleichen WebSocket aus verschiedenen Tasks funktioniert nicht. Ein globaler `broadcast()` aus dem Reader-Task kann nicht senden während der WS-Handler auf `receive_text()` wartet.

3. **Funktionierende Lösung:**
   - **Daemon-Thread** liest Serial in einer Endlosschleife und legt die neueste CSI-Zeile in eine `queue.Queue` (alte Daten werden verworfen)
   - **Async-Loop** prüft die Queue alle 500ms und ruft `process_csi_line()` auf
   - **WebSocket-Handler** hat einen eigenen Push-Loop: liest `latest_status` direkt und sendet alle 500ms

```python
# Thread liest Serial → Queue (neueste Zeile)
# Async task liest Queue → process_csi_line → latest_status
# WS handler liest latest_status → send_text (je Client eigener Loop)
```

## Input Modes

Via `INPUT_MODE` env var in `.env`:
- `udp` – **Standard seit V1.1.** UDP-Pakete vom ESP32 auf Port 5005 (Broadcast). Board läuft kabellos.
- `serial` – USB Serial Port (Fallback/Debug). Fällt auf Demo-Modus zurück wenn Port nicht da.
- Sonstiges → Demo-Modus mit synthetischen Daten.

## Detection Logic (V1.1, rule-based, temporal variance)

**WICHTIG:** V1.0 hatte einen fundamentalen Bug: `np.var(amplitudes)` berechnete die Varianz
der 64 Subcarrier-Werte *innerhalb eines Frames* — das ist der natürliche Spread der Frequenzen
und war immer hoch (→ Intensity 100, Walking). V1.1 nutzt stattdessen **zeitliche Varianz**
(Frame-zu-Frame-Änderungen), was tatsächliche Bewegung misst.

### Presence
- **Temporal Variance**: Mittlere absolute Frame-zu-Frame-Differenz über letzte 6 Frames (~3s)
- **Deviation from Baseline**: Abweichung vom Auto-Baseline oder kalibrierten Baseline
- Combined Score: `temporal * 0.7 + deviation * 0.3`
- Threshold: 2.0 (Standard), Majority-Vote über letzte Readings
- Auto-Baseline: Erste ~10 Sekunden werden als Referenz gespeichert

### Intensity (0–100)
- Gleicher Combined Score wie Presence, normalisiert mit `INTENSITY_SCALE = 20.0`
- Smoothed über 6-Sample-Window (~3s)

### Breathing Rate
- Rolling Buffer 64 Samples (~32s bei 2Hz)
- FFT auf Mean-Amplitude, 0.1–0.5 Hz Band (6–30 BPM)
- SNR-Threshold: Peak > 2.5x Median (erhöht von 2.0x gegen Fehldetektionen)
- Sanity Check: nur 6–30 BPM werden akzeptiert

### Activity Classification
- `empty`: keine Presence
- `lying`: Presence + Intensity < 8 + niedrige Varianz-Stabilität (std < 1.0)
- `still`: Presence + Intensity < 8
- `sitting`: Presence + Intensity 8–30
- `walking`: Presence + Intensity > 30

### Auto-Baseline (NEU in V1.1)
- Erste 20 Frames (~10 Sekunden) werden akkumuliert und gemittelt
- Dient als Referenz wenn keine Kalibrierung vorhanden
- Empfehlung: Raum sollte in den ersten 10s möglichst ruhig sein
- Kalibrierung via `/calibrate` überschreibt Auto-Baseline

## Database Schema (SQLite)

### events
| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER PK | Auto-increment |
| timestamp | TEXT | ISO 8601 |
| presence | INTEGER | 0 oder 1 |
| activity | TEXT | empty/still/sitting/walking/lying |
| intensity | REAL | 0.0–100.0 |
| breathing_rate | REAL | BPM oder NULL |

### calibration
| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER PK | Auto-increment |
| label | TEXT | Activity-Label |
| mean_amplitudes | TEXT | JSON Array von 64 Floats |
| std_amplitudes | TEXT | JSON Array von 64 Floats |
| threshold | REAL | Berechneter Schwellenwert |
| created_at | TEXT | ISO 8601 |

## Known Issues / TODOs

- **Kalibrierung "Empty" wurde mit Person im Raum gemacht** — muss wiederholt werden mit leerem Raum
- **Demo-Reader CSI Format** passt nicht zum echten Bracket-Format — `demo_reader()` muss angepasst werden wenn getestet
- **`connected_clients` Set wird noch importiert aber nicht mehr benutzt** — kann aufgeräumt werden
- **Raumwechsel erfordert Neukalibrierung** — jeder Raum hat ein anderes CSI-Profil (Möbel, Wände, Abstände). Auto-Baseline hilft, aber Kalibrierung ist für beste Ergebnisse nötig
- **Puls-Schätzung ist Approximation** — `breathing_rate × 4.2` ist physiologisch plausibel für Ruhepuls, aber nicht medizinisch genau

## Changelog

### V1.1 (2026-03-13)
- **FIX:** Detection von Frame-Varianz auf zeitliche Varianz umgestellt (behebt Intensity=100 Bug)
- **NEU:** Auto-Baseline (erste 10s als Referenz, kein Kalibrieren nötig für Grundfunktion)
- **NEU:** Temporal Smoothing (6-Frame-Window ~3s) + Hysteresis (4 konsistente Readings für Zustandswechsel)
- **NEU:** Kalibrierungs-Thresholds werden jetzt für Activity-Klassifikation genutzt (nicht mehr nur empty)
- **NEU:** UDP-Output in Firmware — Board sendet CSI per WiFi-Broadcast statt Serial
- **NEU:** Board läuft kabellos — nur Strom nötig, kein USB zum Mac
- **NEU:** BreathingVisualizer — pulsierendes Herz-SVG mit geschätztem Puls via WiFi-Sensing
- **FIX:** Breathing Rate SNR-Threshold erhöht (2.5x) + Sanity-Check 6–30 BPM

## Key Dependencies

### Backend
- fastapi, uvicorn, numpy, aiosqlite, pyserial, python-dotenv

### Frontend
- next 14, react 18, recharts, lucide-react, tailwindcss

## Deployment

- **Lokal:** `python3 -u -m uvicorn main:app --port 8000` (KEIN --reload bei Serial!)
- **Frontend:** `cd frontend && npm run dev`
- **Docker:** `docker-compose up`
