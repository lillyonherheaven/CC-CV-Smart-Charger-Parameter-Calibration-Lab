"""Safe, inspectable export of results and a fixed allowlist of project sources."""
from dataclasses import asdict
from pathlib import Path
import io
import json
import zipfile
import numpy as np
import pandas as pd


def json_safe(value):
    """Use JSON null for missing table values; never emit nonstandard NaN."""
    if isinstance(value, dict):
        return {str(k): json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_safe(v) for v in value]
    if isinstance(value, np.ndarray):
        return json_safe(value.tolist())
    if isinstance(value, (float, np.floating)):
        return float(value) if np.isfinite(value) else None
    if isinstance(value, np.integer):
        return int(value)
    return value


def parameter_table(p, section):
    units = {"capacity_ah": "Ah", "current_a": "A", "resistance_ohm": "ohm", "eta": "fraction",
             "ocv_empty_v": "V", "ocv_slope_v": "V/SoC fraction", "vmax_v": "V", "soc0": "fraction",
             "cutoff_a": "A", "mode": "categorical"}
    rows = [{"section": section, "parameter": k, "value": v, "unit": units[k]} for k, v in asdict(p).items()]
    rows.append({"section": section, "parameter": "tau_sec", "value": p.tau, "unit": "s"})
    return pd.DataFrame(rows)


def source_paths(root):
    """Never include uploaded files, credentials, environment or git metadata."""
    root = Path(root)
    names = ["app.py", "generate_demo.py", "requirements.txt", "requirements-lock.txt", "run_lab.ps1",
             "README.md", "REPORT.md", "PRESENTATION.md", "VERIFICATION.md"]
    files = [root/n for n in names if (root/n).is_file()]
    for folder in ("charger", "tests"):
        files.extend(sorted((root/folder).glob("*.py")))
    return files


def build_bundle(report, tables, figures, root=None):
    """tables: {relative_name: DataFrame}; figures: {relative_name: PNG bytes}."""
    payload = json_safe(report)
    encoded = json.dumps(payload, indent=2, ensure_ascii=False, allow_nan=False)
    summary = ("# CC/CV Laboratory Diagnostic Summary\n\n"
        "Each section has independent inputs; inspect its own settings before comparing results.\n\n"
        "Synthetic data are not physical validation. Calibration metrics are in-sample.\n"
        "The affine OCV model drives the engine and fit; curved OCV is a separate physics illustration.\n"
        "At fixed SoC, charging-current slope is +R; discharge-current slope is −R.\n"
        "Full CV equilibrium is asymptotic; practical completion uses a current cutoff.\n\n"
        "Complete machine-readable settings are in `diagnostics.json`; numeric tables are in `tables/`.\n\n")
    sections = payload.get("sections", {})
    sim = sections.get("simulation", {})
    if sim:
        summary += "## Simulation event times\n\n| Quantity | Seconds |\n|---|---:|\n"
        for key in ("exact_switch_sec", "detected_switch_sec", "exact_target_sec", "numerical_target_sec", "exact_stop_sec", "detected_stop_sec", "time_to_100_percent_sec"):
            value = sim.get(key)
            summary += f"| {key} | {value if value is not None else 'Not reached / N/A'} |\n"
        summary += "\n" + sim.get("full_charge_note", "") + "\n\n"
    fit = sections.get("calibration", {}).get("fit") or payload.get("calibration")
    if fit:
        summary += "## Calibration\n\n"
        summary += "Status: " + str(fit.get("message", "Recorded in diagnostics.json")) + "\n\n"
        for warning in fit.get("warnings", []): summary += "- " + warning + "\n"
    for name in ("calibrated_parameters", "numerical_metrics", "experimental_metrics"):
        if name not in tables: continue
        frame = tables[name]
        summary += "\n## " + name.replace("_", " ").title() + "\n\n"
        columns = [c for c in ("parameter", "value", "unit", "channel", "n", "MAE", "RMSE", "max_error", "fit") if c in frame]
        summary += "| " + " | ".join(columns) + " |\n|" + "|".join("---" for _ in columns) + "|\n"
        for _, row in frame.iterrows():
            cells = []
            for c in columns:
                value = row[c]
                cells.append(f"{value:.6g}" if isinstance(value, (float, np.floating)) else str(value))
            summary += "| " + " | ".join(cells) + " |\n"
    if payload.get("errors"):
        summary += "\n## Unavailable sections\n\n" + json.dumps(payload["errors"], ensure_ascii=False) + "\n"
    summary += "\n## Figures\n\n"
    for name in figures:
        summary += f"![{name.replace('_', ' ')}](figures/{name}.png)\n\n"
    manifest = {"reports": ["diagnostics.json", "summary.md", "summary.txt"],
                "tables": sorted(tables), "figures": sorted(figures), "figure_resolution_dpi": 300,
                "source_included": root is not None}
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("diagnostics.json", encoded)
        archive.writestr("summary.md", summary)
        archive.writestr("summary.txt", summary)
        archive.writestr("manifest.json", json.dumps(manifest, indent=2))
        for name, table in tables.items():
            archive.writestr("tables/" + name + ".csv", table.to_csv(index=False))
        for name, image in figures.items():
            archive.writestr("figures/" + name + ".png", image)
        if root is not None:
            for path in source_paths(root):
                archive.write(path, "source/" + path.relative_to(root).as_posix())
            # Preserve the report's relative image links in the transferred source.
            aliases = {"convergence_and_crossover": "convergence", "experimental_overlay": "calibrated_overlay"}
            for name, image in figures.items():
                archive.writestr("source/outputs/" + aliases.get(name, name) + ".png", image)
    return output.getvalue()
