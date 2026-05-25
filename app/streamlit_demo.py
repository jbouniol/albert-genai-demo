"""Sentinel Demo — Streamlit executive clinical UI.

The app is a 2-minute projection surface for the Sentinel multi-agent demo:
behavioral metadata on the left, agent reasoning on the right, and the score /
parent notification as the climax. The orchestration remains in LangGraph; this
file owns only presentation, pacing, and demo ergonomics.
"""
from __future__ import annotations

# Streamlit owns the visual channel; keep Rich panels out of the terminal.
import os

os.environ.setdefault("SENTINEL_QUIET", "1")

import html  # noqa: E402
import inspect  # noqa: E402
import sys  # noqa: E402
import time  # noqa: E402
from dataclasses import dataclass  # noqa: E402
from pathlib import Path  # noqa: E402
from statistics import mean  # noqa: E402
from typing import Any  # noqa: E402

_REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO_ROOT / "src"))

import plotly.graph_objects as go  # noqa: E402
import streamlit as st  # noqa: E402

from sentinel.agents.collector import Collector  # noqa: E402
from sentinel.config import HITL_TRIGGER, MODELS, THRESHOLDS  # noqa: E402
from sentinel.data.generator import APPS  # noqa: E402
from sentinel.data.models import AnalysisResult, MetadataWindow, ScoreResult  # noqa: E402
from sentinel.llm.client import SentinelLLMError  # noqa: E402
from sentinel.orchestrator.graph import AgentState, build_graph  # noqa: E402
from sentinel.tools.baseline import compute_baseline  # noqa: E402

st.set_page_config(
    page_title="Sentinel — Teen Digital Safety",
    page_icon="S",
    layout="wide",
    initial_sidebar_state="collapsed",
)


PROFILE_OPTIONS = {
    "lucas": {
        "label": "Lucas",
        "short": "Lucas / grooming",
        "demo_role": "climax case",
        "pattern": "New contact escalation",
    },
    "emma": {
        "label": "Emma",
        "short": "Emma / normal",
        "demo_role": "false-positive guardrail",
        "pattern": "Exam-period drift",
    },
    "mia": {
        "label": "Mia",
        "short": "Mia / harassment",
        "demo_role": "known-contact pressure",
        "pattern": "Known contact surge",
    },
}

APP_COLORS = {
    "Discord": "#7C8CFF",
    "Snapchat": "#E8D84D",
    "Instagram": "#FF6FAE",
    "TikTok": "#5BD3D9",
    "iMessage": "#6EE7A8",
}

LEVEL_COLORS = {
    "WATCH": "#6EE7A8",
    "MONITOR": "#E8D84D",
    "ALERT": "#F59E5B",
    "HIGH_ALERT": "#FF6B6B",
}

AGENT_STEPS = {
    "collector": "Collector",
    "analyzer": "Analyzer",
    "scorer": "Scorer",
    "communicator": "Communicator",
}

AGENT_DESCRIPTIONS = {
    "collector": "Loads the 21-day metadata window",
    "analyzer": "Detects behavioral signals",
    "scorer": "Calibrates the 0-1 risk score",
    "communicator": "Drafts the parent notification",
}


st.session_state.setdefault("last_run", None)
st.session_state.setdefault("last_profile", None)
st.session_state.setdefault("cached", False)
st.session_state.setdefault("last_elapsed", None)


def _supports_kw(function: Any, name: str) -> bool:
    try:
        signature = inspect.signature(function)
    except (TypeError, ValueError):
        return False
    return name in signature.parameters


def _html(body: str) -> None:
    if hasattr(st, "html"):
        st.html(body)
        return
    st.markdown(body, unsafe_allow_html=True)


def _stretch_button(label: str, *, type_: str = "secondary", icon: str | None = None) -> bool:
    kwargs: dict[str, Any] = {"type": type_}
    if icon and _supports_kw(st.button, "icon"):
        kwargs["icon"] = icon
    if _supports_kw(st.button, "width"):
        kwargs["width"] = "stretch"
    else:
        kwargs["use_container_width"] = True
    return st.button(label, **kwargs)


def _plotly_chart(fig: go.Figure) -> None:
    kwargs: dict[str, Any] = {
        "theme": None,
        "config": {"displayModeBar": False, "responsive": True},
    }
    if _supports_kw(st.plotly_chart, "width"):
        kwargs["width"] = "stretch"
    else:
        kwargs["use_container_width"] = True
    st.plotly_chart(fig, **kwargs)


@dataclass(frozen=True)
class WindowStats:
    screen_delta: float
    sleep_delta: float
    night_delta: float
    baseline_screen: float
    baseline_sleep: float
    baseline_night: float
    last7_screen: float
    last7_sleep: float
    last7_night: float
    top_contact: str
    top_contact_messages: int


