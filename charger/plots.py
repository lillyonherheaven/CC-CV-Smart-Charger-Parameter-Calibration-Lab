"""Reusable, labeled scientific figures for the app and 300-dpi exports."""
import io
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.ticker import NullFormatter
from .model import exact, exact_events
from .data import CHANNELS

LABELS = {"voltage_v": "Terminal voltage (V)", "current_a": "Cell current (A)", "soc_est": "SoC (fraction)"}


def png_bytes(fig, dpi=300):
    output = io.BytesIO()
    fig.savefig(output, format="png", dpi=dpi, bbox_inches="tight")
    return output.getvalue()


def charging_figure(p, duration, sim=None, data=None, terminate=False, data_label="Measurements", baseline=None):
    fig, axes = plt.subplots(3, 1, figsize=(10, 8), sharex=True)
    t = np.linspace(0, duration, 1600)
    reference = exact(p, t, terminate)
    before = exact(baseline, t, terminate) if baseline is not None else None
    switch, _ = exact_events(p, terminate)
    observations = sim.observations(p) if sim is not None else None
    for ax, c in zip(axes, CHANNELS):
        if before is not None:
            ax.plot(t/60, before[c], "--", color="gray", label="Before calibration")
        ax.plot(t/60, reference[c], color="#167d9a", label="Exact affine-OCV model")
        if sim is not None:
            ax.plot(sim.time/60, observations[c], "--", color="#a64d79", label="Selected numerical solver")
        if data is not None and c in data:
            ax.scatter(data.time_sec/60, data[c], s=13, alpha=.7, color="#dd813b", label=data_label)
        if switch is not None and switch <= duration:
            ax.axvline(switch/60, color="gray", linestyle=":", label="Exact CC → CV")
        ax.set_ylabel(LABELS[c]); ax.grid(alpha=.25); ax.legend(fontsize=8)
    axes[-1].set_xlabel("Elapsed time (minutes)")
    fig.tight_layout()
    return fig


def residual_figure(data, predictions):
    fig, axes = plt.subplots(3, 1, figsize=(10, 7), sharex=True)
    for ax, c in zip(axes, CHANNELS):
        if c in data:
            ax.scatter(data.time_sec/60, data[c]-predictions[c], s=14, color="#167d9a")
        else:
            ax.text(.5, .5, "Channel not supplied", transform=ax.transAxes, ha="center")
        ax.axhline(0, color="black", linewidth=.8)
        ax.set_ylabel("Residual: " + LABELS[c]); ax.grid(alpha=.25)
    axes[-1].set_xlabel("Elapsed time (minutes)")
    fig.suptitle("Experiment − model: in-sample residuals", fontsize=12)
    fig.tight_layout()
    return fig


def convergence_figure(rows):
    fig, axes = plt.subplots(1, 3, figsize=(15, 4.5))
    for (policy, method), group in rows.groupby(["policy", "method"]):
        group = group.sort_values("dt_sec")
        style = "o-" if policy == "Event-aware" else "x--"
        label = f"{method}: {policy}"
        axes[0].loglog(group.dt_sec, np.maximum(group.max_soc_error, 1e-16), style, label=label)
        axes[1].plot(group.dt_sec, group.max_soc_error, style, label=label)
        axes[2].plot(group.dt_sec, group.switch_lag_sec, style, label=label)
    for ax in axes:
        ax.set_xlabel("Step Δt (s)"); ax.grid(alpha=.25)
    axes[0].set_ylabel("Max native-node SoC error (log scale)")
    axes[1].set_ylabel("Max native-node SoC error (linear scale)")
    axes[2].set_ylabel("CC → CV switching lag (s)")
    axes[0].legend(fontsize=7)
    steps = sorted(rows.dt_sec.unique())
    axes[0].set_xticks(steps, labels=[f"{h:g}" for h in steps])
    axes[0].xaxis.set_minor_formatter(NullFormatter())
    fig.tight_layout()
    return fig


