"""CSI-based presence and movement detection.

V1: PIR-sensor-style motion detection.
- Detects movement via MV (moving variance of turbulence) spikes
- Holds presence state for HOLD_SECONDS after last motion
- At 2Hz/7m/through-wall: sitting still is undetectable,
  but walking/moving creates clear 10-50x spikes above baseline
"""

from typing import Deque, Dict, List, Optional
import numpy as np
from collections import deque
import time

# Sampling
SAMPLE_RATE = 10.0
BUFFER_SIZE = 300  # ~30 seconds at 10Hz

# Subcarriers: skip guard bands, DC, and null zone (27-37 dead in this setup)
VALID_SUBCARRIERS = list(range(6, 27)) + list(range(38, 59))

# Moving variance window — short for fast spike detection
MV_WINDOW = 30  # 3 seconds at 10Hz

# Auto-calibration: first ~15s must be empty room
BASELINE_FRAMES = 150  # 15s at 10Hz
_baseline_collected = False
_motion_threshold: float = 0.0

# PIR-style hold: keep presence for this long after last motion
HOLD_SECONDS = 30.0
_last_motion_time: float = 0.0

# Buffers
amplitude_buffer: Deque[np.ndarray] = deque(maxlen=BUFFER_SIZE)
_turbulence_buffer: Deque[float] = deque(maxlen=BUFFER_SIZE)
_mv_buffer: Deque[float] = deque(maxlen=BUFFER_SIZE)

# Smoothing
intensity_history: Deque[float] = deque(maxlen=5)

# Activity hysteresis
HYSTERESIS_COUNT = 3
_current_activity: str = "empty"
_pending_activity: str = "empty"
_pending_count: int = 0

# Frame counter
_frame_count: int = 0

# Peak MV tracker (for intensity during hold period)
_recent_peak_mv: float = 0.0
_peak_decay: float = 0.95  # decay per frame


def reset_detector():
    """Reset everything for fresh auto-calibration."""
    global _frame_count, _baseline_collected, _motion_threshold
    global _last_motion_time, _recent_peak_mv
    global _current_activity, _pending_activity, _pending_count

    _frame_count = 0
    _baseline_collected = False
    _motion_threshold = 0.0
    _last_motion_time = 0.0
    _recent_peak_mv = 0.0
    amplitude_buffer.clear()
    _turbulence_buffer.clear()
    _mv_buffer.clear()
    intensity_history.clear()
    _current_activity = "empty"
    _pending_activity = "empty"
    _pending_count = 0
    print("Detector reset — leave room empty for 15 seconds")


def set_calibration_thresholds(baselines: Dict[str, Dict]):
    """Store calibration data (not used in V1 detection)."""
    if baselines:
        print(f"Calibration data stored for: {list(baselines.keys())}")


# --- Core Metrics ---

def _compute_turbulence(amplitudes: np.ndarray) -> float:
    """CV across valid subcarriers."""
    selected = amplitudes[VALID_SUBCARRIERS]
    alive = selected[selected >= 0.5]
    if len(alive) < 4:
        return 0.0
    mean = np.mean(alive)
    if mean < 0.1:
        return 0.0
    return float(np.std(alive) / mean)


def _compute_moving_variance(buffer: deque, window: int) -> float:
    """Variance of recent turbulence values."""
    if len(buffer) < 3:
        return 0.0
    recent = list(buffer)[-window:]
    return float(np.var(recent))


# --- Pipeline ---

def update_buffer(amplitudes: np.ndarray):
    """Add frame and compute metrics."""
    global _frame_count, _baseline_collected

    amplitude_buffer.append(amplitudes.copy())
    _frame_count += 1

    turb = _compute_turbulence(amplitudes)
    _turbulence_buffer.append(turb)

    mv = _compute_moving_variance(_turbulence_buffer, MV_WINDOW)
    _mv_buffer.append(mv)

    if not _baseline_collected and _frame_count == BASELINE_FRAMES:
        _do_auto_calibrate()


def _do_auto_calibrate():
    """Set motion threshold from empty-room baseline."""
    global _baseline_collected, _motion_threshold

    mv_values = list(_mv_buffer)
    if len(mv_values) < 5:
        return

    p95 = float(np.percentile(mv_values, 95))
    p50 = float(np.median(mv_values))

    # Motion threshold: 3x the P95 of empty room noise
    # Empty room P95 is typically ~0.0005-0.003
    # Walking creates spikes of 0.005-0.03 (10-50x above)
    _motion_threshold = max(p95 * 3.0, p50 * 5.0, 0.002)

    _baseline_collected = True
    print(f"Auto-calibrated from {len(mv_values)} frames:")
    print(f"  empty P50={p50:.6f}, P95={p95:.6f}")
    print(f"  motion_threshold={_motion_threshold:.6f}")


