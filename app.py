"""Independent teaching labs. Run: python -m streamlit run app.py."""
from dataclasses import asdict
from pathlib import Path
import hashlib
import json
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.colors import to_hex, to_rgba
import streamlit as st
from charger.model import Parameters, exact, exact_events, exact_target_time
from charger.solvers import solve, target_time, convergence
from charger.data import sample_data, load_csv, CHANNELS
from charger.analysis import comparison, calibrate, local_defects
from charger.plots import charging_figure, residual_figure, convergence_figure, physics_figure, png_bytes
from charger.export import build_bundle, parameter_table, json_safe

ROOT = Path(__file__).resolve().parent
st.set_page_config(page_title="CC/CV Calibration Lab", page_icon="🔋", layout="wide")

# Presentation only. These styles never read or change numerical state.
UI_STYLES = r"""
<style>
:root {
  --lab-bg: #0F1117; --lab-card: #181B24; --lab-cream: #F2EDE4;
  --lab-muted: #C7BEB2; --lab-gold: #E3A869; --lab-amber: #D9A05B;
  --lab-crimson: #9E2A2B; --lab-coral: #C85A53;
  --lab-border: rgba(217,160,91,.16);
}
.stApp { background: var(--lab-bg); color: var(--lab-cream); }
[data-testid="stAppViewContainer"] { isolation: isolate; }
[data-testid="stAppViewContainer"]::before,
[data-testid="stAppViewContainer"]::after {
  content: ""; position: fixed; pointer-events: none; z-index: -1;
}
[data-testid="stAppViewContainer"]::before {
  inset: 0;
  background-image: linear-gradient(rgba(217,160,91,.025) 1px, transparent 1px),
    linear-gradient(90deg, rgba(217,160,91,.025) 1px, transparent 1px);
  background-size: 44px 44px;
  mask-image: linear-gradient(#000, rgba(0,0,0,.22));
}
[data-testid="stAppViewContainer"]::after {
  inset: -20%;
  background: radial-gradient(ellipse at 12% 12%, rgba(158,42,43,.19), transparent 35%),
    radial-gradient(ellipse at 88% 32%, rgba(217,160,91,.09), transparent 32%),
    radial-gradient(ellipse at 50% 90%, rgba(158,42,43,.09), transparent 34%);
  animation: ambient-drift 26s ease-in-out infinite alternate;
}
[data-testid="stHeader"] { background: rgba(15,17,23,.82); backdrop-filter: blur(12px); }
[data-testid="stMainBlockContainer"] { max-width: 1550px; padding-top: 2.5rem; padding-bottom: 4rem; }
h1, h2, h3 { color: var(--lab-cream); letter-spacing: -.035em; }
h2 { font-size: 1.65rem !important; margin-top: .5rem; }
h3 { font-size: 1.12rem !important; }
p, label, [data-testid="stWidgetLabel"] { color: var(--lab-cream); }
[data-testid="stCaptionContainer"], [data-testid="stCaptionContainer"] p {
  color: var(--lab-muted); line-height: 1.65;
}
a { color: var(--lab-gold); }
::selection { background: rgba(200,90,83,.4); color: #F2EDE4; }

/* The hero is decorative; all figures and calculated values remain native. */
.lab-hero {
  position: relative; display: grid; grid-template-columns: 1.15fr 1fr;
  align-items: center; gap: 1.7rem; overflow: hidden; padding: 2.4rem 2.6rem;
  margin: .2rem 0 1.25rem; border: 1px solid rgba(217,160,91,.23);
  border-radius: 24px; background: linear-gradient(125deg, #20191E, #181B24 58%, #171921);
  box-shadow: 0 22px 70px rgba(0,0,0,.28); animation: reveal .7s ease-out both;
}
.lab-hero::before {
  content: ""; position: absolute; top: 0; left: 2.6rem; width: 110px; height: 2px;
  background: linear-gradient(90deg, #9E2A2B, #E3A869); pointer-events: none;
}
.lab-hero-copy, .lab-hero-art { position: relative; z-index: 1; }
.lab-eyebrow {
  display: flex; align-items: center; gap: .6rem; color: var(--lab-gold);
  font-size: .69rem; font-weight: 650; letter-spacing: .19em; text-transform: uppercase;
}
.lab-status-dot { width: 6px; height: 6px; border-radius: 50%; background: var(--lab-gold); box-shadow: 0 0 12px #D9A05B55; }
.lab-hero-title { color: var(--lab-cream); letter-spacing: -.035em; font-size: clamp(2rem, 3.05vw, 3.1rem); font-weight: 650; line-height: 1.09; padding: .85rem 0 .5rem; margin: 0; }
.lab-hero-title > span { display: block; color: var(--lab-gold); font-size: .72em; margin-top: .35rem; font-weight: 450; }
.lab-hero-description { max-width: 37rem; font-size: .94rem; color: var(--lab-muted); line-height: 1.7; margin: .5rem 0 1.2rem; }
.lab-tags { display: flex; flex-wrap: wrap; gap: .45rem; }
.lab-tags span { color: #D8C7B1; font-size: .67rem; letter-spacing: .025em; border: 1px solid #D9A05B26; border-radius: 6px; padding: .32rem .55rem; background: #D9A05B08; }
.lab-hero-art svg { display: block; width: 100%; height: auto; max-height: 245px; overflow: visible; }
.lab-hero-art { min-width: 0; }
.lab-energy { stroke-dasharray: 7 11; animation: energy-flow 5s linear infinite; }
.lab-charge-bar { transform-box: fill-box; transform-origin: center; animation: cell-breathe 6s ease-in-out infinite; }
.lab-charge-bar:nth-of-type(2) { animation-delay: .45s; }
.lab-charge-bar:nth-of-type(3) { animation-delay: .9s; }
.lab-charge-bar:nth-of-type(4) { animation-delay: 1.35s; }
.lab-curve-glow { animation: curve-breathe 7s ease-in-out infinite; }
.lab-crosshair { transform-origin: 390px 125px; animation: calibrate-drift 16s ease-in-out infinite; }

/* Native Streamlit components retain their focus, keyboard and form semantics. */
[data-testid="stForm"] {
  border: 1px solid var(--lab-border); border-radius: 18px; padding: 1.5rem;
  background: linear-gradient(145deg, rgba(29,31,41,.95), rgba(24,27,36,.91));
  box-shadow: 0 12px 34px #00000020; animation: reveal .5s ease-out both;
  transition: border-color .25s, box-shadow .25s;
}
[data-testid="stForm"]:hover { border-color: #D9A05B3D; box-shadow: 0 14px 40px #00000030; }
[data-testid="stMetric"] {
  padding: 1.15rem 1.25rem; border: 1px solid var(--lab-border); border-radius: 14px;
  background: linear-gradient(145deg, #211D23, #181B24); min-height: 112px;
  box-shadow: 0 8px 20px #00000016; transition: transform .25s, border-color .25s;
  animation: reveal .55s ease-out both;
}
[data-testid="stMetric"]:hover { transform: translateY(-2px); border-color: #D9A05B55; }
[data-testid="stMetricLabel"] p { color: var(--lab-muted); font-size: .76rem; letter-spacing: .02em; }
[data-testid="stMetricValue"] { color: var(--lab-gold); font-variant-numeric: tabular-nums; }
[data-testid="stMetricValue"] > div { font-size: clamp(1.1rem, 1.8vw, 1.8rem); }
:is([data-baseweb="tab-list"], [role="tablist"]) {
  gap: .35rem; padding: .45rem; background: rgba(24,27,36,.92);
  border: 1px solid var(--lab-border); border-radius: 13px; margin: .5rem 0 1.1rem;
  overflow-x: auto; scrollbar-width: thin;
}
:is([data-baseweb="tab"], [role="tab"]) {
  color: var(--lab-muted); padding: .65rem .95rem; border-radius: 8px; height: auto;
  transition: background .22s, color .22s; white-space: nowrap;
}
:is([data-baseweb="tab"], [role="tab"]) p { font-size: .8rem; color: inherit; }
:is([data-baseweb="tab"], [role="tab"]):hover { color: var(--lab-cream); background: #D9A05B0B; }
:is([data-baseweb="tab"], [role="tab"])[aria-selected="true"] { background: linear-gradient(110deg, #9E2A2B3D, #C85A531A); color: #F2D3AE; }
[data-testid="stTab"] { border-bottom: 0 !important; }
[data-baseweb="tab-highlight"], [data-baseweb="tab-border"] { display: none; }
:is([data-baseweb="tab-panel"], [role="tabpanel"]) { animation: reveal .4s ease-out both; }
[data-testid="stNumberInput"] [data-baseweb="input"],
[data-baseweb="select"] > div, [data-baseweb="input"],
[data-testid="stNumberInputContainer"], [data-testid="stSelectbox"] [role="group"],
[data-testid="stMultiSelect"] [role="group"] {
  background-color: #11141C !important; border-color: #C7BEB21F !important;
  border-radius: 9px !important; transition: border-color .22s, box-shadow .22s;
}
[data-baseweb="input"]:focus-within, [data-baseweb="select"]:focus-within > div,
[data-testid="stNumberInputContainer"]:focus-within, [data-testid="stSelectbox"] [role="group"]:focus-within,
[data-testid="stMultiSelect"] [role="group"]:focus-within {
  border-color: #D9A05B99 !important; box-shadow: 0 0 0 2px #D9A05B12 !important;
}
[data-baseweb="input"] input { color: var(--lab-cream) !important; font-variant-numeric: tabular-nums; }
[data-testid="stNumberInputField"], [role="combobox"] { color: var(--lab-cream) !important; font-variant-numeric: tabular-nums; background: transparent; }
[data-testid="stNumberInput"] button { color: var(--lab-muted); background: #181B24; }
[data-baseweb="popover"] [role="listbox"], [data-baseweb="menu"], [role="listbox"] {
  background: #181B24 !important; color: var(--lab-cream) !important; border: 1px solid var(--lab-border);
}
[data-baseweb="tag"] { background: #9E2A2B35 !important; color: var(--lab-cream) !important; border: 1px solid #C85A5345; }
[data-testid="stSlider"] [role="slider"] { background: var(--lab-gold); box-shadow: 0 0 0 4px #D9A05B12; }
[data-testid="stButton"] button, [data-testid="stFormSubmitButton"] button,
[data-testid="stDownloadButton"] button {
  border: 1px solid #C85A5359; background: linear-gradient(135deg, #7D2429, #9E2A2B);
  color: var(--lab-cream); border-radius: 9px; padding: .6rem 1.1rem;
  box-shadow: 0 4px 14px #00000022; font-weight: 600;
  transition: transform .2s, background .2s, border-color .2s, box-shadow .2s;
}
[data-testid="stFormSubmitButton"] { margin-top: .5rem; }
[data-testid="stButton"] button:hover:not(:disabled),
[data-testid="stFormSubmitButton"] button:hover:not(:disabled),
[data-testid="stDownloadButton"] button:hover:not(:disabled) {
  transform: translateY(-1px); border-color: #E3A869B0; color: #FFF3DF;
  background: linear-gradient(135deg, #9E2A2B, #AF413C); box-shadow: 0 6px 20px #9E2A2B29;
}
button:focus-visible, [role="tab"]:focus-visible { outline: 2px solid var(--lab-gold) !important; outline-offset: 3px; }
button:disabled { opacity: .45; }
[data-testid="stDataFrame"], [data-testid="stJson"], [data-testid="stExpander"] {
  border: 1px solid var(--lab-border); border-radius: 12px; overflow: hidden;
  background: #181B24; box-shadow: 0 8px 24px #00000015;
}
[data-testid="stImage"] {
  border: 1px solid var(--lab-border); border-radius: 16px; overflow: hidden;
  background: #181B24; padding: .55rem; margin: .6rem 0; box-shadow: 0 12px 32px #00000020;
}
[data-testid="stImage"] img { border-radius: 10px; }
[data-testid="stImageCaption"] { color: var(--lab-muted); }
[data-testid="stAlert"] { border-radius: 12px; overflow: hidden; }
[data-testid="stAlert"] > div {
  background: rgba(217,160,91,.055) !important; border: 1px solid #D9A05B26 !important;
  color: var(--lab-muted) !important; border-radius: 12px;
}
[data-testid="stAlert"] p { color: var(--lab-muted); font-size: .87rem; }
[data-testid="stFileUploaderDropzone"] { background: #181B24; border: 1px dashed #D9A05B55; border-radius: 12px; }
[data-testid="stLatex"] { color: #E4C9A8; }
code { color: #E3A869; background: #211D23; border-radius: 4px; }

@keyframes ambient-drift { from { transform: translate3d(-1%, -1%, 0) scale(1); opacity: .7; } to { transform: translate3d(2%, 2%, 0) scale(1.05); opacity: 1; } }
@keyframes energy-flow { to { stroke-dashoffset: -108; } }
@keyframes cell-breathe { 0%,100% { opacity: .45; } 50% { opacity: .95; } }
@keyframes curve-breathe { 0%,100% { opacity: .35; } 50% { opacity: .75; } }
@keyframes calibrate-drift { 0%,100% { transform: translateY(-2px); opacity: .55; } 50% { transform: translateY(2px); opacity: .9; } }
@keyframes reveal { from { opacity: 0; transform: translateY(5px); } to { opacity: 1; transform: translateY(0); } }
@media (max-width: 850px) {
  .lab-hero { grid-template-columns: 1fr; padding: 1.8rem; gap: 1rem; }
  .lab-hero-art svg { max-height: 200px; }
  [data-testid="stMainBlockContainer"] { padding-top: 1.5rem; }
  [data-testid="stForm"] { padding: 1rem; }
}
@media (prefers-reduced-motion: reduce) {
  [data-testid="stAppViewContainer"]::after,
  .lab-hero, .lab-energy, .lab-charge-bar, .lab-curve-glow, .lab-crosshair,
  [data-testid="stForm"], [data-testid="stMetric"], [data-baseweb="tab-panel"], [role="tabpanel"] {
    animation: none !important; transform: none !important;
  }
  .lab-charge-bar { opacity: .8; }
  .lab-curve-glow { opacity: .5; }
  [data-testid="stForm"], [data-testid="stMetric"], [data-baseweb="tab"], [role="tab"],
  [data-testid="stButton"] button, [data-testid="stFormSubmitButton"] button,
  [data-testid="stDownloadButton"] button { transition: none !important; transform: none !important; }
}
</style>
"""

