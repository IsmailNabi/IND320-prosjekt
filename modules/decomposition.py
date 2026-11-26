"""STL decomposition and spectrogram of the reservoir filling degree (no Streamlit imports).

The Magasinstatistikk data are weekly, so one year = 52 observations.
"""
from plotly.subplots import make_subplots
import numpy as np
import pandas as pd
from scipy.signal import spectrogram
from statsmodels.tsa.seasonal import STL

WEEKS_PER_YEAR = 52


def filling_series(df: pd.DataFrame, area_type: str, area_number: int,
                   first_year: int | None = None, last_year: int | None = None) -> pd.Series:
    """Weekly filling degree for one area as a regular time series.

    df is the prepared reservoir table (modules.helpers.prepare_reservoir_df).
    STL and the spectrogram need equally spaced values, so the series is put on
    a strict weekly grid and the rare missing weeks are interpolated.
    """
    sel = df[(df["area_type"] == area_type) & (df["area_number"] == area_number)]
    if first_year is not None:
        sel = sel[sel["date"].dt.year >= first_year]
    if last_year is not None:
        sel = sel[sel["date"].dt.year <= last_year]
    s = sel.set_index("date")["filling_degree"].sort_index()
    s = s[~s.index.duplicated()]
    return s.asfreq("W-" + s.index[0].day_name()[:3].upper()).interpolate().rename("filling_degree")


def stl_plot(series: pd.Series, period: int = WEEKS_PER_YEAR, seasonal: int = 13,
             trend: int = 105, robust: bool = False, title: str = "Filling degree"):
    """Seasonal-Trend decomposition using LOESS (STL), plotted as four panels.

    Parameters (statsmodels.tsa.seasonal.STL; smoothers must be odd integers):
    seasonal : seasonal smoother length. 13 weeks lets the yearly pattern change
               slowly from year to year (statsmodels' default is 7).
    trend    : trend smoother length. Must be > period; 105 weeks (about two years)
               follows multi-year changes but not the yearly cycle.
    robust   : True down-weights unusual weeks (e.g. dry years) in the LOESS fits.
    Returns the figure.
    """
    seasonal = seasonal + (seasonal % 2 == 0)           # STL requires odd lengths
    trend = max(trend + (trend % 2 == 0), period + 1 + (period % 2))
    res = STL(series, period=period, seasonal=seasonal, trend=trend, robust=robust).fit()

    parts = [("Observed", res.observed), ("Trend", res.trend), ("Seasonal", res.seasonal), ("Residual", res.resid)]
    fig = make_subplots(rows=4, cols=1, shared_xaxes=True, vertical_spacing=0.05,
                        subplot_titles=[name for name, _ in parts])
    for row, (name, values) in enumerate(parts, start=1):
        if name == "Residual":
            fig.add_scatter(x=values.index, y=values, mode="markers", marker=dict(size=3), name=name, row=row, col=1)
            fig.add_hline(y=0, line=dict(color="black", width=1), row=row, col=1)
        else:
            fig.add_scatter(x=values.index, y=values, name=name, line=dict(width=1.5), row=row, col=1)
    fig.update_layout(title=f"STL of {title} (period {period}, seasonal {seasonal}, trend {trend}, robust {robust})",
                      height=820, showlegend=False, hovermode="x")
    fig.update_xaxes(title_text="Date", row=4, col=1)
    return fig


def spectrogram_plot(series: pd.Series, window_length: int = 104, window_overlap: int = 78,
                     max_frequency: float = 6.0, title: str = "Filling degree"):
    """Spectrogram (short-time Fourier power) of a weekly series.

    window_length  : weeks per window. 104 (two years) resolves the yearly cycle
                     with a frequency resolution of 0.5 cycles per year.
    window_overlap : weeks shared by neighbouring windows (default 75 %), which
                     gives a smoother picture along the time axis.
    max_frequency  : highest frequency shown (cycles per year). Weekly data reach
                     26 cycles per year, but above ~6 there is mostly noise.
    Frequencies are shown in cycles per year (sampling rate 52 per year).
    Returns the figure.
    """
    window_overlap = min(window_overlap, window_length - 1)       # overlap must be < window
    x = series.to_numpy(float)
    f, t, power = spectrogram(x, fs=WEEKS_PER_YEAR, window="hann", nperseg=window_length,
                              noverlap=window_overlap, detrend="linear", scaling="density")
    centres = series.index[0] + pd.to_timedelta(t * 365.25, unit="D")   # window centres as dates

    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.35, 0.65], vertical_spacing=0.06)
    fig.add_scatter(x=series.index, y=series.values, name=title, line=dict(width=1.5), row=1, col=1)
    keep = f <= max_frequency
    fig.add_heatmap(x=centres, y=f[keep], z=10 * np.log10(power[keep] + 1e-12), colorscale="Viridis",
                    colorbar=dict(title="Power (dB)", len=0.65, y=0, yanchor="bottom"), row=2, col=1)
    fig.update_yaxes(title_text=title, row=1, col=1)
    fig.update_yaxes(title_text="Frequency (cycles per year)", row=2, col=1)
    fig.update_xaxes(title_text="Date (window centre)", row=2, col=1)
    fig.update_layout(title=f"Spectrogram of {title} (window {window_length} weeks, overlap {window_overlap} weeks)",
                      height=620, showlegend=False, hovermode="closest")
    return fig