def _inject_css() -> None:
    """Apply a compact executive-clinical skin without adding dependencies."""
    _html(
        """
<style>
:root {
  --sentinel-bg: #0b0f10;
  --sentinel-panel: #111719;
  --sentinel-panel-soft: #151d20;
  --sentinel-line: rgba(229, 226, 216, 0.14);
  --sentinel-text: #f3efe4;
  --sentinel-muted: #9fa8a3;
  --sentinel-green: #6ee7a8;
  --sentinel-cyan: #5bd3d9;
  --sentinel-amber: #e8d84d;
  --sentinel-red: #ff6b6b;
}

.stApp {
  background:
    radial-gradient(circle at 16% 0%, rgba(91, 211, 217, 0.12), transparent 30%),
    linear-gradient(180deg, #0c1112 0%, #080b0c 100%);
  color: var(--sentinel-text);
}

[data-testid="stHeader"] {
  background: transparent;
}

[data-testid="stSidebar"] {
  background: #0b0f10;
}

.block-container {
  max-width: 1500px;
  padding: 1.25rem 2.25rem 7.5rem;
}

h1, h2, h3, p, label, span, div {
  letter-spacing: 0 !important;
}

h1 {
  font-size: clamp(1.85rem, 2.55vw, 2.75rem) !important;
  font-weight: 760 !important;
  line-height: 1.02 !important;
}

h2, h3 {
  color: var(--sentinel-text) !important;
}

.stMarkdown, .stCaption, [data-testid="stMarkdownContainer"] {
  color: var(--sentinel-text);
}

[data-testid="stCaptionContainer"] {
  color: var(--sentinel-muted) !important;
}

.sentinel-kicker {
  color: var(--sentinel-cyan);
  font-size: 0.72rem;
  font-weight: 760;
  letter-spacing: 0.12em !important;
  text-transform: uppercase;
}

.sentinel-hero {
  border-bottom: 1px solid var(--sentinel-line);
  padding: 0.15rem 0 0.75rem;
  margin-bottom: 0.75rem;
}

.sentinel-subtitle {
  color: var(--sentinel-muted);
  max-width: 820px;
  font-size: 0.95rem;
  line-height: 1.45;
}

.case-strip,
.signal-ledger,
.transcript-card,
.empty-card,
.phone-shell,
.risk-lens {
  background: linear-gradient(180deg, rgba(21, 29, 32, 0.96), rgba(12, 17, 18, 0.96));
  border: 1px solid var(--sentinel-line);
  border-radius: 8px;
  box-shadow: 0 18px 48px rgba(0, 0, 0, 0.24);
}

.case-strip {
  display: grid;
  grid-template-columns: 1.4fr repeat(5, minmax(130px, 1fr));
  gap: 1px;
  overflow: hidden;
  margin: 0.7rem 0 1rem;
}

.case-cell {
  background: rgba(255, 255, 255, 0.025);
  padding: 0.72rem 0.86rem;
  min-width: 0;
}

.case-label {
  color: var(--sentinel-muted);
  font-size: 0.68rem;
  font-weight: 700;
  text-transform: uppercase;
}

.case-value {
  color: var(--sentinel-text);
  font-size: 0.95rem;
  font-weight: 720;
  margin-top: 0.25rem;
  white-space: normal;
}

.case-delta-good {
  color: var(--sentinel-green);
}

.case-delta-watch {
  color: var(--sentinel-amber);
}

.case-delta-alert {
  color: var(--sentinel-red);
}

.section-title {
  align-items: baseline;
  display: flex;
  justify-content: space-between;
  margin: 0.25rem 0 0.45rem;
}

.section-title strong {
  color: var(--sentinel-text);
  font-size: 0.92rem;
  text-transform: uppercase;
}

.section-title span {
  color: var(--sentinel-muted);
  font-size: 0.78rem;
}

.chart-caption {
  color: var(--sentinel-muted);
  font-size: 0.78rem;
  margin: -0.35rem 0 0.75rem;
}

.agent-timeline {
  display: grid;
  gap: 0.5rem;
}

.agent-row {
  align-items: center;
  background: rgba(255, 255, 255, 0.035);
  border: 1px solid rgba(229, 226, 216, 0.10);
  border-radius: 8px;
  display: grid;
  grid-template-columns: 1.1rem 1fr auto;
  gap: 0.65rem;
  padding: 0.68rem 0.75rem;
}

.agent-dot {
  border-radius: 999px;
  height: 0.72rem;
  width: 0.72rem;
}

.agent-done .agent-dot {
  background: var(--sentinel-green);
  box-shadow: 0 0 18px rgba(110, 231, 168, 0.45);
}

.agent-active .agent-dot {
  background: var(--sentinel-cyan);
  box-shadow: 0 0 18px rgba(91, 211, 217, 0.60);
}

.agent-skipped .agent-dot {
  background: var(--sentinel-amber);
}

.agent-idle .agent-dot {
  background: rgba(243, 239, 228, 0.28);
}

.agent-name {
  color: var(--sentinel-text);
  font-weight: 700;
}

.agent-desc,
.agent-state {
  color: var(--sentinel-muted);
  font-size: 0.75rem;
}

.transcript-card {
  color: var(--sentinel-text);
  min-height: 138px;
  padding: 1rem;
}

.transcript-label {
  color: var(--sentinel-cyan);
  font-size: 0.72rem;
  font-weight: 760;
  text-transform: uppercase;
}

.transcript-body {
  color: #dfe6df;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  font-size: 0.86rem;
  line-height: 1.55;
  margin-top: 0.65rem;
  white-space: pre-wrap;
}

.empty-card {
  color: var(--sentinel-muted);
  min-height: 138px;
  padding: 1rem;
}

.risk-lens {
  min-height: 184px;
  padding: 1.05rem;
}

.risk-head {
  align-items: flex-start;
  display: flex;
  gap: 1rem;
  justify-content: space-between;
}

.risk-score {
  color: var(--sentinel-text);
  font-size: clamp(2.15rem, 4vw, 3.5rem);
  font-weight: 790;
  line-height: 0.86;
}

.risk-level {
  border-radius: 999px;
  color: #080b0c;
  font-size: 0.72rem;
  font-weight: 800;
  padding: 0.35rem 0.55rem;
  text-transform: uppercase;
}

.risk-rail {
  background: linear-gradient(90deg, #6ee7a8 0 30%, #e8d84d 30% 50%,
    #f59e5b 50% 65%, #ff6b6b 65% 100%);
  border-radius: 999px;
  height: 0.72rem;
  margin-top: 1.25rem;
  position: relative;
}

.risk-marker,
.hitl-marker {
  background: var(--sentinel-text);
  border-radius: 999px;
  height: 1.45rem;
  position: absolute;
  top: -0.36rem;
  transform: translateX(-50%);
  width: 0.24rem;
}

.hitl-marker {
  background: #080b0c;
  border: 1px solid var(--sentinel-text);
  opacity: 0.9;
}

.risk-labels {
  color: var(--sentinel-muted);
  display: flex;
  font-size: 0.7rem;
  justify-content: space-between;
  margin-top: 0.55rem;
}

.risk-rationale {
  border-top: 1px solid var(--sentinel-line);
  color: #dfe6df;
  font-size: 0.9rem;
  line-height: 1.45;
  margin-top: 1.05rem;
  padding-top: 0.9rem;
}

.phone-shell {
  margin: 0 auto;
  max-width: 430px;
  padding: 0.65rem;
}

.phone-screen {
  background:
    linear-gradient(180deg, rgba(10, 18, 21, 0.92), rgba(3, 6, 7, 0.98)),
    radial-gradient(circle at 50% 0%, rgba(91, 211, 217, 0.2), transparent 50%);
  border: 1px solid rgba(229, 226, 216, 0.12);
  border-radius: 8px;
  min-height: 224px;
  padding: 0.85rem;
}

.phone-time {
  color: var(--sentinel-text);
  font-size: 2.15rem;
  font-weight: 760;
  line-height: 1;
  text-align: center;
}

.phone-date {
  color: var(--sentinel-muted);
  font-size: 0.8rem;
  margin: 0.15rem 0 0.8rem;
  text-align: center;
}

.ios-banner {
  background: rgba(28, 31, 33, 0.92);
  border: 1px solid rgba(255, 255, 255, 0.10);
  border-radius: 8px;
  box-shadow: 0 16px 44px rgba(0, 0, 0, 0.42);
  padding: 0.82rem 0.9rem;
}

.banner-top {
  align-items: center;
  color: var(--sentinel-muted);
  display: flex;
  font-size: 0.68rem;
  font-weight: 760;
  gap: 0.45rem;
  text-transform: uppercase;
}

.app-glyph {
  align-items: center;
  background: var(--sentinel-cyan);
  border-radius: 6px;
  color: #051011;
  display: inline-flex;
  font-size: 0.75rem;
  font-weight: 900;
  height: 1.25rem;
  justify-content: center;
  width: 1.25rem;
}

.banner-subject {
  color: var(--sentinel-text);
  font-size: 0.96rem;
  font-weight: 720;
  line-height: 1.25;
  margin-top: 0.55rem;
}

.banner-body {
  color: #d5ddd7;
  font-size: 0.86rem;
  line-height: 1.42;
  margin-top: 0.35rem;
}

.no-notification {
  background: rgba(110, 231, 168, 0.09);
  border: 1px solid rgba(110, 231, 168, 0.35);
  border-radius: 8px;
  color: #b8f3d3;
  line-height: 1.45;
  padding: 1rem;
}

.signal-ledger {
  margin-top: 1.2rem;
  overflow: hidden;
}

.signal-row {
  display: grid;
  grid-template-columns: minmax(170px, 0.95fr) 120px 100px 96px minmax(240px, 2fr);
  gap: 1px;
}

.signal-row > div {
  background: rgba(255, 255, 255, 0.03);
  min-width: 0;
  padding: 0.72rem 0.85rem;
}

.signal-header > div {
  color: var(--sentinel-muted);
  font-size: 0.66rem;
  font-weight: 760;
  text-transform: uppercase;
}

.signal-name {
  color: var(--sentinel-text);
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  font-size: 0.76rem;
  overflow-wrap: anywhere;
}

.signal-muted {
  color: var(--sentinel-muted);
  font-size: 0.78rem;
}

.signal-evidence {
  color: #dfe6df;
  font-size: 0.82rem;
  line-height: 1.35;
}

[data-testid="stBottom"],
[data-testid="stBottom"] > div,
[data-testid="stBottomBlockContainer"] {
  background: rgba(8, 11, 12, 0.92);
}

[data-testid="stBottom"] {
  border-top: 1px solid rgba(229, 226, 216, 0.18);
  backdrop-filter: blur(16px);
}

[data-testid="stBottomBlockContainer"] {
  max-width: 1500px;
  padding-bottom: 0.75rem;
  padding-top: 0.65rem;
}

[data-testid="stBottom"] label,
[data-testid="stBottom"] p,
[data-testid="stBottom"] span {
  color: #dfe6df !important;
}

[data-testid="stBottom"] [data-testid="stCaptionContainer"] p {
  color: var(--sentinel-muted) !important;
}

[data-testid="stBottom"] .stButton > button {
  background: var(--sentinel-text) !important;
  border: 1px solid rgba(243, 239, 228, 0.55) !important;
  color: #080b0c !important;
}

[data-testid="stBottom"] .stButton > button span {
  color: #080b0c !important;
}

[data-testid="stBottom"] .stButton > button * {
  color: #080b0c !important;
  fill: #080b0c !important;
}

[data-testid="stBottom"] [data-testid="stButtonGroup"] button {
  background: rgba(255, 255, 255, 0.04) !important;
  border-color: rgba(229, 226, 216, 0.20) !important;
  color: var(--sentinel-muted) !important;
}

[data-testid="stBottom"] [data-testid="stButtonGroup"] button[aria-pressed="true"],
[data-testid="stBottom"] [data-testid="stButtonGroup"] button[aria-checked="true"] {
  background: rgba(91, 211, 217, 0.14) !important;
  border-color: rgba(91, 211, 217, 0.75) !important;
}

[data-testid="stBottom"] [data-testid="stButtonGroup"] button[aria-pressed="true"] *,
[data-testid="stBottom"] [data-testid="stButtonGroup"] button[aria-checked="true"] * {
  color: var(--sentinel-text) !important;
}

.stButton > button,
[data-testid="stBaseButton-primary"] {
  border-radius: 8px !important;
  font-weight: 760 !important;
}

[data-testid="stPlotlyChart"] {
  background: rgba(17, 23, 25, 0.68);
  border: 1px solid var(--sentinel-line);
  border-radius: 8px;
  padding: 0.1rem;
}

@media (max-width: 900px) {
  .block-container {
    padding: 1rem 1rem 8rem;
  }
  .case-strip,
  .signal-row {
    grid-template-columns: 1fr;
  }
}
</style>
        """
    )