HERO_HEADER = r"""
<section class="lab-hero" aria-label="CC/CV Smart Charger and Parameter Calibration Lab">
<div class="lab-hero-copy">
  <div class="lab-eyebrow"><span class="lab-status-dot"></span> Math 3 / Differential Equations</div>
  <div class="lab-hero-title" role="heading" aria-level="1">CC/CV Smart Charger<span>&amp; Parameter Calibration Lab</span></div>
  <p class="lab-hero-description">Explore the charge. Understand the transition.<br>Precision simulation, numerical analysis, and experimental calibration.</p>
  <div class="lab-tags"><span>CC → CV</span><span>Euler · Heun · RK4</span><span>Independent calculation sections</span><span>No hardware control</span></div>
</div>
<div class="lab-hero-art" aria-hidden="true">
<svg viewBox="0 0 540 270" xmlns="http://www.w3.org/2000/svg" focusable="false">
<defs>
  <linearGradient id="labCell" x1="0" y1="0" x2="1" y2="1"><stop stop-color="#2A242B"/><stop offset="1" stop-color="#171A23"/></linearGradient>
  <linearGradient id="labEnergy" x1="0" y1="0" x2="0" y2="1"><stop stop-color="#E3A869"/><stop offset="1" stop-color="#9E2A2B"/></linearGradient>
  <linearGradient id="labCurve" x1="0" y1="0" x2="1" y2="0"><stop stop-color="#C85A53"/><stop offset="1" stop-color="#E3A869"/></linearGradient>
  <pattern id="labSvgGrid" width="25" height="25" patternUnits="userSpaceOnUse"><path d="M25 0H0V25" fill="none" stroke="#D9A05B" stroke-opacity=".07" stroke-width=".6"/></pattern>
</defs>
<rect x="2" y="2" width="536" height="266" rx="18" fill="url(#labSvgGrid)"/>
<path d="M13 137H58M194 137H236M236 137V197H274" stroke="#D9A05B" stroke-opacity=".2" fill="none"/>
<path class="lab-energy" d="M13 137H58M194 137H236M236 137V197H274" stroke="#E3A869" stroke-width="1.5" fill="none"/>
<g transform="translate(65 51)">
  <rect x="44" y="0" width="39" height="12" rx="4" fill="#C7BEB2" fill-opacity=".4"/>
  <rect x="0" y="10" width="127" height="173" rx="20" fill="url(#labCell)" stroke="#D9A05B" stroke-opacity=".6" stroke-width="1.3"/>
  <rect x="9" y="19" width="109" height="155" rx="14" fill="none" stroke="#D9A05B" stroke-opacity=".1"/>
  <g fill="url(#labEnergy)">
    <rect class="lab-charge-bar" x="24" y="135" width="79" height="21" rx="4"/>
    <rect class="lab-charge-bar" x="24" y="107" width="79" height="21" rx="4"/>
    <rect class="lab-charge-bar" x="24" y="79" width="79" height="21" rx="4"/>
    <rect class="lab-charge-bar" x="24" y="51" width="79" height="21" rx="4"/>
  </g>
  <path d="M69 63L52 92H65L58 115L79 84H65Z" fill="#F2EDE4" opacity=".9"/>
</g>
<g font-family="sans-serif" font-size="10" letter-spacing="1.6" fill="#C7BEB2">
  <text x="83" y="255">SMART CELL</text><text x="284" y="42" fill="#E3A869">CHARGE PROFILE</text>
  <text x="289" y="244">CC</text><text x="451" y="244">CV</text>
</g>
<path d="M270 61V219H513" fill="none" stroke="#C7BEB2" stroke-opacity=".3"/>
<path d="M270 166H513M270 112H513M270 61H513" fill="none" stroke="#C7BEB2" stroke-opacity=".08" stroke-dasharray="3 5"/>
<path d="M390 65V220" fill="none" stroke="#D9A05B" stroke-opacity=".35" stroke-dasharray="3 5"/>
<path d="M282 204L390 88C416 68 462 68 504 68" fill="none" stroke="url(#labCurve)" stroke-width="2.6" stroke-linecap="round"/>
<path class="lab-curve-glow" d="M282 204L390 88C416 68 462 68 504 68" fill="none" stroke="#E3A869" stroke-width="8" stroke-opacity=".12"/>
<path d="M282 122H390C418 124 429 185 504 200" fill="none" stroke="#C85A53" stroke-width="1.8" stroke-dasharray="4 4" opacity=".7"/>
<circle cx="390" cy="88" r="4" fill="#E3A869"/><circle cx="390" cy="88" r="10" fill="none" stroke="#E3A869" stroke-opacity=".25"/>
<g class="lab-crosshair" fill="none" stroke="#E3A869" stroke-width=".8">
  <circle cx="463" cy="158" r="19" stroke-opacity=".35"/><circle cx="463" cy="158" r="11" stroke-opacity=".55"/>
  <path d="M437 158H489M463 132V184" stroke-opacity=".5"/><circle cx="463" cy="158" r="2" fill="#E3A869"/>
</g>
</svg>
</div>
</section>
"""

