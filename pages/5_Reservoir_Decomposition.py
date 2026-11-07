"""Page 5 (part 3): STL decomposition and spectrogram of the filling degree.

Area: GLOBAL sidebar selector. Year interval and method parameters: LOCAL,
because they only apply to this page. Plot functions are shared with the
notebook (modules/decomposition.py).
"""
import matplotlib.pyplot as plt
import streamlit as st

from modules.data_loader import load_reservoirs
from modules.decomposition import filling_series, spectrogram_plot, stl_plot
from modules.selectors import selected_area

st.title("Filling degree: STL and spectrogram")
df = load_reservoirs()

area_type, area_number, _ = selected_area()
area_name = df.loc[(df["area_type"] == area_type) & (df["area_number"] == area_number), "name"].iloc[0]

# Local setting shared by both tabs: which years to analyse
years = df["date"].dt.year
first, last = st.slider("Years", int(years.min()), int(years.max()), (2010, int(years.max())))
series = filling_series(df, area_type, area_number, first, last)
st.caption(f"Area: **{area_name}** (change it in the sidebar) · {len(series)} weekly values")

tab_stl, tab_spec = st.tabs(["STL decomposition", "Spectrogram"])

with tab_stl:
    c1, c2, c3 = st.columns(3)
    # Smoother lengths must be odd; step=2 keeps the sliders on odd numbers
    seasonal = c1.slider("Seasonal smoother (weeks)", 7, 51, 13, step=2,
                         help="Larger = the yearly pattern is allowed to change more slowly.")
    trend = c2.slider("Trend smoother (weeks)", 53, 261, 105, step=2,
                      help="Must be longer than the period (52). Larger = smoother trend.")
    robust = c3.toggle("Robust fit", value=False, help="Down-weights unusual weeks, e.g. very dry years.")
    fig = stl_plot(series, seasonal=seasonal, trend=trend, robust=robust, title=f"filling degree, {area_name}")
    st.pyplot(fig)
    plt.close(fig)
    st.markdown("**Reading the plot:** *Trend* = slow multi-year change, *Seasonal* = the yearly "
                "fill-and-drain cycle (period 52 weeks), *Residual* = what is left, e.g. wet or dry weeks.")

with tab_spec:
    c1, c2, c3 = st.columns(3)
    window = c1.slider("Window length (weeks)", 26, 260, 104, step=2,
                       help="Longer window = sharper frequencies, blurrier time.")
    overlap = c2.slider("Window overlap (weeks)", 0, window - 1, min(78, window - 1),
                        help="Weeks shared by neighbouring windows.")
    max_f = c3.slider("Max frequency (cycles/year)", 2, 26, 6)
    fig = spectrogram_plot(series, window, overlap, max_f, title=f"filling degree, {area_name}")
    st.pyplot(fig)
    plt.close(fig)
    st.markdown("**Reading the plot:** the bright band at **1 cycle per year** is the yearly cycle. "
                "Energy at 2-3 cycles per year shows that the yearly curve is not a pure sine.")

with st.expander("Data source and method"):
    st.markdown(
        "Weekly filling degree from the **NVE Magasinstatistikk API** (live). Missing weeks are "
        "interpolated so the series is equally spaced. STL: `statsmodels.tsa.seasonal.STL` with period 52. "
        "Spectrogram: `scipy.signal.spectrogram` with a Hann window and linear detrending."
    )
