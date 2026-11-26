"""Plotly figures used by the Streamlit pages and the notebook (no Streamlit imports).

Part 4 replaced every matplotlib figure with an interactive Plotly figure.
All figures use the app theme from modules/theme.py.
"""
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from modules import theme  # noqa: F401  (registers the template)
from modules.theme import ACCENT, PRIMARY


def reservoir_lines(df: pd.DataFrame, column: str, label: str) -> go.Figure:
    """One line per area for one metric (reservoir plots)."""
    fig = px.line(df.sort_values("date"), x="date", y=column, color="name", markers=True,
                  labels={"date": "Date", column: label, "name": "Area"})
    fig.update_layout(title=f"{label} per area", height=480)
    return fig


def reservoir_normalized(area_df: pd.DataFrame, labels: dict, normalize) -> go.Figure:
    """All metrics for one area, each min-max scaled to 0-1."""
    fig = go.Figure()
    for col, label in labels.items():
        fig.add_scatter(x=area_df["date"], y=normalize(area_df[col]), name=label, mode="lines+markers")
    fig.update_layout(title="All metrics, min-max normalized", yaxis_title="Normalized (0 = min, 1 = max)",
                      xaxis_title="Date", height=480)
    return fig


def flows_pie(totals: pd.Series, title: str) -> go.Figure:
    """Share of energy exported and imported (GWh)."""
    fig = go.Figure(go.Pie(labels=totals.index, values=totals.values, hole=0.45,
                           marker=dict(colors=[PRIMARY, ACCENT]), textinfo="label+percent"))
    fig.update_layout(title=title, height=420, showlegend=False)
    return fig


def flows_lines(series: pd.DataFrame, title: str) -> go.Figure:
    """Hourly flow per direction."""
    fig = px.line(series, x="ts", y="mw", color="direction",
                  labels={"ts": "Time (UTC)", "mw": "Flow (MW)", "direction": "Direction"})
    fig.update_layout(title=title, height=420)
    return fig


def exchange_rates(rates: pd.DataFrame) -> go.Figure:
    """NOK per EUR and per USD over time."""
    fig = go.Figure()
    for col in rates.columns:
        fig.add_scatter(x=rates.index, y=rates[col], name=f"NOK per {col}")
    fig.update_layout(title="Exchange rates from Norges Bank", xaxis_title="Date", yaxis_title="NOK", height=450)
    return fig


def forecast_animation(table: pd.DataFrame, title: str, n_frames: int = 30) -> go.Figure:
    """Animated forecast: the forecast line (and interval) grows week by week.

    Plotly animations need the same traces in every frame; each frame shows the
    forecast up to a given week. The play button and slider control the frames.
    """
    hist = table[table["part"] == "history"]
    fc = table[table["part"] == "forecast"].reset_index(drop=True)
    has_band = "lower" in fc and fc["lower"].notna().any()
    truth = fc.dropna(subset=["observed"])

    def traces(k: int) -> list:
        part = fc.iloc[:k]
        out = []
        if has_band:
            out.append(go.Scatter(x=list(part["date"]) + list(part["date"][::-1]),
                                  y=list(part["upper"]) + list(part["lower"][::-1]),
                                  fill="toself", fillcolor="rgba(204,121,167,0.22)", line=dict(width=0),
                                  name="80 % interval", hoverinfo="skip"))
        out.append(go.Scatter(x=part["date"], y=part["forecast"], name="Forecast", mode="lines",
                              line=dict(color="#CC79A7", width=3)))
        return out

    steps = sorted(set(int(round(x)) for x in pd.Series(range(1, len(fc) + 1)).quantile(
        [i / max(1, n_frames - 1) for i in range(n_frames)]).tolist()))
    base = [go.Scatter(x=hist["date"], y=hist["observed"], name="Observed (training)",
                       line=dict(color=PRIMARY, width=1.5))]
    if len(truth):
        base.append(go.Scatter(x=truth["date"], y=truth["observed"], name="Observed (after training)",
                               line=dict(color="grey", width=1.5, dash="dot")))
    fig = go.Figure(data=base + traces(len(fc)),
                    frames=[go.Frame(data=base + traces(k), name=str(k)) for k in steps])
    fig.update_layout(
        title=title, xaxis_title="Week", yaxis_title="Filling degree (0-1)", height=520,
        yaxis=dict(range=[0, 1]),
        updatemenus=[dict(type="buttons", showactive=False, x=0, y=-0.18, xanchor="left",
                          buttons=[dict(label="▶ Play", method="animate",
                                        args=[None, dict(frame=dict(duration=120, redraw=True),
                                                         fromcurrent=False, transition=dict(duration=0))])])],
        sliders=[dict(active=len(steps) - 1, x=0.12, y=-0.12, len=0.88,
                      currentvalue=dict(prefix="Weeks forecast: "),
                      steps=[dict(label=str(k), method="animate",
                                  args=[[str(k)], dict(mode="immediate", frame=dict(duration=0, redraw=True))])
                             for k in steps])],
    )
    return fig