# Keep CSS separate, and use raw Markdown HTML to preserve inline SVG. The
# accessible heading avoids Markdown's automatic heading/anchor rewrites.
st.html(UI_STYLES)
st.markdown(HERO_HEADER, unsafe_allow_html=True)
st.info("Each tab has its own inputs and Calculate button. Calibration changes only Section 3. "
        "Match settings explicitly when comparing sections. ZIP export records every section's settings.")


def physical_inputs(prefix):
    """Namespaced widget keys prevent any tab from changing another tab's model."""
    l, r = st.columns(2)
    with l:
        mode = st.selectbox("Charging mode", ["CC/CV", "CC"], key=prefix+"mode")
        q = st.number_input("Capacity Q (Ah)", .1, 10., 2., .1, key=prefix+"q")
        current = st.number_input("CC current (A)", .05, 5., 1., .05, key=prefix+"current")
        resistance = st.number_input("Internal resistance (Ω)", .005, 1., .15, .005, format="%.3f", key=prefix+"r")
        soc0 = st.slider("Initial SoC (fraction)", 0., .99, .2, .01, key=prefix+"soc0")
    with r:
        a = st.number_input("OCV intercept a (V)", 2.5, 3.5, 3., .05, key=prefix+"a")
        b = st.number_input("OCV slope b (V / SoC fraction)", .5, 1.8, 1.2, .05, key=prefix+"b")
        vmax = st.number_input("CV voltage Vmax (V)", 3.5, 4.35, 4.2, .01, key=prefix+"vmax")
        cutoff = st.number_input("Termination current (A)", .001, 1., .1, .01, format="%.3f", key=prefix+"cutoff")
        eta = st.slider("Coulombic efficiency", .90, 1., .995, .001, key=prefix+"eta")
    return Parameters(q, current, resistance, eta, a, b, vmax, soc0, cutoff, mode)


