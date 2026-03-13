"""Feature extraction from CSI amplitude arrays.

Rule-based detection using variance thresholds and FFT.
No ML required for V1.
"""

from typing import Deque, Dict, List, Optional
import numpy as np
from collections import deque

# Configurable thresholds
PRESENCE_VARIANCE_THRESHOLD = 5.0
INTENSITY_MAX_VARIANCE = 50.0
BREATHING_LOW_HZ = 0.1
BREATHING_HIGH_HZ = 0.5
SAMPLE_RATE = 2.0  # ~2 Hz sampling rate

# Buffer for time-series analysis (breathing detection)
BUFFER_SIZE = 64  # ~32 seconds at 2Hz
amplitude_buffer: Deque[np.ndarray] = deque(maxlen=BUFFER_SIZE)


def update_buffer(amplitudes: np.ndarray):
    """Add new amplitude sample to the rolling buffer."""
    amplitude_buffer.append(amplitudes.copy())


def detect_presence(amplitudes: np.ndarray, baseline_mean: Optional[np.ndarray] = None) -> bool:
    """Detect presence based on variance threshold on subcarrier amplitudes.

    If a baseline is available, compare against it.
    Otherwise use raw variance across subcarriers.
    """
    if baseline_mean is not None:
        diff = amplitudes - baseline_mean
        variance = np.var(diff)
    else:
        variance = np.var(amplitudes)

    return bool(variance > PRESENCE_VARIANCE_THRESHOLD)


def compute_intensity(amplitudes: np.ndarray, baseline_mean: Optional[np.ndarray] = None) -> float:
    """Compute movement intensity as normalized variance score 0–100."""
    if baseline_mean is not None:
        diff = amplitudes - baseline_mean
        variance = np.var(diff)
    else:
        variance = np.var(amplitudes)

    # Normalize to 0-100
    score = min(100.0, (variance / INTENSITY_MAX_VARIANCE) * 100.0)
    return round(score, 1)


def detect_breathing_rate() -> Optional[float]:
    """Estimate breathing rate using FFT on slow-varying subcarriers.

    Looks for dominant frequency in 0.1–0.5 Hz band (6–30 breaths/min).
    Returns breaths per minute or None if not enough data.
    """
    if len(amplitude_buffer) < BUFFER_SIZE:
        return None

    # Use mean amplitude across subcarriers over time
    time_series = np.array([np.mean(a) for a in amplitude_buffer])

    # Remove DC component
    time_series = time_series - np.mean(time_series)

    # Apply FFT
    fft_result = np.fft.rfft(time_series)
    freqs = np.fft.rfftfreq(len(time_series), d=1.0 / SAMPLE_RATE)
    magnitudes = np.abs(fft_result)

    # Filter to breathing band (0.1–0.5 Hz)
    mask = (freqs >= BREATHING_LOW_HZ) & (freqs <= BREATHING_HIGH_HZ)
    if not np.any(mask):
        return None

    breathing_freqs = freqs[mask]
    breathing_mags = magnitudes[mask]

    # Find dominant frequency
    peak_idx = np.argmax(breathing_mags)
    peak_freq = breathing_freqs[peak_idx]
    peak_mag = breathing_mags[peak_idx]

    # Only report if signal is strong enough relative to noise
    noise_floor = np.median(magnitudes[1:])  # skip DC
    if peak_mag < noise_floor * 2.0:
        return None

    # Convert Hz to breaths per minute
    bpm = round(peak_freq * 60.0, 1)
    return bpm


def classify_activity(intensity: float, presence: bool) -> str:
    """Rule-based activity classification.

    Categories: empty, still, sitting, walking, lying
    Based on intensity level and variance patterns.
    """
    if not presence:
        return "empty"

    if intensity < 5:
        # Very low movement – could be lying or very still
        if len(amplitude_buffer) >= 10:
            # Check if there's periodic low-frequency variation (lying/breathing)
            recent = [np.var(a) for a in list(amplitude_buffer)[-10:]]
            recent_std = np.std(recent)
            if recent_std < 1.0:
                return "lying"
        return "still"
    elif intensity < 25:
        return "sitting"
    else:
        return "walking"


def analyze(amplitudes: np.ndarray, baseline_mean: Optional[np.ndarray] = None) -> Dict:
    """Run full detection pipeline on a CSI amplitude frame.

    Returns dict with presence, activity, intensity, breathing_rate.
    """
    update_buffer(amplitudes)

    presence = detect_presence(amplitudes, baseline_mean)
    intensity = compute_intensity(amplitudes, baseline_mean)
    breathing_rate = detect_breathing_rate()
    activity = classify_activity(intensity, presence)

    return {
        "presence": presence,
        "activity": activity,
        "intensity": intensity,
        "breathing_rate": breathing_rate,
        "amplitudes": amplitudes.tolist(),
    }