def _esc(value: Any) -> str:
    return html.escape(str(value), quote=True)


def _format_delta(value: float, unit: str, danger_when_positive: bool = True) -> tuple[str, str]:
    sign = "+" if value >= 0 else ""
    css_class = "case-delta-good"
    if abs(value) >= 1:
        is_alert = value > 0 if danger_when_positive else value < 0
        css_class = "case-delta-alert" if is_alert else "case-delta-good"
    elif abs(value) >= 0.5:
        css_class = "case-delta-watch"
    return f"{sign}{value:.1f}{unit}", css_class


def _rgba(hex_color: str, alpha: float) -> str:
    color = hex_color.lstrip("#")
    red, green, blue = (int(color[i : i + 2], 16) for i in (0, 2, 4))
    return f"rgba({red}, {green}, {blue}, {alpha})"


def _window_stats(window: MetadataWindow) -> WindowStats:
    baseline = compute_baseline(window)
    last_7 = window.days[-7:]
    last7_screen = mean(day.total_screen_time_min for day in last_7)
    last7_sleep = mean(day.sleep_hours for day in last_7)
    last7_night = mean(day.nighttime_activity_min for day in last_7)

    totals: dict[str, int] = {}
    for day in window.days:
        for contact in day.contacts_interactions:
            totals[contact.contact_label] = (
                totals.get(contact.contact_label, 0) + contact.message_count
            )
    top_contact, top_messages = max(totals.items(), key=lambda item: item[1])

    return WindowStats(
        screen_delta=last7_screen - baseline.mean_screen_time_min,
        sleep_delta=last7_sleep - baseline.mean_sleep_hours,
        night_delta=last7_night - baseline.mean_nighttime_activity_min,
        baseline_screen=baseline.mean_screen_time_min,
        baseline_sleep=baseline.mean_sleep_hours,
        baseline_night=baseline.mean_nighttime_activity_min,
        last7_screen=last7_screen,
        last7_sleep=last7_sleep,
        last7_night=last7_night,
        top_contact=top_contact,
        top_contact_messages=top_messages,
    )


