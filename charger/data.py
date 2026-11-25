"""Strict CSV validation and a reproducible, explicitly synthetic bench."""
import numpy as np
import pandas as pd
from .model import Parameters, exact

CHANNELS = ("voltage_v", "current_a", "soc_est")
UNITS = {"voltage_v": "V", "current_a": "A", "soc_est": "fraction"}


def load_csv(source):
    frame = pd.read_csv(source)
    if "time_sec" not in frame or not any(c in frame for c in CHANNELS):
        raise ValueError("CSV needs time_sec and at least one of voltage_v, current_a, soc_est.")
    frame = frame[["time_sec"] + [c for c in CHANNELS if c in frame]].copy()
    for name in frame:
        # Empty readings may be NaN; nonnumeric strings and infinities are errors.
        frame[name] = pd.to_numeric(frame[name], errors="raise")
        if np.isinf(frame[name]).any():
            raise ValueError(f"Infinite value in {name}.")
    if frame.time_sec.isna().any() or (frame.time_sec < 0).any():
        raise ValueError("Times must be present and nonnegative.")
    frame = frame.sort_values("time_sec").reset_index(drop=True)
    if frame.time_sec.duplicated().any():
        raise ValueError("Duplicate times: average repeated measurements before uploading.")
    if len(frame) < 4 or not frame[list(frame.columns[1:])].notna().any(axis=1).all():
        raise ValueError("Need at least four rows, each with at least one measured channel.")
    if "soc_est" in frame and ((frame.soc_est.dropna() < 0) | (frame.soc_est.dropna() > 1)).any():
        raise ValueError("soc_est uses fractions from 0 to 1, not percent.")
    if "current_a" in frame and (frame.current_a.dropna() < 0).any():
        raise ValueError("Use positive current into the cell (charging).")
    return frame


def sample_data(seed=2026):
    """Fixed hidden parameters independent of sliders; includes CC and CV."""
    truth = Parameters(capacity_ah=2.12, resistance_ohm=0.18, soc0=0.23)
    t = np.arange(0, 8401, 120, dtype=float)
    # Uninterrupted CV taper avoids fitting the discontinuous OFF observation.
    values = exact(truth, t, terminate=False)
    rng = np.random.default_rng(seed)
    noise = {"voltage_v": 0.006, "current_a": 0.008, "soc_est": 0.003}
    frame = pd.DataFrame({"time_sec": t})
    for channel in CHANNELS:
        frame[channel] = values[channel] + rng.normal(0, noise[channel], len(t))
    frame["soc_est"] = frame.soc_est.clip(0, 1)
    frame["current_a"] = frame.current_a.clip(lower=0)
    return frame, truth
