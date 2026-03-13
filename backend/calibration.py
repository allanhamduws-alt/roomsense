"""Calibration: record baseline CSI snapshots and compute thresholds."""

from typing import Dict, List, Optional
import json
import numpy as np
from csi_parser import NUM_SUBCARRIERS
from database import save_calibration, get_calibration

# In-memory calibration data (loaded from DB on startup)
baselines: Dict[str, Dict] = {}


async def load_baselines():
    """Load all calibration baselines from the database."""
    for label in ["empty", "still", "sitting", "walking", "lying"]:
        cal = await get_calibration(label)
        if cal:
            baselines[label] = {
                "mean": np.array(json.loads(cal["mean_amplitudes"])),
                "std": np.array(json.loads(cal["std_amplitudes"])),
                "threshold": cal["threshold"],
            }


def get_empty_baseline() -> Optional[np.ndarray]:
    """Return the mean amplitudes from the 'empty' room calibration."""
    if "empty" in baselines:
        return baselines["empty"]["mean"]
    return None


async def record_calibration(label: str, snapshots: List[List[float]]) -> Dict:
    """Process a list of CSI amplitude snapshots for a given activity label.

    Args:
        label: Activity label (empty, still, sitting, walking, lying)
        snapshots: List of amplitude arrays (each 64 floats)

    Returns:
        Dict with computed mean, std, and threshold.
    """
    if not snapshots:
        raise ValueError("No snapshots provided")

    data = np.array(snapshots)
    mean_amps = np.mean(data, axis=0)
    std_amps = np.std(data, axis=0)

    # Threshold = mean variance + 2 * std of variance
    variances = np.var(data, axis=1)
    threshold = float(np.mean(variances) + 2 * np.std(variances))

    # Save to database
    await save_calibration(
        label=label,
        mean_amplitudes=json.dumps(mean_amps.tolist()),
        std_amplitudes=json.dumps(std_amps.tolist()),
        threshold=threshold,
    )

    # Update in-memory cache
    baselines[label] = {
        "mean": mean_amps,
        "std": std_amps,
        "threshold": threshold,
    }

    return {
        "label": label,
        "samples": len(snapshots),
        "threshold": round(threshold, 2),
    }