# --- Detection ---

def detect_presence() -> bool:
    """PIR-style: motion spike → hold presence for HOLD_SECONDS."""
    global _last_motion_time, _recent_peak_mv

    if not _baseline_collected or len(_mv_buffer) < MV_WINDOW:
        return False

    current_mv = _mv_buffer[-1]
    now = time.time()

    # Detect motion spike
    if current_mv > _motion_threshold:
        _last_motion_time = now
        _recent_peak_mv = max(_recent_peak_mv, current_mv)
    else:
        # Decay peak
        _recent_peak_mv *= _peak_decay

    # Hold presence for HOLD_SECONDS after last motion
    elapsed = now - _last_motion_time
    if _last_motion_time > 0 and elapsed < HOLD_SECONDS:
        return True

    return False


def compute_intensity() -> float:
    """Movement intensity 0-100 based on MV magnitude."""
    if not _baseline_collected or len(_mv_buffer) < MV_WINDOW:
        return 0.0

    current_mv = _mv_buffer[-1]

    # Use current MV or decaying peak (whichever is higher)
    effective_mv = max(current_mv, _recent_peak_mv)

    # Scale: motion_threshold = ~10, heavy movement = ~100
    if effective_mv < _motion_threshold * 0.5:
        raw = 0.0
    else:
        raw = min(100.0, (effective_mv / (_motion_threshold * 5.0)) * 100.0)

    intensity_history.append(raw)
    if len(intensity_history) >= 3:
        return round(float(np.mean(list(intensity_history))), 1)
    return round(raw, 1)


def classify_activity(intensity: float, presence: bool) -> str:
    """Simple activity classification with hysteresis."""
    global _current_activity, _pending_activity, _pending_count

    if not presence:
        raw_activity = "empty"
    elif intensity < 15.0:
        raw_activity = "still"
    elif intensity < 50.0:
        raw_activity = "sitting"
    else:
        raw_activity = "walking"

    if raw_activity == _current_activity:
        _pending_activity = _current_activity
        _pending_count = 0
        return _current_activity

    if raw_activity == _pending_activity:
        _pending_count += 1
    else:
        _pending_activity = raw_activity
        _pending_count = 1

    if _pending_count >= HYSTERESIS_COUNT:
        _current_activity = _pending_activity
        _pending_count = 0

    return _current_activity


def detect_breathing_rate(presence: bool) -> Optional[float]:
    """Estimate breathing rate via FFT. Only when presence detected."""
    if not presence or len(amplitude_buffer) < BUFFER_SIZE:
        return None

    time_series = np.array([np.mean(a[VALID_SUBCARRIERS]) for a in amplitude_buffer])
    time_series = time_series - np.mean(time_series)

    window = np.hanning(len(time_series))
    time_series = time_series * window

    fft_result = np.fft.rfft(time_series)
    freqs = np.fft.rfftfreq(len(time_series), d=1.0 / SAMPLE_RATE)
    magnitudes = np.abs(fft_result)

    mask = (freqs >= 0.1) & (freqs <= 0.5)
    if not np.any(mask):
        return None

    breathing_freqs = freqs[mask]
    breathing_mags = magnitudes[mask]

    peak_idx = np.argmax(breathing_mags)
    peak_freq = breathing_freqs[peak_idx]
    peak_mag = breathing_mags[peak_idx]

    noise_floor = np.median(magnitudes[1:])
    if noise_floor == 0 or peak_mag < noise_floor * 3.0:
        return None

    bpm = round(peak_freq * 60.0, 1)
    if bpm < 8.0 or bpm > 25.0:
        return None

    return bpm


def analyze(amplitudes: np.ndarray, baseline_mean: Optional[np.ndarray] = None) -> Dict:
    """Run full detection pipeline on a CSI amplitude frame."""
    update_buffer(amplitudes)

    presence = detect_presence()
    intensity = compute_intensity()
    breathing_rate = detect_breathing_rate(presence)
    activity = classify_activity(intensity, presence)

    return {
        "presence": presence,
        "activity": activity,
        "intensity": intensity,
        "breathing_rate": breathing_rate,
        "amplitudes": amplitudes.tolist(),
    }
