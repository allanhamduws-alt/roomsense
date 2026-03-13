"""Parse raw CSI data from ESP32-S3 into amplitude arrays."""

from typing import Optional
import numpy as np

NUM_SUBCARRIERS = 64


def parse_csi_string(raw: str) -> Optional[np.ndarray]:
    """Parse a raw CSI string from ESP32 serial/UDP into amplitude array.

    ESP32-S3 CSI format: comma-separated I/Q pairs as integers.
    Example: "CSI_DATA,0,3,-1,5,2,-4,..."
    The values come in I,Q pairs → 128 values for 64 subcarriers.

    Returns amplitude array of shape (64,) or None if parsing fails.
    """
    try:
        # Strip prefix if present
        data = raw.strip()
        if data.startswith("CSI_DATA"):
            # Remove the CSI_DATA prefix and any metadata fields
            parts = data.split(",")
            # Find where numeric IQ data starts (skip metadata fields)
            iq_start = 1
            for i, part in enumerate(parts[1:], 1):
                try:
                    int(part.strip())
                    iq_start = i
                    break
                except ValueError:
                    continue
            iq_values = [int(v.strip()) for v in parts[iq_start:] if v.strip()]
        else:
            iq_values = [int(v.strip()) for v in data.split(",") if v.strip()]

        if len(iq_values) < NUM_SUBCARRIERS * 2:
            return None

        # Take first 128 values (64 I/Q pairs)
        iq_values = iq_values[: NUM_SUBCARRIERS * 2]

        # Convert I/Q pairs to amplitude: sqrt(I^2 + Q^2)
        amplitudes = np.zeros(NUM_SUBCARRIERS)
        for i in range(NUM_SUBCARRIERS):
            real = iq_values[2 * i]
            imag = iq_values[2 * i + 1]
            amplitudes[i] = np.sqrt(real**2 + imag**2)

        return amplitudes

    except (ValueError, IndexError):
        return None