def _chart_theme(fig: go.Figure, height: int, left_margin: int = 40) -> go.Figure:
    fig.update_layout(
        height=height,
        margin={"l": left_margin, "r": 36, "t": 18, "b": 38},
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font={"color": "#dfe6df", "family": "Inter, -apple-system, Segoe UI, sans-serif"},
        hovermode="x unified",
        legend={
            "orientation": "h",
            "x": 0,
            "y": 1.14,
            "font": {"size": 11, "color": "#9fa8a3"},
        },
    )
    fig.update_xaxes(
        color="#9fa8a3",
        gridcolor="rgba(229,226,216,0.08)",
        linecolor="rgba(229,226,216,0.18)",
        zeroline=False,
    )
    fig.update_yaxes(
        color="#9fa8a3",
        gridcolor="rgba(229,226,216,0.08)",
        linecolor="rgba(229,226,216,0.18)",
        zeroline=False,
    )
    return fig


def _chart_sleep_screen(window: MetadataWindow, stats: WindowStats) -> go.Figure:
    """Dual-axis drift chart: sleep, screen time, and late-night activity."""
    days = list(range(len(window.days)))
    sleep = [day.sleep_hours for day in window.days]
    screen = [day.total_screen_time_min for day in window.days]
    night = [day.nighttime_activity_min for day in window.days]

    fig = go.Figure()
    fig.add_vrect(x0=13.5, x1=20.5, fillcolor="#5BD3D9", opacity=0.07, line_width=0)
    fig.add_trace(
        go.Scatter(
            x=days,
            y=sleep,
            name="Sleep hours",
            mode="lines+markers",
            line={"color": "#6EE7A8", "width": 3},
            marker={"size": 5},
            yaxis="y",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=days,
            y=screen,
            name="Screen time",
            mode="lines",
            line={"color": "#5BD3D9", "width": 2.5},
            yaxis="y2",
        )
    )
    fig.add_trace(
        go.Bar(
            x=days,
            y=night,
            name="Night activity",
            marker={"color": "#FF6B6B"},
            opacity=0.34,
            yaxis="y2",
        )
    )
    fig.add_hline(
        y=stats.baseline_sleep,
        line={"color": "rgba(110,231,168,0.45)", "dash": "dot", "width": 1},
        annotation_text="sleep baseline",
        annotation_font={"color": "#9fa8a3", "size": 10},
    )
    fig.update_layout(
        xaxis={"title": "Day in 21-day window", "dtick": 2, "range": [-0.5, 20.5]},
        yaxis={"title": "Sleep (h)", "range": [0, 10.5]},
        yaxis2={
            "title": "Screen / night minutes",
            "overlaying": "y",
            "side": "right",
            "range": [0, max(max(screen), max(night), 220) * 1.12],
        },
    )
    return _chart_theme(fig, height=220)


