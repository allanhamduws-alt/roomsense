# Calibration Guide

Calibration teaches RoomSense your personal baseline.
It takes ~2 minutes total and must be done once after first setup.

## Why Calibration?

CSI signals vary by room size, furniture, wall materials and body type.
Without calibration, thresholds are generic and less accurate.
With calibration, the system learns YOUR specific environment.

## Steps

Open the app at http://localhost:3000/calibrate

### 1. Empty Room Baseline (30 seconds)
- Leave the room completely
- Click "Start: Empty Room"
- Wait 30 seconds
- Come back

### 2. Still / Sitting (30 seconds)
- Sit normally in front of the board
- Click "Start: Sitting"
- Stay still for 30 seconds

### 3. Walking (30 seconds)
- Click "Start: Walking"
- Walk normally around the room for 30 seconds

### 4. Lying (30 seconds)
- Lie down (on bed or floor near board)
- Click "Start: Lying"
- Stay still for 30 seconds

## What Happens Technically

- Backend records ~100 CSI samples/second during each phase
- Computes mean and standard deviation of variance per subcarrier
- Stores thresholds in SQLite calibration table
- Detector uses these thresholds instead of generic defaults

## Re-calibration

Re-calibrate if you:
- Move the board to a different room
- Rearrange furniture significantly
- Add/remove a second person to the household