def physics_tables(p, fixed_soc=.5, curvature=.4):
    """Independent relationship experiments, not one evolving charge trajectory.

    curvature is dimensionless k/b, so |curvature|<1 guarantees monotone OCV.
    The nonlinear OCV illustration is NOT used by the affine charging solvers.
    """
    p.validate()
    if not 0 <= fixed_soc <= 1 or not abs(curvature) < 1:
        raise ValueError("Require 0≤fixed SoC≤1 and |curvature|<1.")
    i = np.linspace(0, p.current_a, 161)
    ocv_fixed = p.ocv_empty_v + p.ocv_slope_v*fixed_soc
    s = np.linspace(0, 1, 201)
    k = p.ocv_slope_v*curvature
    relations = pd.DataFrame({"current_magnitude_a": i,
        "charge_terminal_v": ocv_fixed+p.resistance_ohm*i,
        "discharge_terminal_v": ocv_fixed-p.resistance_ohm*i,
        "charge_soc_rate_per_sec": p.eta*i/(3600*p.capacity_ah)})
    ocv = pd.DataFrame({"soc_fraction": s, "affine_ocv_v": p.ocv_empty_v+p.ocv_slope_v*s,
                       "illustrative_nonlinear_ocv_v": p.ocv_empty_v+p.ocv_slope_v*s+k*s*(1-s)})
    switch, _ = exact_events(p, terminate=False)
    cc_end = max(0., (min(p.switch_soc, 1.)-p.soc0)/p.rate) if p.mode == "CC/CV" else (1-p.soc0)/p.rate
    cc_t = np.linspace(0, cc_end, 161)
    cc = pd.DataFrame({"time_sec": cc_t, "soc_fraction": p.soc0+p.rate*cc_t})
    # This constitutive CV experiment is available even if the engine is set to CC-only.
    cv_start = max(p.soc0, p.switch_soc)
    ic = (p.equilibrium-cv_start)*p.ocv_slope_v/p.resistance_ohm
    cv_t = np.linspace(0, 5*p.tau, 241)
    cv = pd.DataFrame({"time_since_cv_sec": cv_t, "current_a": ic*np.exp(-cv_t/p.tau)})
    return {"ohms_law": relations, "ocv": ocv, "cc_growth": cc, "cv_taper": cv}


def physics_figure(p, fixed_soc=.5, curvature=.4):
    tables = physics_tables(p, fixed_soc, curvature)
    r, ocv, cc, cv = (tables[c] for c in ("ohms_law", "ocv", "cc_growth", "cv_taper"))
    fig, axes = plt.subplots(2, 3, figsize=(15, 8))
    ax = axes[0, 0]
    ax.plot(r.current_magnitude_a, r.charge_terminal_v, label=f"Charge: slope +R = +{p.resistance_ohm:g} Ω")
    ax.plot(r.current_magnitude_a, r.discharge_terminal_v, "--", label=f"Discharge: slope −R = −{p.resistance_ohm:g} Ω")
    ax.axhline(p.vmax_v, linestyle=":", color="gray", label="Charger voltage limit")
    ax.set(xlabel="Current magnitude (A)", ylabel="Terminal voltage (V)", title=f"Fixed SoC = {fixed_soc:.2f}; separate current sweeps")
    ax.legend(fontsize=7)
    axes[0, 1].plot(r.current_magnitude_a, r.charge_soc_rate_per_sec, color="#167d9a")
    axes[0, 1].set(xlabel="Charging current (A)", ylabel="dSoC/dt (fraction/s)", title="Linear charge accumulation rate")
    axes[0, 2].plot(cc.time_sec/60, cc.soc_fraction, color="#167d9a")
    axes[0, 2].set(xlabel="CC elapsed time (min)", ylabel="SoC (fraction)", title="CC segment: s(t) = s₀ + rt")
    if cc.time_sec.iloc[-1] == 0:
        axes[0, 2].text(.5, .5, "Starts in CV; no CC interval", transform=axes[0, 2].transAxes, ha="center")
    axes[1, 0].plot(ocv.soc_fraction, ocv.affine_ocv_v, "--", label="Affine OCV: engine and calibration")
    axes[1, 0].plot(ocv.soc_fraction, ocv.illustrative_nonlinear_ocv_v, label="Nonlinear OCV: illustration only")
    axes[1, 0].set(xlabel="SoC (fraction)", ylabel="Open-circuit voltage (V)", title="OCV law: affine versus curved example")
    axes[1, 0].legend(fontsize=7)
    axes[1, 1].plot(cv.time_since_cv_sec/60, cv.current_a, color="#dd813b")
    axes[1, 1].set(xlabel="Time since CV entry (min)", ylabel="Charging current (A)", title="Nonlinear exponential taper: I = I_c exp(−t/τ)")
    axes[1, 2].semilogy(cv.time_since_cv_sec/60, cv.current_a, color="#dd813b")
    axes[1, 2].set(xlabel="Time since CV entry (min)", ylabel="Charging current (A, log scale)", title="Semilog taper: log-current slope −60/τ per minute")
    for ax in axes.flat: ax.grid(alpha=.25)
    fig.tight_layout()
    return fig, tables
