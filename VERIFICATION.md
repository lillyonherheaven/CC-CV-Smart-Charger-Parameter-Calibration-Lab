# Verification and practical limits

Verified on Windows with Python 3.12.14. Installed versions are recorded in `requirements-lock.txt`; the project-local `.venv` contains the dependencies used for verification.

## Checks

`python -m unittest discover -s tests -v` runs 17 checks:

- Exact CC solutions for Euler, Heun and RK4.
- Continuity of state/current/terminal voltage at the ideal CC/CV event.
- Event splitting and the grid-delayed switching-lag bound.
- Approximately first-, second- and fourth-order convergence on a smooth CV interval.
- Numerical cutoff-event timing, state holding after termination and target reachability.
- Starting in CV or already below the current cutoff.
- Visible overshoot and negative current for an unstable Euler run, without state clipping.
- Noise-free parameter recovery and seeded noisy recovery.
- Nonidentifiability from constant CV voltage alone.
- CSV units, missing-channel support, duplicate-time rejection and other input checks.
- Final horizon handling and invalid model settings.
- Streamlit initial rendering, calibration, independence of simulation/convergence/fit settings, local fit invalidation, and no-overlay mode.
- Invalid inputs in one section leave the other sections available.
- Charging/discharging V–I slopes, rate-law slope, monotone nonlinear OCV illustration and exponential taper slope.
- Isolated one-step defect orders near 2, 3 and 5.
- Actual downloaded ZIP entries, summaries/CSV/source inclusion, standards-compliant JSON and 300-dpi PNG metadata.

The Streamlit checks execute the actual app through `streamlit.testing.v1.AppTest` and inspect the actual downloadable bytes. They do not substitute for testing a particular browser or real hardware. The synthetic generator creates the offline example bundle and charts; the generated scientific figures are visually inspected for labels and layout.

## Scientific limits

No physical cell experiment was conducted. Supplied sample measurements are explicitly synthetic. No device is controlled. Calibration metrics are in-sample. The affine OCV, constant temperature/resistance/capacity and absence of polarization limit real-cell accuracy. Consult Part 4 of `REPORT.md` before any supervised experiment.

The nonlinear OCV graph is a separate monotone illustration with matching endpoints, not a nonlinear engine or a measured cell curve. Charging voltage versus inward current has slope +R; the plotted −R relation uses outward discharge current at fixed SoC. No finite exact 100%-equilibrium time is asserted for regulated CV.

Extreme unstable steps are refused once the state diverges beyond a large numerical threshold. Moderate unstable results remain visible for teaching. CV termination bisection assumes a sensible monotone numerical step; inspect unstable schemes with termination off. The convergence study disables termination so that the smooth-method comparison is not dominated by an OFF-output discontinuity.

## Reproduce

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe generate_demo.py
.\.venv\Scripts\python.exe -m streamlit run app.py
```

For a fresh environment use `requirements.txt`, or `requirements-lock.txt` for the exact tested package versions. The ZIP excludes the environment; install dependencies before running the extracted project.
