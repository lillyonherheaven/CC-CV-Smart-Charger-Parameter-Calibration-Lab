"""Affine-OCV single-cell model with an exact hybrid reference (SI seconds)."""
from dataclasses import dataclass, asdict
import numpy as np


@dataclass(frozen=True)
class Parameters:
    capacity_ah: float = 2.0
    current_a: float = 1.0
    resistance_ohm: float = 0.15
    eta: float = 0.995
    ocv_empty_v: float = 3.0
    ocv_slope_v: float = 1.2
    vmax_v: float = 4.2
    soc0: float = 0.2
    cutoff_a: float = 0.1
    mode: str = "CC/CV"

    def validate(self):
        values = [v for v in asdict(self).values() if isinstance(v, (int, float))]
        if not np.all(np.isfinite(values)):
            raise ValueError("All parameters must be finite.")
        if min(self.capacity_ah, self.current_a, self.resistance_ohm, self.ocv_slope_v) <= 0:
            raise ValueError("Capacity, current, resistance and OCV slope must be positive.")
        if not 0 < self.eta <= 1 or not 0 <= self.soc0 < 1:
            raise ValueError("Require 0 < efficiency <= 1 and 0 <= initial SoC < 1.")
        if self.mode not in ("CC", "CC/CV"):
            raise ValueError("Unknown charger mode.")
        if not self.ocv_empty_v < self.vmax_v <= self.ocv_empty_v + self.ocv_slope_v + 1e-12:
            raise ValueError("Vmax must lie above OCV(0) and at or below OCV(1).")
        if self.soc0 >= self.equilibrium:
            raise ValueError("Initial OCV must be below Vmax.")
        if not 0 < self.cutoff_a < self.current_a:
            raise ValueError("Termination current must be between zero and CC current.")
        return self

    @property
    def rate(self):
        return self.eta * self.current_a / (3600 * self.capacity_ah)

    @property
    def equilibrium(self):
        return (self.vmax_v - self.ocv_empty_v) / self.ocv_slope_v

    @property
    def switch_soc(self):
        return self.equilibrium - self.current_a * self.resistance_ohm / self.ocv_slope_v

    @property
    def tau(self):
        return 3600 * self.capacity_ah * self.resistance_ohm / (self.eta * self.ocv_slope_v)

    @property
    def stop_soc(self):
        return self.equilibrium - self.cutoff_a * self.resistance_ohm / self.ocv_slope_v


def exact_events(p, terminate=True):
    p.validate()
    if p.mode == "CC":
        return None, None
    switch = max(0.0, (p.switch_soc - p.soc0) / p.rate)
    start_soc = max(p.soc0, p.switch_soc)
    initial_cv_current = (p.equilibrium - start_soc) * p.ocv_slope_v / p.resistance_ohm
    stop = switch + p.tau * max(0.0, np.log(initial_cv_current / p.cutoff_a))
    return switch, stop if terminate else None


def observe(p, soc, phase):
    """No clipping: an unstable numerical state remains visible in diagnostics."""
    soc = np.asarray(soc, dtype=float)
    phase = np.asarray(phase)
    current = np.where(phase == "CC", p.current_a,
                       np.where(phase == "CV", (p.equilibrium - soc) * p.ocv_slope_v / p.resistance_ohm, 0.0))
    voltage = p.ocv_empty_v + p.ocv_slope_v * soc + p.resistance_ohm * current
    # Impose the algebraically exact CV constraint: subtractive roundoff here
    # would otherwise create spurious finite-difference calibration sensitivities.
    voltage = np.where(phase == "CV", p.vmax_v, voltage)
    return {"soc_est": soc, "current_a": current, "voltage_v": voltage}


def exact(p, times, terminate=True):
    p.validate()
    t = np.asarray(times, dtype=float)
    if np.any(~np.isfinite(t)) or np.any(t < 0):
        raise ValueError("Times must be finite and nonnegative.")
    if p.mode == "CC":
        return observe(p, p.soc0 + p.rate * t, np.full(t.shape, "CC"))
    switch, stop = exact_events(p, terminate)
    active_t = np.minimum(t, stop) if stop is not None else t
    start_soc = max(p.soc0, p.switch_soc)
    cv = p.equilibrium - (p.equilibrium - start_soc) * np.exp(-np.maximum(0, active_t - switch) / p.tau)
    soc = np.where(active_t < switch, p.soc0 + p.rate * active_t, cv)
    phase = np.where(t < switch, "CC", "CV")
    if stop is not None:
        phase = np.where(t >= stop, "OFF", phase)
    return observe(p, soc, phase)


def exact_target_time(p, target, terminate=True):
    if target <= p.soc0:
        return 0.0
    if p.mode == "CC":
        return (target - p.soc0) / p.rate
    switch, stop = exact_events(p, terminate)
    if target >= p.equilibrium or (terminate and target > max(p.stop_soc, p.soc0) + 1e-12):
        return None
    if target <= p.switch_soc:
        return (target - p.soc0) / p.rate
    start = max(p.switch_soc, p.soc0)
    result = switch + p.tau * np.log((p.equilibrium - start) / (p.equilibrium - target))
    return float(min(result, stop)) if stop is not None else float(result)
