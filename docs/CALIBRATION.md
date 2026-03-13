# Calibration Guide

Calibration teaches RoomSense your personal baseline.
It takes ~2.5 minutes total and must be done once after first setup.

## Why Calibration?

CSI signals vary by room size, furniture, wall materials and body type.
Without calibration, thresholds are generic and less accurate.
With calibration, the system learns YOUR specific environment.

## Steps

Open the app at http://localhost:3000/calibrate

### 1. Empty Room Baseline (30 seconds)
- Leave the room completely
- Click "empty" button
- Wait 30 seconds
- Come back

### 2. Still (30 seconds)
- Stand still near the board
- Click "still" button
- Don't move for 30 seconds

### 3. Sitting (30 seconds)
- Sit normally in front of the board
- Click "sitting" button
- Stay still for 30 seconds

### 4. Walking (30 seconds)
- Click "walking" button
- Walk normally around the room for 30 seconds

### 5. Lying (30 seconds)
- Lie down (on bed or floor near board)
- Click "lying" button
- Stay still for 30 seconds

## What Happens Technically

1. Frontend connects to WebSocket `/ws` and collects `amplitudes` arrays for 30 seconds
2. Collected snapshots (each 64 floats) are sent via `POST /calibrate` with the label
3. Backend computes:
   - **mean_amplitudes**: average amplitude per subcarrier
   - **std_amplitudes**: standard deviation per subcarrier
   - **threshold**: `mean(variance) + 2 * std(variance)` across all snapshots
4. Saved to SQLite `calibration` table
5. Loaded into memory on next startup (or immediately after recording)
6. Detector uses `empty` baseline to improve presence/intensity detection

## Re-calibration

Re-calibrate if you:
- Move the board to a different room
- Rearrange furniture significantly
- Add/remove a second person to the household

Just click the buttons again — new calibration overwrites old data.
