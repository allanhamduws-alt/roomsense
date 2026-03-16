"""Parse raw CSI data from ESP32-S3 into amplitude arrays."""

import re
from typing import Optional
import numpy as np

NUM_SUBCARRIERS = 64


def parse_csi_string(raw: str) -> Optional[np.ndarray]:
    """Parse a raw CSI string from ESP32 serial/UDP into amplitude array.

    ESP32-S3 CSI format (csi_recv_router):
    CSI_DATA,id,MAC,rssi,rate,...,len,first_word,"[i0,q0,i1,q1,...]"

    The IQ data is inside square brackets at the end of the line.
    Returns amplitude array of shape (64,) or None if parsing fails.
    """
    try:
        data = raw.strip()
        if not data.startswith("CSI_DATA"):
            return None

        # Extract IQ values from square brackets
        match = re.search(r'\[([^\]]+)\]', data)
        if not match:
            return None

        iq_values = [int(v.strip()) for v in match.group(1).split(",") if v.strip()]

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
