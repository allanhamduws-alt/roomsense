"""RoomSense Backend – FastAPI application."""

import asyncio
import json
import os
import serial
import socket
from contextlib import asynccontextmanager
from typing import AsyncGenerator, List, Optional, Set

import numpy as np
from dotenv import load_dotenv
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from calibration import baselines, get_empty_baseline, load_baselines, record_calibration
from csi_parser import parse_csi_string
from database import get_history, init_db, insert_event
from detector import analyze, reset_detector, set_calibration_thresholds

load_dotenv()

INPUT_MODE = os.getenv("INPUT_MODE", "udp")
SERIAL_PORT = os.getenv("SERIAL_PORT", "/dev/tty.usbmodem1234")
UDP_PORT = int(os.getenv("WIFI_UDP_PORT", "5005"))

# Shared state
latest_status: dict = {
    "presence": False,
    "activity": "empty",
    "intensity": 0.0,
    "breathing_rate": None,
    "amplitudes": [0.0] * 64,
}
connected_clients: Set[WebSocket] = set()
reader_task: Optional[asyncio.Task] = None


# --- Data reader loops ---

async def serial_reader():
    """Read CSI data from serial port using a background thread and queue."""
    try:
        ser = serial.Serial(SERIAL_PORT, 921600, timeout=1)
    except serial.SerialException as e:
        print(f"Serial error: {e}. Falling back to demo mode.")
        await demo_reader()
        return

    import threading
    import queue

    line_queue: queue.Queue = queue.Queue(maxsize=10)

    def _reader_thread():
        """Background thread that reads serial and puts latest CSI line in queue."""
        while True:
            try:
                line = ser.readline().decode("utf-8", errors="ignore").strip()
                if line and "CSI_DATA" in line:
                    # Drop old data, keep only latest
                    while not line_queue.empty():
                        try:
                            line_queue.get_nowait()
                        except queue.Empty:
                            break
                    line_queue.put(line)
            except Exception:
                break

    thread = threading.Thread(target=_reader_thread, daemon=True)
    thread.start()
    print("Serial reader thread started")

    while True:
        # Check queue for new data at ~2Hz
        await asyncio.sleep(0.5)
        try:
            line = line_queue.get_nowait()
            await process_csi_line(line)
        except queue.Empty:
            pass


async def udp_reader():
    """Read CSI data from UDP socket at full 100Hz, downsample for detection."""
    loop = asyncio.get_event_loop()
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(("0.0.0.0", UDP_PORT))
    sock.setblocking(False)

    # Process every Nth packet for detection (100Hz -> 10Hz)
    packet_count = 0
    PROCESS_EVERY = 10

    while True:
        try:
            data = await loop.sock_recv(sock, 4096)
            packet_count += 1
            if packet_count % PROCESS_EVERY == 0:
                line = data.decode("utf-8", errors="ignore").strip()
                if line:
                    await process_csi_line(line)
        except Exception:
            await asyncio.sleep(0.01)


async def demo_reader():
    """Generate synthetic CSI data for testing without hardware."""
    t = 0.0
    while True:
        # Simulate 64 subcarrier I/Q pairs
        iq_values = []
        for sc in range(64):
            # Base signal with some variation
            i_val = int(10 * np.sin(0.1 * t + sc * 0.3) + np.random.normal(0, 2))
            q_val = int(10 * np.cos(0.1 * t + sc * 0.3) + np.random.normal(0, 2))
            iq_values.extend([i_val, q_val])

        line = "CSI_DATA," + ",".join(str(v) for v in iq_values)
        await process_csi_line(line)
        t += 0.5
        await asyncio.sleep(0.5)  # ~2Hz


