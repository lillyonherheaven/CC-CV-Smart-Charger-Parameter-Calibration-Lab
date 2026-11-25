"""Unit-aware metrics and bounded multi-channel parameter estimation."""
from dataclasses import asdict, replace
import numpy as np
import pandas as pd
from scipy.optimize import least_squares
from .model import exact
from .data import CHANNELS, UNITS


def metrics(observed, predicted):
    y, z = np.asarray(observed), np.asarray(predicted)
    good = np.isfinite(y) & np.isfinite(z)
    if not good.any():
        return {"n": 0, "MAE": None, "RMSE": None, "max_error": None, "bias_exp_minus_model": None}
    e = y[good] - z[good]
    return {"n": int(len(e)), "MAE": float(np.mean(np.abs(e))),
            "RMSE": float(np.sqrt(np.mean(e**2))), "max_error": float(np.max(np.abs(e))),
            "bias_exp_minus_model": float(np.mean(e))}


def comparison(frame, prediction):
    rows = []
    for c in CHANNELS:
        if c in frame:
            rows.append({"channel": c, "unit": UNITS[c], **metrics(frame[c], prediction[c])})
    return pd.DataFrame(rows)


def local_defects(p, steps):
    """One-step state defects on an isolated smooth CV interval."""
    from .solvers import step
    start = max(p.soc0, p.switch_soc)
    rows = []
    for method in ("Euler", "Heun", "RK4"):
        previous = None
        for h in sorted(steps, reverse=True):
            truth = p.equilibrium-(p.equilibrium-start)*np.exp(-h/p.tau)
            predicted = step(lambda s: (p.equilibrium-s)/p.tau, start, h, method)
            error = float(abs(predicted-truth))
            order = None
            if previous and error > 1e-13 and previous[1] > 1e-13:
                order = float(np.log(previous[1]/error)/np.log(previous[0]/h))
            rows.append({"method": method, "dt_sec": h, "one_step_soc_defect": error,
                         "observed_local_order": order})
            previous = h, error
    return pd.DataFrame(rows)


def calibrate(frame, base, names=("capacity_ah", "resistance_ohm", "soc0"),
              sigmas=None, terminate=False):
    """Fit exact trajectories, so fitted parameters do not absorb solver error.

    Capacity and efficiency cannot both be fitted from this model. OCV endpoints
    and CC current are independently measured and fixed here.
    """
    base.validate()
    sigmas = sigmas or {"voltage_v": .006, "current_a": .008, "soc_est": .003}
    bounds = {"capacity_ah": (.1, 10.), "resistance_ohm": (.005, 1.),
              "soc0": (0., min(.99, base.equilibrium - 1e-6))}
    if not names or any(n not in bounds for n in names):
        raise ValueError("Select capacity_ah, resistance_ohm and/or soc0.")
    channels = [c for c in CHANNELS if c in frame and frame[c].notna().any()]
    if any(not np.isfinite(sigmas[c]) or sigmas[c] <= 0 for c in channels):
        raise ValueError("Noise standard deviations must be positive.")
    masks = {c: frame[c].notna().to_numpy() for c in channels}
    count = sum(int(m.sum()) for m in masks.values())
    if count <= len(names):
        raise ValueError("Need more measured values than fitted parameters.")
    t = frame.time_sec.to_numpy()
    def residual(x):
        p = replace(base, **dict(zip(names, x)))
        pred = exact(p, t, terminate)
        return np.concatenate([(pred[c][masks[c]] - frame[c].to_numpy()[masks[c]]) / sigmas[c]
                               for c in channels])
    low = np.array([bounds[n][0] for n in names])
    high = np.array([bounds[n][1] for n in names])
    initial = np.clip([getattr(base, n) for n in names], low+1e-8, high-1e-8)
    result = least_squares(residual, initial, bounds=(low, high), x_scale="jac", max_nfev=1500)
    fitted = replace(base, **dict(zip(names, result.x)))
    # Scale parameter columns to the bounds before reporting conditioning.
    singular = np.linalg.svd(result.jac * (high-low), compute_uv=False)
    rank = int(np.sum(singular > (singular[0]*1e-8 if len(singular) else 0)))
    condition = float(singular[0]/singular[-1]) if len(singular) and singular[-1] > 1e-12 else None
    warning = []
    if rank < len(names) or condition is None or condition > 1e6:
        warning.append("Weak parameter identifiability: collect CC and CV and an independent OCV/SoC anchor.")
    if np.any(result.active_mask):
        warning.append("At least one parameter reached a fitting bound; inspect model mismatch and units.")
    if terminate:
        warning.append("Termination makes the current observation discontinuous; exclude OFF samples for smoother fitting.")
    return fitted, {"success": bool(result.success), "message": result.message,
                    "names": list(names), "weighted_sum_squares": float(2*result.cost),
                    "n_observations": count, "jacobian_rank": rank,
                    "scaled_jacobian_condition": condition, "warnings": warning,
                    "parameters": asdict(fitted),
                    "metrics": comparison(frame, exact(fitted, t, terminate)).to_dict(orient="records"),
                    "scope": "In-sample fit; not independent experimental validation."}
