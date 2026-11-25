"""Reproducible report assets, synthetic CSV, calibration and numerical tables."""
from dataclasses import asdict
from pathlib import Path
import json
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from charger.model import Parameters, exact, exact_events, exact_target_time
from charger.data import sample_data, CHANNELS
from charger.analysis import calibrate, comparison
from charger.solvers import solve, convergence
from charger.plots import physics_figure, png_bytes
from charger.export import build_bundle, parameter_table
from charger.analysis import local_defects


def main():
    out = Path(__file__).resolve().parent / "outputs"
    out.mkdir(exist_ok=True)
    data, truth = sample_data()
    data.to_csv(out / "synthetic_experiment.csv", index=False)
    base = Parameters()
    fitted, info = calibrate(data, base)
    info["synthetic_truth"] = asdict(truth)
    info["exact_switch_sec"], info["exact_stop_sec"] = exact_events(fitted)
    info["target_95_percent_sec"] = exact_target_time(fitted, .95, False)
    (out / "sample_calibration.json").write_text(json.dumps(info, indent=2), encoding="utf-8")
    before = comparison(data, exact(base, data.time_sec.to_numpy(), False)).assign(fit="Before")
    after = comparison(data, exact(fitted, data.time_sec.to_numpy(), False)).assign(fit="After")
    pd.concat([before, after]).to_csv(out / "calibration_metrics.csv", index=False)
    rows = pd.DataFrame(convergence(base, 9000, [240, 120, 60, 30]))
    rows.to_csv(out / "convergence.csv", index=False)
    fig, axes = plt.subplots(3, 1, figsize=(10, 9), sharex=True)
    t = np.linspace(0, 9000, 1600)
    pred = exact(fitted, t, False)
    old = exact(base, t, False)
    for ax, c, unit in zip(axes, CHANNELS, ["Terminal voltage (V)", "Current (A)", "SoC (fraction)"]):
        ax.plot(t/60, old[c], "--", color="gray", label="Before calibration")
        ax.plot(t/60, pred[c], color="#167d9a", label="Calibrated exact model")
        ax.scatter(data.time_sec/60, data[c], s=12, color="#dd813b", label="Synthetic bench")
        ax.set_ylabel(unit); ax.grid(alpha=.2); ax.legend(fontsize=8)
    axes[-1].set_xlabel("Time (minutes)"); fig.tight_layout()
    fig.savefig(out / "calibrated_overlay.png", dpi=300); plt.close(fig)
    fig, axes = plt.subplots(3, 1, figsize=(10, 7), sharex=True)
    pred = exact(fitted, data.time_sec.to_numpy(), False)
    for ax, c in zip(axes, CHANNELS):
        ax.scatter(data.time_sec/60, data[c]-pred[c], s=14, color="#167d9a")
        ax.axhline(0, color="black", linewidth=.8); ax.set_ylabel(c); ax.grid(alpha=.2)
    axes[-1].set_xlabel("Time (minutes)"); fig.tight_layout()
    fig.savefig(out / "residuals.png", dpi=300); plt.close(fig)
    from charger.plots import convergence_figure
    fig = convergence_figure(rows)
    fig.tight_layout(); fig.savefig(out / "convergence.png", dpi=300); plt.close(fig)
    # One-dimensional direction field and phase line near the CV equilibrium.
    fig, ax = plt.subplots(figsize=(9, 4))
    states = np.linspace(.82, 1.06, 19)
    velocity = (base.equilibrium-states)/base.tau
    ax.quiver(states, np.zeros_like(states), np.sign(velocity)*.01, np.zeros_like(states),
              angles="xy", scale_units="xy", scale=1, color="#167d9a")
    ax.axvline(base.equilibrium, color="#dd813b", label="CV equilibrium s*=1")
    ax.axvspan(1, 1.07, color="red", alpha=.06, label="Outside physical SoC domain")
    ax.set(xlabel="SoC (fraction)", yticks=[], ylim=(-.1, .1), title="CV phase line: ideal bidirectional mathematical extension")
    ax.legend(fontsize=8); fig.tight_layout(); fig.savefig(out / "phase_line.png", dpi=300); plt.close(fig)
    fig, relationships = physics_figure(base)
    (out / "physics_relationships.png").write_bytes(png_bytes(fig)); plt.close(fig)
    sim = solve(base, 9000, 60, "RK4", terminate=False)
    from charger.plots import charging_figure
    fig = charging_figure(base, 9000, sim=sim, terminate=False)
    (out / "charging_curves.png").write_bytes(png_bytes(fig)); plt.close(fig)
    numerical_scores = comparison(pd.DataFrame(exact(base, sim.time, False)), sim.observations(base))
    residual_table = pd.DataFrame({"time_sec": data.time_sec})
    for channel in CHANNELS:
        residual_table[channel+"_predicted"] = pred[channel]
        residual_table[channel+"_residual"] = data[channel]-pred[channel]
    tables = {"experiment": data, "calibrated_parameters": parameter_table(fitted, "calibration"),
              "simulation_parameters": parameter_table(base, "simulation"), "convergence": rows,
              "numerical_metrics": numerical_scores, "experimental_metrics": pd.concat([before, after]),
              "predictions_and_residuals": residual_table,
              "trajectory": pd.DataFrame({"time_sec": sim.time, **sim.observations(base), "phase": sim.phase}),
              "local_defects": local_defects(base, [240,120,60,30])}
    tables.update({"physics_"+k: v for k,v in relationships.items()})
    for name, frame in tables.items(): frame.to_csv(out / (name+".csv"), index=False)
    images = {p.stem: p.read_bytes() for p in out.glob("*.png")}
    bundle_report = {"data_source": "Seeded synthetic bench, not physical measurements", "calibration": info,
        "simulation_parameters": asdict(base), "simulation_switch_sec": sim.switch_time,
        "calibrated_target_95_percent_sec": exact_target_time(fitted, .95, False),
        "time_to_100_percent_sec": None, "full_charge_note": "CV full-charge equilibrium is asymptotic.",
        "physics_curvature_ratio": .4, "nonlinear_ocv_scope": "Illustration only; affine engine and fit."}
    (out / "presentation_bundle.zip").write_bytes(build_bundle(bundle_report, tables, images, root=out.parent))
    print(json.dumps({"fitted": asdict(fitted), "metrics": info["metrics"], "output": str(out)}, indent=2))


if __name__ == "__main__":
    main()
