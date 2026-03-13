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

from calibration import get_empty_baseline, load_baselines, record_calibration
from csi_parser import parse_csi_string
from database import get_history, init_db, insert_event
from detector import analyze

load_dotenv()

INPUT_MODE = os.getenv("INPUT_MODE", "serial")
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
    """Read CSI data from serial port in a background thread."""
    loop = asyncio.get_event_loop()

    def _read_serial():
        try:
            ser = serial.Serial(SERIAL_PORT, 115200, timeout=1)
            while True:
                line = ser.readline().decode("utf-8", errors="ignore").strip()
                if line:
                    yield line
        except serial.SerialException as e:
            print(f"Serial error: {e}. Running in demo mode.")
            yield from _demo_generator()

    for line in await loop.run_in_executor(None, lambda: list(_read_lines_serial())):
        await process_csi_line(line)


def _read_lines_serial():
    """Generator that yields serial lines."""
    try:
        ser = serial.Serial(SERIAL_PORT, 115200, timeout=1)
        while True:
            line = ser.readline().decode("utf-8", errors="ignore").strip()
            if line:
                yield line
    except serial.SerialException:
        yield from []


async def udp_reader():
    """Read CSI data from UDP socket."""
    loop = asyncio.get_event_loop()
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("0.0.0.0", UDP_PORT))
    sock.setblocking(False)

    while True:
        try:
            data = await loop.sock_recv(sock, 4096)
            line = data.decode("utf-8", errors="ignore").strip()
            if line:
                await process_csi_line(line)
        except Exception:
            await asyncio.sleep(0.1)


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

    # Broadcast to WebSocket clients
    await broadcast(result)


async def broadcast(data: dict):
    """Send data to all connected WebSocket clients."""
    if not connected_clients:
        return
    message = json.dumps(data, default=str)
    disconnected = set()
    for ws in connected_clients:
        try:
            await ws.send_text(message)
        except Exception:
            disconnected.add(ws)
    connected_clients -= disconnected


# --- App lifecycle ---

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator:
    global reader_task

    await init_db()
    await load_baselines()

    # Start the appropriate reader
    if INPUT_MODE == "serial":
        try:
            serial.Serial(SERIAL_PORT, 115200, timeout=0.1).close()
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


class CalibrationRequest(BaseModel):
    label: str
    snapshots: List[List[float]]


@app.post("/calibrate")
async def calibrate(req: CalibrationRequest):
    """Receive calibration label + CSI snapshots."""
    result = await record_calibration(req.label, req.snapshots)
    return result


@app.get("/history")
async def history(limit: int = 100):
    """Last N events from SQLite."""
    events = await get_history(limit)
    return events


@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    """Stream live status at ~2Hz."""
    await ws.accept()
    connected_clients.add(ws)
    try:
        while True:
            # Keep connection alive, wait for client messages (ping/pong)
            await ws.receive_text()
    except WebSocketDisconnect:
        connected_clients.discard(ws)
    except Exception:
        connected_clients.discard(ws)