def style_figure(fig):
    """Recolor existing artists only: preserve data, scales, labels and limits.

    Applied at the PNG boundary, so charger/ stays byte-for-byte unchanged and
    every app/export chart shares the same warm dark treatment.
    """
    palette = {
        "#167d9a": "#E3A869", "#a64d79": "#C85A53", "#dd813b": "#D78374",
        "#1f77b4": "#E3A869", "#ff7f0e": "#D78374", "#2ca02c": "#C7C4A2",
        "#d62728": "#C85A53", "#9467bd": "#B994A5", "#8c564b": "#BDA88C",
        "#e377c2": "#D8A6A0", "#7f7f7f": "#A59C91", "#bcbd22": "#D4C58F",
        "#17becf": "#DBCCB5", "#808080": "#90877C", "#000000": "#C7BEB2",
    }

    def warm(color):
        try:
            rgba = to_rgba(color)
            return to_rgba(palette.get(to_hex(rgba).lower(), to_hex(rgba)), rgba[3])
        except (ValueError, TypeError):
            return color

    def recolor(artist):
        if hasattr(artist, "get_color") and hasattr(artist, "set_color"):
            artist.set_color(warm(artist.get_color()))
        if hasattr(artist, "get_facecolors"):
            colors = artist.get_facecolors()
            if len(colors): artist.set_facecolors([warm(c) for c in colors])
        if hasattr(artist, "get_edgecolors"):
            colors = artist.get_edgecolors()
            if len(colors): artist.set_edgecolors([warm(c) for c in colors])

    fig.set_facecolor("#181B24")
    fig.set_edgecolor("#181B24")
    for text in fig.texts:
        text.set_color("#F2EDE4")
    for ax in fig.axes:
        ax.set_facecolor("#181B24")
        ax.tick_params(axis="both", which="both", colors="#C7BEB2", labelsize=9)
        ax.xaxis.label.set_color("#F2EDE4")
        ax.yaxis.label.set_color("#F2EDE4")
        ax.xaxis.get_offset_text().set_color("#C7BEB2")
        ax.yaxis.get_offset_text().set_color("#C7BEB2")
        for title in (ax.title, ax._left_title, ax._right_title): title.set_color("#F2EDE4")
        for spine in ax.spines.values():
            spine.set_color("#6D6256"); spine.set_alpha(.55)
        for line in ax.get_xgridlines() + ax.get_ygridlines():
            line.set_color("#C7BEB2"); line.set_alpha(.12); line.set_linewidth(.6)
        for artist in list(ax.lines) + list(ax.collections): recolor(artist)
        for text in ax.texts: text.set_color("#C7BEB2")
        legend = ax.get_legend()
        if legend is not None:
            legend.get_frame().set_facecolor("#20232D")
            legend.get_frame().set_edgecolor("#6D6256")
            legend.get_frame().set_alpha(.94)
            for text in legend.get_texts(): text.set_color("#F2EDE4")
            legend.get_title().set_color("#F2EDE4")
            for artist in legend.get_lines(): recolor(artist)
            for artist in getattr(legend, "legend_handles", []): recolor(artist)
    return fig


