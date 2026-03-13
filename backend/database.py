"""SQLite database setup and access layer."""

from typing import Dict, List, Optional

import aiosqlite
import os
from datetime import datetime

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./roomsense.db")
# Extract file path from SQLite URL
DB_PATH = DATABASE_URL.replace("sqlite:///", "")


async def init_db():
    """Create tables if they don't exist."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                presence INTEGER NOT NULL,
                activity TEXT NOT NULL,
                intensity REAL NOT NULL,
                breathing_rate REAL
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS calibration (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                label TEXT NOT NULL,
                mean_amplitudes TEXT NOT NULL,
                std_amplitudes TEXT NOT NULL,
                threshold REAL NOT NULL,
                created_at TEXT NOT NULL
            )
        """)
        await db.commit()


async def insert_event(presence: bool, activity: str, intensity: float, breathing_rate: Optional[float]):
    """Insert a detection event."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO events (timestamp, presence, activity, intensity, breathing_rate) VALUES (?, ?, ?, ?, ?)",
            (datetime.now().isoformat(), int(presence), activity, intensity, breathing_rate),
        )
        await db.commit()


async def get_history(limit: int = 100) -> List[Dict]:
    """Return the last N events."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM events ORDER BY id DESC LIMIT ?", (limit,)
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]


async def save_calibration(label: str, mean_amplitudes: str, std_amplitudes: str, threshold: float):
    """Save a calibration baseline."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO calibration (label, mean_amplitudes, std_amplitudes, threshold, created_at) VALUES (?, ?, ?, ?, ?)",
            (label, mean_amplitudes, std_amplitudes, threshold, datetime.now().isoformat()),
        )
        await db.commit()


async def get_calibration(label: str) -> Optional[Dict]:
    """Get the latest calibration for a label."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM calibration WHERE label = ? ORDER BY id DESC LIMIT 1", (label,)
        )
        row = await cursor.fetchone()
        return dict(row) if row else None