def _chart_app_sessions(window: MetadataWindow) -> go.Figure:
    """Stacked app sessions, tuned for dark projection."""
    days = list(range(len(window.days)))
    fig = go.Figure()
    for app in APPS:
        color = APP_COLORS[app]
        fig.add_trace(
            go.Scatter(
                x=days,
                y=[day.sessions_per_app.get(app, 0) for day in window.days],
                name=app,
                stackgroup="apps",
                mode="lines",
                line={"width": 1.3, "color": color},
                fillcolor=_rgba(color, 0.42),
            )
        )
    fig.add_vrect(x0=13.5, x1=20.5, fillcolor="#F3EFE4", opacity=0.05, line_width=0)
    fig.update_layout(
        xaxis={"title": "Day", "dtick": 2, "range": [-0.5, 20.5]},
        yaxis={"title": "Sessions / day"},
    )
    return _chart_theme(fig, height=190)


def _chart_contacts_heatmap(window: MetadataWindow, key_contact: str) -> go.Figure:
    """Message volume heatmap for the top contacts."""
    day_count = len(window.days)
    totals: dict[str, int] = {}
    matrix: dict[str, list[int]] = {}
    for idx, day in enumerate(window.days):
        for contact in day.contacts_interactions:
            totals[contact.contact_label] = (
                totals.get(contact.contact_label, 0) + contact.message_count
            )
            row = matrix.setdefault(contact.contact_label, [0] * day_count)
            row[idx] += contact.message_count

    top_contacts = sorted(totals.items(), key=lambda item: -item[1])[:6]
    labels = [label for label, _ in top_contacts][::-1]
    z_values = [matrix[label] for label in labels]
    tick_text = [
        f"{label}  key" if label == key_contact else label
        for label in labels
    ]

    fig = go.Figure(
        data=go.Heatmap(
            z=z_values,
            x=list(range(day_count)),
            y=labels,
            colorscale=[
                [0, "#111719"],
                [0.34, "#24454A"],
                [0.68, "#E8D84D"],
                [1, "#FF6B6B"],
            ],
            hovertemplate="day %{x} / %{y}: %{z} msgs<extra></extra>",
            colorbar={
                "title": {"text": "msgs", "font": {"color": "#9fa8a3"}},
                "tickfont": {"color": "#9fa8a3"},
            },
        )
    )
    if key_contact in labels:
        fig.add_annotation(
            x=20,
            y=key_contact,
            text="dominant thread",
            showarrow=False,
            font={"color": "#0B0F10", "size": 10},
            bgcolor="#E8D84D",
            borderpad=3,
        )
    fig.update_layout(
        xaxis={"title": "Day", "dtick": 2, "range": [-0.5, 20.5]},
        yaxis={"tickmode": "array", "tickvals": labels, "ticktext": tick_text},
    )
    return _chart_theme(fig, height=214, left_margin=112)


def _parse_notification(notification: str) -> tuple[str, str]:
    """Extract the subject line that Communicator is instructed to emit."""
    lines = notification.strip().splitlines()
    subject = ""
    body_start = 0
    for idx, line in enumerate(lines):
        if line.lower().startswith("subject:"):
            subject = line.split(":", 1)[1].strip()
            body_start = idx + 1
            break
    body = "\n".join(lines[body_start:]).strip()
    if not subject:
        subject = "Pattern detected in device activity"
        body = notification.strip()
    return subject, body


def _render_case_strip(window: MetadataWindow, stats: WindowStats, use_cache: bool) -> str:
    screen_delta, screen_class = _format_delta(stats.screen_delta, "m", True)
    sleep_delta, sleep_class = _format_delta(stats.sleep_delta, "h", False)
    night_delta, night_class = _format_delta(stats.night_delta, "m", True)
    mode = "cached replay" if use_cache else "live API"
    return f"""
<div class="case-strip">
  <div class="case-cell">
    <div class="case-label">Case file</div>
    <div class="case-value">{_esc(window.profile_name)}, {_esc(window.age)}
      · {_esc(PROFILE_OPTIONS[window.profile_id]["demo_role"])}</div>
  </div>
  <div class="case-cell">
    <div class="case-label">Persona</div>
    <div class="case-value">{_esc(window.persona_label)}</div>
  </div>
  <div class="case-cell">
    <div class="case-label">Window</div>
    <div class="case-value">{_esc(window.days[0].date)} to {_esc(window.days[-1].date)}</div>
  </div>
  <div class="case-cell">
    <div class="case-label">Last 7d drift</div>
    <div class="case-value"><span class="{screen_class}">{screen_delta}</span> screen
      · <span class="{sleep_class}">{sleep_delta}</span> sleep</div>
  </div>
  <div class="case-cell">
    <div class="case-label">Night / top thread</div>
    <div class="case-value"><span class="{night_class}">{night_delta}</span> night
      · {_esc(stats.top_contact)} ({_esc(stats.top_contact_messages)} msgs)</div>
  </div>
  <div class="case-cell">
    <div class="case-label">Run mode</div>
    <div class="case-value">{_esc(mode)} · metadata only</div>
  </div>
</div>
"""