def freeze_plot(fig):
    try: return png_bytes(style_figure(fig), dpi=300)
    finally: plt.close(fig)


@st.cache_data(max_entries=12, show_spinner=False)
def simulation_result(p, duration, dt, method, policy, terminate, target):
    p.validate()
    sim = solve(p, duration, dt, method, policy, terminate)
    obs = sim.observations(p)
    ts, stop = exact_events(p, terminate)
    full = exact_target_time(p, 1., terminate)
    result = {"parameters": asdict(p), "duration_sec": duration, "dt_sec": dt,
              "method": method, "policy": policy, "termination": terminate,
              "tau_sec": p.tau, "exact_switch_sec": ts, "detected_switch_sec": sim.switch_time,
              "exact_stop_sec": stop, "detected_stop_sec": sim.stop_time,
              "target_soc": target, "exact_target_sec": exact_target_time(p, target, terminate),
            "numerical_target_sec": target_time(sim, target), "time_to_100_percent_sec": full,
              "full_charge_note": "100% is asymptotic/unreachable in regulated CV; practical completion uses current cutoff." if full is None else "Unregulated CC reaches 100% mathematically; hardware safety limits still apply."}
    trajectory = pd.DataFrame({"time_sec": sim.time, **obs, "phase": sim.phase})
    errors = comparison(pd.DataFrame(exact(p, sim.time, terminate)), obs)
    return result, trajectory, errors, freeze_plot(charging_figure(p, duration, sim=sim, terminate=terminate))


