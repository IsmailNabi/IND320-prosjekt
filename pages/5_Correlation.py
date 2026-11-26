"""Prediction: sliding window correlation between weather and reservoir data.

Streamlit version of the lecture's ipywidgets exercise ("ML approach"):
window length, lag and the meteorological property are selectable, and the
correlation is computed against a representative Magasinstatistikk variable.
Everything is weekly (NVE's resolution); the period is the global time frame.
"""
import pandas as pd
import plotly.express as px
import streamlit as st

from modules.correlation import lagged_correlation, swc_figure
from modules.data_loader import load_reservoirs, weather_weekly_with_progress
from modules.selectors import get_period, selected_area
from modules.theme import page_header
from modules.weather import WEATHER_LABELS

page_header("Weather vs reservoir: sliding window correlation", "Prediction",
            "Does the weather some weeks earlier go together with the reservoirs now? Weekly values.")
df = load_reservoirs()
area_type, area_number, region = selected_area()
area_name = df.loc[(df["area_type"] == area_type) & (df["area_number"] == area_number), "name"].iloc[0]
start, end = get_period()
st.caption(f"Area **{area_name}**, time frame {start:%d.%m.%Y}–{end:%d.%m.%Y} (sidebar / map page).")

RESERVOIR_VARS = {
    "change_filling_degree": "Weekly change in filling degree",
    "filling_degree": "Filling degree (0-1)",
}
c1, c2 = st.columns(2)
res_var = c1.selectbox("Reservoir variable", list(RESERVOIR_VARS), format_func=RESERVOIR_VARS.get,
                       help="The weekly change reacts to inflow; the level itself is dominated by the season.")
met_var = c2.selectbox("Weather property", list(WEATHER_LABELS), index=list(WEATHER_LABELS).index("precipitation"),
                       format_func=WEATHER_LABELS.get)

c1, c2 = st.columns(2)
window = c1.slider("Window length (weeks)", 4, 104, 26, step=2)
lag = c2.slider("Lag (weeks the weather comes before the reservoir)", 0, 52, 2)

# Reservoir series for the area and period
area = df[(df["area_type"] == area_type) & (df["area_number"] == area_number)].set_index("date").sort_index()
reservoir = area.loc[pd.Timestamp(start):pd.Timestamp(end), res_var].rename(RESERVOIR_VARS[res_var])

try:
    weekly = weather_weekly_with_progress(region, start.year, min(end.year, pd.Timestamp.today().year))
except Exception as exc:
    st.error(f"Weather could not be loaded: {exc}")
    st.stop()
weather = weekly[met_var].rename(WEATHER_LABELS[met_var])
if reservoir.dropna().empty or weather.dropna().empty:
    st.warning("No overlapping data in the chosen time frame.")
    st.stop()

# Highlighted window: the lecture's "centre" slider
dates = reservoir.index
centre = st.select_slider("Highlight window around", options=list(dates), value=dates[len(dates) // 2],
                          format_func=lambda d: f"{d:%d.%m.%Y}")
st.plotly_chart(swc_figure(reservoir, weather, window, lag, centre), width="stretch")

with st.expander("Correlation over the whole time frame for every lag"):
    lags = lagged_correlation(reservoir, weather, max_lag=52)
    fig = px.bar(lags.reset_index(), x="lag (weeks)", y="correlation", title="Correlation vs lag")
    fig.update_yaxes(range=[-1, 1])
    st.plotly_chart(fig, width="stretch")
    st.caption(f"Strongest absolute correlation at a lag of {int(lags.abs().idxmax())} weeks "
               f"(r = {lags.loc[lags.abs().idxmax()]:.2f}).")
