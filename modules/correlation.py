"""Sliding window correlation (SWC) between weather and reservoir data (no Streamlit imports).

From the lecture "ML approach": the correlation between two series can change
over time. A SWC computes Pearson's correlation inside a window that slides
along the series. A lag shifts the weather series forward in time, so we can
ask "does the weather k weeks ago go together with the reservoir today?".
"""
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from modules.theme import ACCENT


def sliding_window_correlation(reservoir: pd.Series, weather: pd.Series,
                               window: int = 26, lag: int = 0) -> pd.Series:
    """Rolling correlation between `reservoir` and `weather` shifted `lag` steps.

    window: number of weeks in each window (centred).
    lag: weeks the weather leads the reservoir (lag=4: weather 4 weeks earlier).
    """
    shifted = weather.shift(lag)                      # value from `lag` weeks earlier
    both = pd.concat([reservoir, shifted], axis=1, join="inner").dropna()
    swc = both.iloc[:, 0].rolling(window, center=True).corr(both.iloc[:, 1])
    return swc.rename("SWC")


def lagged_correlation(reservoir: pd.Series, weather: pd.Series, max_lag: int = 26) -> pd.Series:
    """Correlation over the whole period for every lag 0..max_lag (one number per lag)."""
    return pd.Series({lag: reservoir.corr(weather.shift(lag)) for lag in range(max_lag + 1)},
                     name="correlation").rename_axis("lag (weeks)")


def swc_figure(reservoir: pd.Series, weather: pd.Series, window: int, lag: int,
               centre: pd.Timestamp | None = None) -> go.Figure:
    """Three panels: reservoir variable, lagged weather variable and their SWC.

    If `centre` is given, the window around it is highlighted in all panels
    (the Plotly version of the lecture's interactive window).
    """
    swc = sliding_window_correlation(reservoir, weather, window, lag)
    shifted = weather.shift(lag)
    fig = make_subplots(rows=3, cols=1, shared_xaxes=True, vertical_spacing=0.06,
                        subplot_titles=[reservoir.name, f"{weather.name}, {lag} weeks earlier",
                                        f"Sliding window correlation (window {window} weeks)"])
    fig.add_scatter(x=reservoir.index, y=reservoir, name=str(reservoir.name), row=1, col=1)
    fig.add_scatter(x=shifted.index, y=shifted, name=str(weather.name), row=2, col=1)
    fig.add_scatter(x=swc.index, y=swc, name="SWC", line=dict(width=2), row=3, col=1)
    fig.add_hline(y=0, line=dict(color="grey", dash="dot"), row=3, col=1)
    if centre is not None:
        half = pd.Timedelta(weeks=window // 2)
        for row in (1, 2, 3):
            fig.add_vrect(x0=centre - half, x1=centre + half, fillcolor=ACCENT, opacity=0.15,
                          line_width=0, row=row, col=1)
    fig.update_yaxes(range=[-1, 1], row=3, col=1)
    fig.update_layout(height=700, showlegend=False)
    return fig