@st.cache_data(max_entries=12, show_spinner=False)
def numerical_result(p, duration, dt):
    p.validate()
    steps = [dt/4, dt/2, dt, dt*2]
    rows = pd.DataFrame(convergence(p, duration, steps, terminate=False))
    errors = []
    for method in ("Euler", "Heun", "RK4"):
        sim = solve(p, duration, dt, method, "Event-aware", terminate=False)
        errors.append(comparison(pd.DataFrame(exact(p, sim.time, False)), sim.observations(p)).assign(method=method))
    return rows, pd.concat(errors, ignore_index=True), local_defects(p, steps), freeze_plot(convergence_figure(rows))


@st.cache_data(max_entries=12, show_spinner=False)
def calibration_figures(base, fitted, frame, terminate, label):
    duration = max(float(frame.time_sec.max()), 60.)
    pred = exact(fitted, frame.time_sec.to_numpy(), terminate)
    overlay = freeze_plot(charging_figure(fitted, duration, data=frame, terminate=terminate,
                                        data_label=label, baseline=base))
    residual = freeze_plot(residual_figure(frame, pred))
    table = pd.DataFrame({"time_sec": frame.time_sec})
    for c in CHANNELS:
        table[c+"_predicted"] = pred[c]
        if c in frame: table[c+"_residual"] = frame[c]-pred[c]
    return overlay, residual, table


@st.cache_data(max_entries=12, show_spinner=False)
def physics_result(p, fixed_soc, curvature):
    fig, tables = physics_figure(p, fixed_soc, curvature)
    return freeze_plot(fig), tables


def time_text(value):
    return "Not reached / N/A" if value is None else f"{value:.2f} s"


report = {"model": "Affine OCV, isothermal, no polarization", "sections": {}, "errors": {},
          "notes": ["Sections use independent physical inputs.", "Synthetic data are not physical validation.",
                    "Calibration metrics are in-sample.", "Curved OCV is a separate illustration, not the engine's law."]}
tables, figures = {}, {}
tabs = st.tabs(["1 · CC/CV Simulation Engine", "2 · Numerical Solver & Convergence Lab",
                "3 · Experimental Overlay & Calibration", "Physics Relationships", "One-click ZIP Export"])

with tabs[0]:
    st.header("Section 1 — CC/CV Simulation Engine")
    with st.form("simulation_form"):
        p = physical_inputs("sim_")
        c1, c2, c3 = st.columns(3)
        with c1:
            method = st.selectbox("Solver", ["RK4", "Heun", "Euler"], key="sim_method")
            policy = st.selectbox("Switch handling", ["Event-aware", "Grid-delayed"], key="sim_policy")
        with c2:
            dt = st.number_input("Step Δt (seconds)", 1., 3600., 60., 10., key="sim_dt")
            duration = st.number_input("Duration (seconds)", 60., 30000., 9000., 300., key="sim_duration")
        with c3:
            target = st.slider("Target SoC", .5, 1., .95, .01, key="sim_target")
            terminate = st.checkbox("Stop at termination current", value=False, key="sim_terminate")
        st.form_submit_button("Calculate simulation")
    try:
        result, trajectory, scores, figure = simulation_result(p, duration, dt, method, policy, terminate, target)
        cols = st.columns(4)
        for col, title, value in zip(cols, ["Exact CC → CV", "Detected CC → CV", "Numerical target time", "CV time constant"],
                                    [result["exact_switch_sec"], result["detected_switch_sec"], result["numerical_target_sec"], p.tau]):
            col.metric(title, time_text(value))
        st.write(f"Exact target: {time_text(result['exact_target_sec'])}. Exact practical termination: {time_text(result['exact_stop_sec'])}.")
        st.write("**Time to 100%:** " + time_text(result["time_to_100_percent_sec"]) + ". " + result["full_charge_note"])
        st.caption("Exact event times may lie beyond the plotted duration. Numerical target uses interpolation between nodes.")
        if p.mode == "CC": st.warning("Unregulated CC: interpret physically only before voltage or SoC limits are exceeded.")
        if dt/p.tau >= 1: st.warning("Δt/τ ≥ 1: inspect overshoot and unstable steps with termination off.")
        if (trajectory.soc_est > 1+1e-9).any() or (trajectory.soc_est < 0).any() or (trajectory.current_a < -1e-9).any():
            st.warning("Numerical trajectory left the physical domain. No state clipping was applied.")
        st.image(figure, caption="Exact and selected numerical time-domain charging curves")
        st.dataframe(scores, hide_index=True)
        result["numerical_metrics"] = scores.to_dict(orient="records")
        report["sections"]["simulation"] = result
        tables.update({"simulation_parameters": parameter_table(p, "simulation"), "trajectory": trajectory, "numerical_metrics": scores})
        figures["charging_curves"] = figure
    except ValueError as exc:
        st.error(str(exc)); report["errors"]["simulation"] = str(exc)