def _render_header(window: MetadataWindow, stats: WindowStats, use_cache: bool) -> None:
    st.markdown(
        f"""
<div class="sentinel-hero">
  <div class="sentinel-kicker">Sentinel · privacy-by-design digital safety</div>
  <h1>Behavioral risk intelligence, without reading messages.</h1>
  <div class="sentinel-subtitle">
    A multi-agent pipeline reads 21 days of metadata only: timing, frequency,
    app drift, sleep signals and contact volume. The demo keeps the jury's eye
    on the evidence, then lands on the human-in-the-loop decision.
  </div>
</div>
{_render_case_strip(window, stats, use_cache)}
        """,
        unsafe_allow_html=True,
    )


def _section_title(title: str, detail: str) -> None:
    st.markdown(
        f"""
<div class="section-title">
  <strong>{_esc(title)}</strong>
  <span>{_esc(detail)}</span>
</div>
        """,
        unsafe_allow_html=True,
    )


def _render_agent_timeline(
    completed: list[str],
    active: str | None = None,
    skipped: list[str] | None = None,
) -> str:
    skipped = skipped or []
    rows: list[str] = ['<div class="agent-timeline">']
    for name, label in AGENT_STEPS.items():
        if name in completed:
            state = "complete"
            row_class = "agent-done"
        elif name in skipped:
            state = "skipped"
            row_class = "agent-skipped"
        elif name == active:
            state = "running"
            row_class = "agent-active"
        else:
            state = "queued"
            row_class = "agent-idle"
        rows.append(
            f"""
<div class="agent-row {row_class}">
  <div class="agent-dot"></div>
  <div>
    <div class="agent-name">{_esc(label)}</div>
    <div class="agent-desc">{_esc(AGENT_DESCRIPTIONS[name])}</div>
  </div>
  <div class="agent-state">{_esc(state)}</div>
</div>
            """
        )
    rows.append("</div>")
    return "\n".join(rows)


def _render_ready_panel() -> str:
    return """
<div class="empty-card">
  <div class="transcript-label">Pipeline ready</div>
  <div style="margin-top:0.75rem;line-height:1.55;">
    Select a case, choose live API or cached replay, then run the analysis.
    The right side will show the agent timeline and the communicator transcript.
  </div>
</div>
"""


def _render_transcript(text: str, streaming: bool = False) -> str:
    if not text.strip():
        shimmer = "Waiting for Communicator output" if streaming else "No transcript yet."
        return f"""
<div class="empty-card">
  <div class="transcript-label">Communicator transcript</div>
  <div style="margin-top:0.75rem;">{shimmer}</div>
</div>
"""
    label = "Communicator streaming" if streaming else "Communicator transcript"
    return f"""
<div class="transcript-card">
  <div class="transcript-label">{_esc(label)}</div>
  <div class="transcript-body">{_esc(text)}</div>
</div>
"""


def _render_skip_transcript(score_result: ScoreResult | None) -> str:
    score_text = f"{score_result.score:.2f}" if score_result else "pending"
    return f"""
<div class="empty-card">
  <div class="transcript-label">Communicator skipped</div>
  <div style="margin-top:0.75rem;line-height:1.55;">
    Score {score_text} is at or below the HITL trigger ({HITL_TRIGGER:.2f}).
    No parent notification is created for this run.
  </div>
</div>
"""


def _render_phone_notification(notification: str, streaming: bool = False) -> str:
    subject, body = _parse_notification(notification)
    body_html = _esc(body).replace("\n\n", "<br><br>").replace("\n", " ")
    if streaming:
        body_html += '<span style="color:#5bd3d9;">▌</span>'
    return f"""
<div class="phone-shell">
  <div class="phone-screen">
    <div class="phone-time">9:41</div>
    <div class="phone-date">Monday, May 25</div>
    <div class="ios-banner">
      <div class="banner-top"><span class="app-glyph">S</span> Sentinel · now</div>
      <div class="banner-subject">{_esc(subject)}</div>
      <div class="banner-body">{body_html}</div>
    </div>
  </div>
</div>
"""


def _render_no_notification(score_result: ScoreResult | None) -> str:
    score = f"{score_result.score:.2f}" if score_result else "pending"
    return f"""
<div class="phone-shell">
  <div class="phone-screen">
    <div class="phone-time">9:41</div>
    <div class="phone-date">Monday, May 25</div>
    <div class="no-notification">
      <strong>No parent notification triggered.</strong><br>
      Risk score {score} is below the HITL trigger ({HITL_TRIGGER:.2f}).
      The run remains auditable through the signal ledger and scorer rationale.
    </div>
  </div>
</div>
"""