async def process_csi_line(line: str):
    """Parse CSI line, run detection, broadcast to clients."""
    global latest_status

    amplitudes = parse_csi_string(line)
    if amplitudes is None:
        return

    baseline = get_empty_baseline()
    result = analyze(amplitudes, baseline)
    latest_status = result

    # Store event periodically (every ~5 seconds to avoid flooding DB)
    if not hasattr(process_csi_line, "_counter"):
        process_csi_line._counter = 0
    process_csi_line._counter += 1
    if process_csi_line._counter % 10 == 0:
        await insert_event(
            presence=result["presence"],
            activity=result["activity"],
            intensity=result["intensity"],
            breathing_rate=result["breathing_rate"],
        )

    # WebSocket clients read from latest_status directly


# --- App lifecycle ---

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator:
    global reader_task

    await init_db()
    await load_baselines()
    set_calibration_thresholds(baselines)

    # Start the appropriate reader
    if INPUT_MODE == "serial":
        try:
            serial.Serial(SERIAL_PORT, 921600, timeout=0.1).close()
            reader_task = asyncio.create_task(serial_reader())
            print(f"Reading CSI from serial: {SERIAL_PORT}")
        except serial.SerialException:
            print(f"Serial port {SERIAL_PORT} not available. Starting demo mode.")
            reader_task = asyncio.create_task(demo_reader())
    elif INPUT_MODE == "udp":
        reader_task = asyncio.create_task(udp_reader())
        print(f"Reading CSI from UDP port: {UDP_PORT}")
    else:
        print("Unknown INPUT_MODE. Starting demo mode.")
        reader_task = asyncio.create_task(demo_reader())

    yield

    if reader_task:
        reader_task.cancel()
        try:
            await reader_task
        except asyncio.CancelledError:
            pass


app = FastAPI(title="RoomSense", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- API Routes ---

@app.get("/status")
async def get_status():
    """Current presence, activity, intensity, breathing rate."""
    return {
        "presence": latest_status["presence"],
        "activity": latest_status["activity"],
        "intensity": latest_status["intensity"],
        "breathing_rate": latest_status["breathing_rate"],
    }


@app.get("/debug")
async def debug_status():
    """Debug endpoint showing raw detector internals."""
    import time as _time
    from detector import (
        _frame_count, _baseline_collected, _motion_threshold,
        _turbulence_buffer, _mv_buffer, intensity_history,
        _last_motion_time, _recent_peak_mv, HOLD_SECONDS,
    )
    now = _time.time()
    hold_remaining = max(0, HOLD_SECONDS - (now - _last_motion_time)) if _last_motion_time > 0 else 0
    return {
        "frame_count": _frame_count,
        "calibrated": _baseline_collected,
        "motion_threshold": round(_motion_threshold, 6),
        "current_mv": round(_mv_buffer[-1], 6) if _mv_buffer else None,
        "recent_mv": [round(x, 6) for x in list(_mv_buffer)[-8:]],
        "peak_mv": round(_recent_peak_mv, 6),
        "hold_remaining_s": round(hold_remaining, 1),
        "intensity_history": [round(x, 1) for x in intensity_history],
        **latest_status,
    }


class CalibrationRequest(BaseModel):
    label: str
    snapshots: List[List[float]]


@app.post("/calibrate")
async def calibrate(req: CalibrationRequest):
    """Receive calibration label + CSI snapshots."""
    result = await record_calibration(req.label, req.snapshots)
    set_calibration_thresholds(baselines)
    return result


@app.post("/reset")
async def reset():
    """Reset detector for fresh auto-calibration.

    Call this when the room is EMPTY, then wait ~20s for recalibration.
    """
    reset_detector()
    return {"status": "ok", "message": "Detector reset. Auto-calibration starts now (~20s)."}


@app.get("/history")
async def history(limit: int = 100):
    """Last N events from SQLite."""
    events = await get_history(limit)
    return events


@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    """Stream live status at ~2Hz."""
    await ws.accept()
    try:
        while True:
            # Send latest status every 500ms
            data = json.dumps(latest_status, default=str)
            await ws.send_text(data)
            await asyncio.sleep(0.5)
    except WebSocketDisconnect:
        pass
    except Exception:
        pass