with tabs[1]:
    st.header("Section 2 — Numerical Solver & Convergence Lab")
    st.caption("Independent model and step-size controls. Termination is disabled to isolate solver order.")
    with st.form("numerical_form"):
        p_lab = physical_inputs("lab_")
        lab_dt = st.number_input("Base Δt (seconds)", 1., 1800., 60., 10., key="lab_dt")
        lab_duration = st.number_input("Study duration (seconds)", 60., 30000., 9000., 300., key="lab_duration")
        st.form_submit_button("Calculate convergence")
    try:
        rows, numerical_scores, defects, figure = numerical_result(p_lab, lab_duration, lab_dt)
        st.image(figure, caption="Error vs Δt: log-log, linear axes, and crossover timing lag")
        st.subheader("Global errors and crossover comparator"); st.dataframe(rows, hide_index=True)
        st.subheader("Live MAE, RMSE and maximum error — numerical vs exact"); st.dataframe(numerical_scores, hide_index=True)
        st.subheader("Isolated smooth-CV one-step defects"); st.dataframe(defects, hide_index=True)
        st.caption("One-step defects scale as h²/h³/h⁵; global state errors scale as h/h²/h⁴. CC is exact for all three. "
                   "Roundoff-level orders are omitted. The one-way latch prevents artificial mode chattering.")
        report["sections"]["numerical"] = {"parameters": asdict(p_lab), "duration_sec": lab_duration,
            "steps_sec": [lab_dt/4, lab_dt/2, lab_dt, lab_dt*2], "termination": False,
            "solver_metrics": numerical_scores.to_dict(orient="records")}
        tables.update({"numerical_lab_parameters": parameter_table(p_lab, "numerical_lab"), "convergence": rows,
                       "solver_metrics": numerical_scores, "local_defects": defects})
        figures["convergence_and_crossover"] = figure
    except ValueError as exc:
        st.error(str(exc)); report["errors"]["numerical"] = str(exc)

with tabs[2]:
    st.header("Section 3 — Experimental Overlay & Calibration")
    st.caption("Local model assumptions and fit results. Calibrating here leaves Sections 1 and 2 unchanged.")
    source = st.radio("Data source", ["Synthetic bench (not real measurements)", "Upload CSV", "No overlay"], key="fit_source")
    data = None
    if source.startswith("Synthetic"):
        data, truth = sample_data()
        st.caption("71 seeded synthetic samples; uninterrupted CV taper. Keep termination off.")
        with st.expander("Reveal synthetic ground truth"): st.json(asdict(truth))
    elif source == "Upload CSV":
        upload = st.file_uploader("CSV: time_sec, voltage_v, current_a, soc_est", type="csv", key="fit_upload")
        if upload is not None:
            try: data = load_csv(upload)
            except (ValueError, TypeError) as exc:
                st.error(f"Invalid CSV: {exc}"); report["errors"]["experimental_csv"] = str(exc)
    with st.form("calibration_form"):
        base = physical_inputs("fit_")
        fit_names = st.multiselect("Fit parameters", ["capacity_ah", "resistance_ohm", "soc0"],
                                   default=["capacity_ah", "resistance_ohm", "soc0"], key="fit_names")
        fit_terminate = st.checkbox("Include termination in model", value=False, key="fit_terminate")
        c1, c2, c3 = st.columns(3)
        with c1: sv = st.number_input("Voltage σ (V)", .0001, 1., .006, .001, format="%.4f", key="fit_sv")
        with c2: si = st.number_input("Current σ (A)", .0001, 1., .008, .001, format="%.4f", key="fit_si")
        with c3: ss = st.number_input("SoC σ (fraction)", .0001, .2, .003, .001, format="%.4f", key="fit_ss")
        st.form_submit_button("Calculate overlay")
        fit_button = st.form_submit_button("Auto-calibrate", disabled=data is None)
    try:
        base.validate()
        identity = json.dumps({"base": asdict(base), "terminate": fit_terminate, "names": fit_names, "sigma": [sv, si, ss]}, sort_keys=True)
        identity += source + ("" if data is None else data.to_csv(index=False))
        key = hashlib.sha256(identity.encode()).hexdigest()
        if fit_button:
            with st.spinner("Fitting exact CC/CV trajectories…"):
                fitted, info = calibrate(data, base, fit_names,
                    {"voltage_v": sv, "current_a": si, "soc_est": ss}, fit_terminate)
            st.session_state["calibration"] = (key, fitted, info)
        saved = st.session_state.get("calibration")
        fitted, info = (saved[1], saved[2]) if saved and saved[0] == key else (base, None)
        if info:
            if info["success"]: st.success("Calibration applied in Section 3. Metrics are in-sample.")
            else: st.warning("Optimizer did not converge; inspect diagnostics before using parameters.")
            for warning in info["warnings"]: st.warning(warning)
            st.json({n: getattr(fitted, n) for n in fit_names}, expanded=False)
        if data is None:
            st.info("Select a sample or upload CSV for overlays, residuals and fit errors.")
        else:
            before = comparison(data, exact(base, data.time_sec.to_numpy(), fit_terminate)).assign(fit="Before")
            after = comparison(data, exact(fitted, data.time_sec.to_numpy(), fit_terminate)).assign(fit="After" if info else "Uncalibrated")
            scores = pd.concat([before, after], ignore_index=True) if info else after
            st.dataframe(scores, hide_index=True)
            overlay, residual, predictions = calibration_figures(base, fitted, data, fit_terminate,
                "Synthetic bench" if source.startswith("Synthetic") else "Measured data")
            st.image(overlay); st.image(residual)
            st.write("**Residual = experiment − model.** Voltage residuals proportional to current suggest resistance/lead-drop error; "
                     "a signed current tail suggests taper or timing mismatch. These are hypotheses, not unique diagnoses. "
                     "Coulomb-counted SoC is correlated with the current used to compute it.")
            tables.update({"experiment": data, "experimental_metrics": scores, "predictions_and_residuals": predictions})
            figures.update({"experimental_overlay": overlay, "residuals": residual})
        report["sections"]["calibration"] = {"base_parameters": asdict(base), "parameters": asdict(fitted),
            "source": source, "termination": fit_terminate, "fit": info,
            "experimental_metrics": None if data is None else scores.to_dict(orient="records"),
            "exact_switch_sec": exact_events(fitted, fit_terminate)[0], "exact_stop_sec": exact_events(fitted, fit_terminate)[1]}
        tables["calibrated_parameters"] = parameter_table(fitted, "calibration" if info else "uncalibrated_overlay")
    except ValueError as exc:
        st.error(str(exc)); report["errors"]["calibration"] = str(exc)