def _render_risk_lens(score_result: ScoreResult | None) -> str:
    if score_result is None:
        return f"""
<div class="risk-lens">
  <div class="transcript-label">Risk Lens</div>
  <div style="color:#9fa8a3;margin-top:0.85rem;line-height:1.5;">
    Awaiting Scorer output. HITL trigger is fixed at {HITL_TRIGGER:.2f}.
  </div>
</div>
"""
    score_pct = max(0.0, min(100.0, score_result.score * 100))
    color = LEVEL_COLORS[score_result.level]
    return f"""
<div class="risk-lens">
  <div class="risk-head">
    <div>
      <div class="transcript-label">Risk Lens</div>
      <div class="risk-score">{score_result.score:.2f}</div>
    </div>
    <div class="risk-level" style="background:{color};">{_esc(score_result.level)}</div>
  </div>
  <div class="risk-rail">
    <div class="risk-marker" style="left:{score_pct:.1f}%;"></div>
    <div class="hitl-marker" title="HITL trigger" style="left:{HITL_TRIGGER * 100:.1f}%;"></div>
  </div>
  <div class="risk-labels">
    <span>WATCH &lt;{THRESHOLDS["watch"]:.2f}</span>
    <span>MONITOR</span>
    <span>ALERT ≥{THRESHOLDS["monitor"]:.2f}</span>
    <span>HITL {HITL_TRIGGER:.2f}</span>
  </div>
  <div class="risk-rationale">{_esc(score_result.rationale)}</div>
</div>
"""


def _render_signal_ledger(analysis: AnalysisResult | None) -> str:
    if analysis is None:
        return ""
    if not analysis.signals:
        rows = """
<div class="signal-row">
  <div class="signal-name">none</div>
  <div class="signal-muted">none</div>
  <div class="signal-muted">none</div>
  <div class="signal-muted">0.00</div>
  <div class="signal-evidence">No risk signals were detected by the Analyzer.</div>
</div>
"""
    else:
        row_parts = []
        for signal in analysis.signals:
            row_parts.append(
                f"""
<div class="signal-row">
  <div class="signal-name">{_esc(signal.name)}</div>
  <div class="signal-muted">{_esc(signal.category)}</div>
  <div class="signal-muted">{_esc(signal.severity)}</div>
  <div class="signal-muted">{signal.confidence:.2f}</div>
  <div class="signal-evidence">{_esc(signal.evidence)}</div>
</div>
                """
            )
        rows = "\n".join(row_parts)
    normal_life = "yes" if analysis.matches_normal_life_event else "no"
    return f"""
<div class="signal-ledger">
  <div class="signal-row signal-header">
    <div>Signal</div>
    <div>Category</div>
    <div>Severity</div>
    <div>Confidence</div>
    <div>Evidence</div>
  </div>
  {rows}
  <div style="border-top:1px solid rgba(229,226,216,0.14);padding:0.9rem;color:#dfe6df;">
    <strong>Analyzer observation:</strong> {_esc(analysis.overall_observation)}
    <span style="color:#9fa8a3;"> · normal life event: {normal_life}</span>
  </div>
</div>
"""


def _render_error(error: SentinelLLMError) -> None:
    if error.kind == "quota":
        st.error(
            "OpenAI returned insufficient_quota. The API key has no remaining credit; "
            "switch to cached mode to replay the last saved outputs."
        )
    elif error.kind == "ratelimit":
        st.error("OpenAI rate-limited the request. Retry in a few seconds or use cached mode.")
    elif error.kind == "timeout":
        st.error("OpenAI request timed out. Retry, or use cached mode.")
    else:
        st.error(f"OpenAI error: {error.original}")

    if _stretch_button(
        "Switch to cached mode and rerun",
        type_="primary",
        icon=":material/offline_bolt:",
    ):
        st.session_state["cached"] = True
        st.rerun()


def _run_pipeline(profile: str, use_cache: bool) -> None:
    """Run LangGraph and stream the Communicator into transcript + phone surfaces."""
    graph = build_graph()
    final_state: dict[str, Any] = {}
    completed: list[str] = []
    skipped: list[str] = []
    buffer: list[str] = []

    with status_placeholder.container():
        status_kwargs: dict[str, Any] = {"expanded": True, "state": "running"}
        if _supports_kw(st.status, "width"):
            status_kwargs["width"] = "stretch"
        status_box = st.status("Agent pipeline starting", **status_kwargs)
        timeline_slot = st.empty()

    def render_timeline(active: str | None) -> None:
        timeline_slot.markdown(
            _render_agent_timeline(completed, active=active, skipped=skipped),
            unsafe_allow_html=True,
        )

    def on_delta(chunk: str) -> None:
        buffer.append(chunk)
        text = "".join(buffer)
        transcript_placeholder.markdown(
            f":shimmer[Communicator streaming]\n\n{_render_transcript(text, streaming=True)}",
            unsafe_allow_html=True,
        )
        notification_placeholder.markdown(
            _render_phone_notification(text, streaming=True),
            unsafe_allow_html=True,
        )

    initial_state: AgentState = {
        "profile_id": profile,
        "window": None,
        "analysis": None,
        "score_result": None,
        "notification": None,
        "callbacks": {"on_communicator_delta": on_delta},
        "use_cache": use_cache,
    }

    t0 = time.perf_counter()
    render_timeline("collector")

    try:
        for event in graph.stream(initial_state, stream_mode="updates"):
            for node_name, node_output in event.items():
                completed.append(node_name)
                final_state.update(node_output or {})
                status_box.write(f"{AGENT_STEPS.get(node_name, node_name)} complete")

                next_active = None
                ordered = list(AGENT_STEPS)
                if node_name in ordered:
                    next_idx = ordered.index(node_name) + 1
                    if next_idx < len(ordered):
                        next_active = ordered[next_idx]
                status_box.update(
                    label=f"{AGENT_STEPS.get(next_active, 'Pipeline')} running",
                    state="running",
                    expanded=True,
                )
                render_timeline(next_active)
    except SentinelLLMError as error:
        st.session_state["last_elapsed"] = time.perf_counter() - t0
        status_box.update(label="Pipeline stopped", state="error", expanded=True)
        _render_error(error)
        return

    if "communicator" not in completed:
        skipped.append("communicator")
    render_timeline(None)
    status_box.update(label="Pipeline complete", state="complete", expanded=True)

    st.session_state["last_run"] = final_state
    st.session_state["last_profile"] = profile
    st.session_state["last_elapsed"] = time.perf_counter() - t0


