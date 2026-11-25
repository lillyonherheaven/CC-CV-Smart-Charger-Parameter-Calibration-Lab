"""Fixed-step teaching solvers with latched CC -> CV -> OFF transitions."""
from dataclasses import dataclass
import numpy as np
from .model import exact_events, observe


def step(f, y, h, method):
    k1 = f(y)
    if method == "Euler":
        return y + h * k1
    k2 = f(y + h * k1 / (2 if method == "RK4" else 1))
    if method == "Heun":
        return y + h * (k1 + k2) / 2
    if method == "RK4":
        k3 = f(y + h * k2 / 2)
        k4 = f(y + h * k3)
        return y + h * (k1 + 2*k2 + 2*k3 + k4) / 6
    raise ValueError("Method must be Euler, Heun or RK4.")


@dataclass
class Simulation:
    time: np.ndarray
    soc: np.ndarray
    phase: np.ndarray
    switch_time: float | None
    stop_time: float | None

    def observations(self, p):
        return observe(p, self.soc, self.phase)


def solve(p, duration=9000.0, dt=30.0, method="RK4", policy="Event-aware", terminate=True):
    p.validate()
    if not np.isfinite(duration) or not np.isfinite(dt) or duration <= 0 or dt <= 0:
        raise ValueError("Duration and step size must be finite and positive.")
    if duration / dt > 200_000:
        raise ValueError("Use at most 200,000 steps.")
    if policy not in ("Event-aware", "Grid-delayed"):
        raise ValueError("Unknown switch policy.")
    if method not in ("Euler", "Heun", "RK4"):
        raise ValueError("Unknown method.")
    switch = 0.0 if p.mode == "CC/CV" and p.soc0 >= p.switch_soc else None
    phase = "CV" if switch is not None else "CC"
    stop = None
    if phase == "CV" and terminate and p.soc0 >= p.stop_soc:
        phase, stop = "OFF", 0.0
    t, y = 0.0, p.soc0
    ts, ys, phases = [t], [y], [phase]
    # Split a nominal step at an event, then finish its remaining interval.
    for endpoint in np.arange(dt, duration + dt, dt):
        endpoint = min(float(endpoint), duration)
        while endpoint - t > 1e-10:
            h = endpoint - t
            if phase == "CC":
                if p.mode == "CC/CV" and policy == "Event-aware":
                    until_switch = max(0.0, (p.switch_soc - y) / p.rate)
                    if until_switch <= h + 1e-10:
                        t += until_switch
                        y, phase, switch = p.switch_soc, "CV", t
                        ts.append(t); ys.append(y); phases.append(phase)
                        continue
                y += h * p.rate  # all three RK methods are exact for constant derivative
            elif phase == "CV":
                f = lambda s: (p.equilibrium - s) / p.tau
                candidate = step(f, y, h, method)
                if terminate and y < p.stop_soc <= candidate:
                    lo, hi = 0.0, h
                    for _ in range(50):
                        mid = (lo + hi) / 2
                        if step(f, y, mid, method) >= p.stop_soc:
                            hi = mid
                        else:
                            lo = mid
                    t += hi
                    y, phase, stop = p.stop_soc, "OFF", t
                    ts.append(t); ys.append(y); phases.append(phase)
                    continue
                y = candidate
            if not np.isfinite(y) or abs(y) > 1e100:
                raise ValueError("Numerical solution diverged: reduce Δt relative to the CV time constant.")
            t = endpoint
            if phase == "CC" and p.mode == "CC/CV" and y >= p.switch_soc:
                switch, phase = t, "CV"
                if terminate and y >= p.stop_soc:
                    stop, phase = t, "OFF"
            ts.append(t); ys.append(y); phases.append(phase)
        if endpoint >= duration:
            break
    return Simulation(np.array(ts), np.array(ys), np.array(phases), switch, stop)


def target_time(sim, target):
    ids = np.flatnonzero(sim.soc >= target)
    if len(ids) == 0:
        return None
    j = ids[0]
    if j == 0:
        return 0.0
    return float(np.interp(target, sim.soc[j-1:j+1], sim.time[j-1:j+1]))


def convergence(p, duration, steps, terminate=False):
    """Native-node state errors avoid interpolation error masking RK4 order."""
    from .model import exact
    rows = []
    ref_switch, _ = exact_events(p, terminate)
    for policy in ("Event-aware", "Grid-delayed"):
        for method in ("Euler", "Heun", "RK4"):
            previous = None
            for h in sorted(steps, reverse=True):
                sim = solve(p, duration, h, method, policy, terminate)
                err = np.abs(sim.soc - exact(p, sim.time, terminate)["soc_est"])
                maximum = float(np.max(err))
                order = None
                if previous and maximum > 1e-13 and previous[1] > 1e-13:
                    order = float(np.log(previous[1]/maximum)/np.log(previous[0]/h))
                rows.append({"policy": policy, "method": method, "dt_sec": h,
                             "max_soc_error": maximum, "final_soc_error": float(err[-1]),
                             "observed_order": order,
                             "switch_sec": sim.switch_time,
                             "pre_switch_overshoot_v": 0.0 if sim.switch_time is None or ref_switch is None else max(0., sim.switch_time-ref_switch)*p.rate*p.ocv_slope_v,
                             "switch_lag_sec": None if sim.switch_time is None or ref_switch is None else sim.switch_time-ref_switch})
                previous = h, maximum
    return rows