with tabs[3]:
    st.header("Physics-style relationship experiments")
    st.write("At fixed SoC, current positive into the cell gives Vterm = VOC + RI, slope **+R**. "
             "The **−R** line uses positive outward discharge current. These are current sweeps at a fixed state, not a charging trajectory.")
    with st.form("physics_form"):
        p_physics = physical_inputs("phy_")
        fixed_soc = st.slider("Fixed SoC for Ohm's-law sweep", 0., 1., .5, .05, key="phy_fixed_soc")
        curvature = st.slider("Illustrative OCV curvature k/b", -.8, .8, .4, .05, key="phy_curvature")
        st.form_submit_button("Calculate physics relationships")
    try:
        figure, relationships = physics_result(p_physics, fixed_soc, curvature)
        st.image(figure, caption="Linear circuit/rate/CC relationships; curved OCV illustration; exponential and semilog taper")
        st.latex(r"U_{illustration}(s)=a+bs+ks(1-s),\quad |k|<b")
        st.caption("Curved OCV is an illustrative monotone alternative, not measured data or the engine/calibration law. "
                   "Curvature affects only this panel. Sweep points above Vmax describe the constitutive line, not attainable regulated charging.")
        report["sections"]["physics"] = {"parameters": asdict(p_physics), "fixed_soc": fixed_soc,
            "curvature_ratio": curvature, "curvature_v": p_physics.ocv_slope_v*curvature,
            "charging_slope_ohm": p_physics.resistance_ohm, "discharging_slope_ohm": -p_physics.resistance_ohm,
            "nonlinear_ocv_scope": "Illustration only; affine engine unchanged."}
        tables["physics_parameters"] = parameter_table(p_physics, "physics")
        tables.update({"physics_"+name: table for name, table in relationships.items()})
        figures["physics_relationships"] = figure
    except ValueError as exc:
        st.error(str(exc)); report["errors"]["physics"] = str(exc)

with tabs[4]:
    st.header("One-click presentation and report bundle")
    st.write("Summaries (TXT/Markdown/JSON), all available parameter/error/trajectory/relationship CSVs, "
             "300-dpi PNGs, and complete source with report and bilingual presentation guide.")
    if report["errors"]: st.warning("Some sections have invalid inputs. Their errors are recorded; fix them for a complete bundle.")
    st.caption("Apply each form before downloading; unsent edits are excluded.")
    package = build_bundle(report, tables, figures, root=ROOT)
    # Inspect the actual download payload in Streamlit integration tests.
    st.session_state["last_export_bytes"] = package
    st.session_state["last_export_report"] = report
    st.download_button("Download complete presentation ZIP", package, "charger_diagnostics.zip", "application/zip", key="export_zip")
    st.json(json_safe(report), expanded=False)