_inject_css()

bottom_surface = st.bottom if hasattr(st, "bottom") else st.container()
with bottom_surface:
    ctrl_profile, ctrl_cache, ctrl_run, ctrl_meta = st.columns([2.4, 1.05, 1.05, 2.2])
    with ctrl_profile:
        segmented_kwargs: dict[str, Any] = {
            "options": list(PROFILE_OPTIONS),
            "default": st.session_state.get("profile_id", "lucas"),
            "format_func": lambda key: PROFILE_OPTIONS[key]["short"],
            "label_visibility": "collapsed",
        }
        if _supports_kw(st.segmented_control, "width"):
            segmented_kwargs["width"] = "stretch"
        selected_profile = st.segmented_control(
            "Case",
            **segmented_kwargs,
        )
        profile_id = selected_profile or "lucas"
        st.session_state["profile_id"] = profile_id
    with ctrl_cache:
        cached_toggle = st.toggle(
            "Cached replay",
            value=st.session_state["cached"],
            help="Replay saved LLM outputs from disk; useful if quota or network fails.",
        )
        st.session_state["cached"] = cached_toggle
    with ctrl_run:
        run_clicked = _stretch_button(
            "Run analysis",
            type_="primary",
            icon=":material/play_arrow:",
        )
    with ctrl_meta:
        elapsed = st.session_state["last_elapsed"]
        elapsed_text = f"{elapsed:.1f}s" if elapsed else "not run"
        st.caption(
            f"models: {MODELS['analyzer']} / {MODELS['scorer']} / "
            f"{MODELS['communicator']} · HITL {HITL_TRIGGER:.2f} · last run {elapsed_text}"
        )


window = Collector().run(profile_id)
stats = _window_stats(window)
_render_header(window, stats, use_cache=cached_toggle)

data_col, reasoning_col = st.columns([1.22, 1.0], gap="large")

with data_col:
    _section_title("Behavioral Metadata", "baseline days 0-13 · decision window days 14-20")
    _plotly_chart(_chart_sleep_screen(window, stats))
    st.markdown(
        f"""
<div class="chart-caption">
  Last 7d: screen {stats.last7_screen:.0f}m/day vs baseline {stats.baseline_screen:.0f}m;
  sleep {stats.last7_sleep:.1f}h vs {stats.baseline_sleep:.1f}h;
  night activity {stats.last7_night:.0f}m vs {stats.baseline_night:.0f}m.
</div>
        """,
        unsafe_allow_html=True,
    )
    _plotly_chart(_chart_app_sessions(window))
    _plotly_chart(_chart_contacts_heatmap(window, stats.top_contact))

with reasoning_col:
    _section_title("Agent Reasoning", "Collector → Analyzer → Scorer → Communicator")
    status_placeholder = st.empty()
    transcript_placeholder = st.empty()
    status_placeholder.markdown(_render_ready_panel(), unsafe_allow_html=True)
    transcript_placeholder.markdown(_render_transcript(""), unsafe_allow_html=True)

    _section_title("Risk Score", "calibrated by Scorer · HITL threshold shown")
    risk_placeholder = st.empty()
    risk_placeholder.markdown(_render_risk_lens(None), unsafe_allow_html=True)

    _section_title("Parent Notification", "generated only above HITL threshold")
    notification_placeholder = st.empty()
    notification_placeholder.markdown(_render_no_notification(None), unsafe_allow_html=True)

if run_clicked:
    risk_placeholder.markdown(_render_risk_lens(None), unsafe_allow_html=True)
    notification_placeholder.empty()
    transcript_placeholder.empty()
    _run_pipeline(profile_id, use_cache=cached_toggle)

render_state = None
if st.session_state["last_run"] and st.session_state["last_profile"] == profile_id:
    render_state = st.session_state["last_run"]

if render_state:
    analysis = render_state.get("analysis")
    score_result = render_state.get("score_result")
    notification = render_state.get("notification")

    completed_nodes = ["collector", "analyzer", "scorer"]
    skipped_nodes: list[str] = []
    if notification:
        completed_nodes.append("communicator")
    else:
        skipped_nodes.append("communicator")

    status_placeholder.markdown(
        _render_agent_timeline(completed_nodes, skipped=skipped_nodes),
        unsafe_allow_html=True,
    )

    risk_placeholder.markdown(_render_risk_lens(score_result), unsafe_allow_html=True)
    if notification:
        notification_placeholder.markdown(
            _render_phone_notification(notification),
            unsafe_allow_html=True,
        )
        transcript_placeholder.markdown(
            _render_transcript(notification),
            unsafe_allow_html=True,
        )
    else:
        notification_placeholder.markdown(
            _render_no_notification(score_result),
            unsafe_allow_html=True,
        )
        transcript_placeholder.markdown(
            _render_skip_transcript(score_result),
            unsafe_allow_html=True,
        )

    st.markdown(_render_signal_ledger(analysis), unsafe_allow_html=True)

st.caption(
    "Sentinel analyzes metadata only: counts, timing, app sessions, sleep and contact-volume "
    "patterns. It never reads message content."
)
