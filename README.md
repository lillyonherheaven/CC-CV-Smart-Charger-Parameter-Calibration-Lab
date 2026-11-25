# CC/CV Smart Charger & Parameter Calibration Lab

A complete Math 3 battery-charging project: exact/numerical CC/CV dynamics, independent calculation tabs, physical relationship graphs, CSV overlays, calibration, solver convergence, residual diagnosis, 300-dpi ZIP export, and a bilingual English/Arabic slide script.

## Start

Python 3.11/3.12 recommended. In PowerShell from this directory:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m streamlit run app.py
```

If `py` is unavailable, use your Python executable for the first command. A prepared `.venv` can be used directly with the last command. On macOS/Linux use `python3` and `.venv/bin/python`.

## Deliverables

- [REPORT.md](REPORT.md): all four requested parts, full derivations, solver/event analysis, calibration mathematics, experiment protocol and safety.
- [PRESENTATION.md](PRESENTATION.md): 12-slide English/Arabic speaker guide, glossary, demo checklist and professor Q&A.
- `app.py` and `charger/`: complete runnable modular code.
- `outputs/`: generated synthetic data, fit diagnostics, comparison CSVs, 300-dpi PNG charts and `presentation_bundle.zip`.
- [VERIFICATION.md](VERIFICATION.md): actual checks and limitations.

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe generate_demo.py
```

The three calculation tabs have independent settings and submit buttons: Section 1 simulates, Section 2 compares numerical methods, and Section 3 fits experimental/sample data. The physics panel has its own controls. Calibration in Section 3 does not change another section. Match inputs explicitly before comparing results.

The sample is synthetic and independent of slider changes. Leave termination **off** when fitting it. Use **Auto-calibrate** in Section 3. For real data enter the actual charger settings in that section first. CSV columns: `time_sec,voltage_v,current_a,soc_est`; at least one measured channel is required. SoC is a fraction, not a percentage.

Physics plots show +R slope for inward charging current and −R for outward discharge current, linear CC/rate laws, affine and illustrative curved OCV, exponential current taper and its semilog form. Curved OCV is explicitly an illustration; engine/calibration use affine OCV. Regulated CV approaches its full equilibrium asymptotically; practical completion uses the current cutoff

The export tab's single ZIP button packages summaries (TXT/Markdown/JSON), parameter and error CSVs, trajectory/relationship tables, all available 300-dpi figures, and allowlisted source/report/presentation files. Apply each form before downloading. For an offline example open `outputs/presentation_bundle.zip`. The source ZIP excludes the virtual environment.

This is an educational isothermal affine-OCV model, not battery-control software. Use a dedicated compatible charger and supervised laboratory procedure for physical measurements. The interface does not control hardware.
