"""Outlier and anomaly detection for weather series (no Streamlit imports).

* spc_outliers : DCT high-pass filter + Statistical Process Control (robust statistics)
* lof_anomalies: Local Outlier Factor (scikit-learn)

Both functions return (figure, statistics, table of outliers) so the same code
is used in the notebook and on the Streamlit page.
"""
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.fft import dct, idct
from scipy.stats import median_abs_deviation
from sklearn.neighbors import LocalOutlierFactor

OUTLIER_COLOUR = "#d62728"   # red, contrasts with the default blue line


def _step_hours(index: pd.DatetimeIndex) -> float:
    """Sampling interval in hours (1 for hourly data, 24 for daily data)."""
    return pd.Series(index).diff().median() / pd.Timedelta(hours=1)


def dct_highpass(values: np.ndarray, cutoff_days: float, step_hours: float = 1.0):
    """Split a series into slow (seasonal) and fast parts with the Discrete Cosine Transform.

    DCT coefficient k describes a cosine with period 2N/k samples. All
    coefficients with a period LONGER than cutoff_days are removed (set to 0),
    which is a high-pass filter. Returns (high-pass part = SATV, low-pass part, k_cut).
    """
    n = len(values)
    coeffs = dct(values, type=2, norm="ortho")
    k_cut = int(np.ceil(2 * n * step_hours / (cutoff_days * 24)))   # first k with period <= cutoff
    high = coeffs.copy()
    high[:k_cut] = 0                                                # remove slow variation
    satv = idct(high, type=2, norm="ortho")
    return satv, values - satv, k_cut


def spc_outliers(series: pd.Series, cutoff_days: float = 30, n_std: float = 3.0,
                 title: str = "Precipitation"):
    """SPC outliers in a (precipitation) series based on DCT-filtered values (SATV).

    Steps (lecture "Outlier statistics", section Time resolution):
    1. High-pass filter with DCT -> SATV ("seasonally adjusted variations"):
       the season is removed, only the fast variation is left.
    2. Robust statistics on SATV for the whole period: median and
       sigma = 1.4826 * MAD (MAD = median absolute deviation).
    3. Inliers: median - n_std*sigma <= SATV <= median + n_std*sigma.
    4. The limits are moved back to the ORIGINAL scale by adding the low-pass
       (seasonal) part, so they follow the curve. SATV itself is not plotted.

    Parameters: cutoff_days = shortest period (days) regarded as seasonal,
    n_std = number of robust standard deviations for the limits.
    Returns (fig, stats: pd.Series, outliers: pd.DataFrame).
    """
    s = series.dropna()
    satv, low, k_cut = dct_highpass(s.to_numpy(float), cutoff_days, _step_hours(s.index))

    centre = np.median(satv)
    sigma = 1.4826 * median_abs_deviation(satv)          # robust standard deviation
    upper = low + centre + n_std * sigma                  # limits on the original scale
    lower = low + centre - n_std * sigma
    is_out = np.abs(satv - centre) > n_std * sigma

    fig, ax = plt.subplots(figsize=(12, 4.5))
    ax.plot(s.index, s.values, lw=0.7, label=title)
    ax.plot(s.index, upper, color="black", lw=1, ls="--", label=f"SPC limits (±{n_std:g} robust SD)")
    ax.plot(s.index, lower, color="black", lw=1, ls="--")
    ax.scatter(s.index[is_out], s.values[is_out], s=12, color=OUTLIER_COLOUR, zorder=3,
               label=f"Outliers ({is_out.sum()})")
    ax.set_title(f"{title}: SPC on DCT high-pass values (cut-off {cutoff_days:g} days)")
    ax.set_xlabel("Time (UTC)")
    ax.set_ylabel(title)
    ax.grid(True, ls="--", alpha=0.5)
    ax.legend(loc="upper right")
    fig.tight_layout()

    outliers = pd.DataFrame({
        "time": s.index[is_out], "value": s.values[is_out],
        "lower_limit": lower[is_out], "upper_limit": upper[is_out],
        "direction": np.where(satv[is_out] > centre, "high", "low"),
    })
    stats = pd.Series({
        "observations": len(s),
        "outliers": int(is_out.sum()),
        "outlier share (%)": round(100 * is_out.mean(), 2),
        "high outliers": int((outliers["direction"] == "high").sum()),
        "low outliers": int((outliers["direction"] == "low").sum()),
        "DCT coefficients removed": k_cut,
        "SATV median": round(centre, 4),
        "SATV robust SD (1.4826·MAD)": round(sigma, 4),
        "largest outlier value": round(float(outliers["value"].max()), 3) if len(outliers) else np.nan,
    })
    return fig, stats, outliers


def lof_anomalies(series: pd.Series, contamination: float = 0.01, n_neighbors: int = 20,
                  title: str = "Temperature (°C)"):
    """Anomalies in a (temperature) series with the Local Outlier Factor method.

    As in the lecture "Anomaly detection", LOF works on 2D points
    (scaled time, scaled value). Scaling both to unit variance means the
    neighbours of a point are the hours closest in time AND value, so LOF finds
    values that are unusual compared with their local surroundings - not just
    the coldest or warmest hours of the year.

    contamination = expected proportion of anomalies (default 1 %).
    Returns (fig, stats: pd.Series, anomalies: pd.DataFrame).
    """
    s = series.dropna()
    t = np.arange(len(s), dtype=float)
    X = np.column_stack([(t - t.mean()) / t.std(), (s.values - s.values.mean()) / s.values.std()])

    lof = LocalOutlierFactor(n_neighbors=n_neighbors, contamination=contamination)
    labels = lof.fit_predict(X)                 # -1 = anomaly, 1 = normal
    score = -lof.negative_outlier_factor_       # LOF value: about 1 = normal, larger = more outlying
    is_out = labels == -1

    fig, ax = plt.subplots(figsize=(12, 4.5))
    ax.plot(s.index, s.values, lw=0.7, label=title)
    ax.scatter(s.index[is_out], s.values[is_out], s=14, color=OUTLIER_COLOUR, zorder=3,
               label=f"LOF anomalies ({is_out.sum()})")
    ax.set_title(f"{title}: Local Outlier Factor (proportion {contamination:.1%}, {n_neighbors} neighbours)")
    ax.set_xlabel("Time (UTC)")
    ax.set_ylabel(title)
    ax.grid(True, ls="--", alpha=0.5)
    ax.legend(loc="upper right")
    fig.tight_layout()

    anomalies = (pd.DataFrame({"time": s.index[is_out], "value": s.values[is_out], "lof_score": score[is_out]})
                 .sort_values("lof_score", ascending=False).reset_index(drop=True))
    stats = pd.Series({
        "observations": len(s),
        "anomalies": int(is_out.sum()),
        "anomaly share (%)": round(100 * is_out.mean(), 2),
        "mean value, all hours": round(float(s.mean()), 2),
        "mean value, anomalies": round(float(anomalies["value"].mean()), 2) if len(anomalies) else np.nan,
        "highest LOF score": round(float(score.max()), 2),
        "month with most anomalies": anomalies["time"].dt.strftime("%Y-%m").mode().iloc[0] if len(anomalies) else "-",
    })
    return fig, stats, anomalies
