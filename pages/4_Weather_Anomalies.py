"""Anomalies: outliers (SPC/SATV) and anomalies (LOF) in a chosen weather property.

Area: GLOBAL sidebar selector -> decides which weather data are used.
Year and weather property: LOCAL settings (part 4: property selectors, with
temperature as default for the SATV/SPC tab as the task asks).

The weather comes from MongoDB; a region/year that is not stored yet is
downloaded from open-meteo once (spinner) and stored, so no separate download
page is needed.
"""
from datetime import date

import streamlit as st

from modules.data_loader import load_points, load_reservoirs, load_weather_year
from modules.outliers import lof_anomalies, spc_outliers
from modules.regions import N_POINTS_YEAR, pick_locations
from modules.selectors import get_period, selected_area
from modules.theme import page_header
from modules.weather import WEATHER_LABELS

page_header("Weather outliers and anomalies", "Anomalies",
            f"Hourly ERA5 weather from open-meteo, mean of {N_POINTS_YEAR} sampled points in the area.")
df = load_reservoirs()
area_type, area_number, region = selected_area()
area_name = df.loc[(df["area_type"] == area_type) & (df["area_number"] == area_number), "name"].iloc[0]

# Year: local, default = the last full year inside the global time frame
_, end = get_period()
years = list(range(date.today().year, 1999, -1))
default_year = min(end.year, date.today().year - 1)
year = st.selectbox("Year", years, index=years.index(default_year))

try:
    hourly = load_weather_year(region, year)
except RuntimeError as exc:       # open-meteo daily limit
    st.error(f"open-meteo refused the download: {exc}. Try another year or come back tomorrow.")
    st.stop()
except Exception as exc:          # no network, MongoDB down, ...
    st.error(f"Weather data could not be loaded: {exc}")
    st.stop()
if hourly.empty:
    st.warning("No weather data for this year yet.")
    st.stop()

st.success(f"ERA5 data for **{area_name}**, {year}: {len(hourly)} hours.")
with st.expander("Locations used (random sample from the area)"):
    locations = pick_locations(load_points(), region, N_POINTS_YEAR)
    st.map(locations, latitude="lat", longitude="lon", size=4000)
    st.caption("Points lie in different ERA5 grid cells (0.25°). VASS3 and VASS4 share the North region (RM + RN).")

variables = [v for v in WEATHER_LABELS if v in hourly.columns]
tab_spc, tab_lof = st.tabs(["Outliers: SATV / SPC", "Anomalies: LOF"])

with tab_spc:
    c1, c2, c3, c4 = st.columns(4)
    var = c1.selectbox("Weather property", variables, index=variables.index("temperature_2m"),
                       format_func=WEATHER_LABELS.get, key="spc_var")
    cutoff = c2.slider("DCT cut-off (days)", 5, 120, 30,
                       help="Variation slower than this is treated as seasonal and removed (high-pass).")
    n_std = c3.slider("Number of robust SDs", 1.0, 6.0, 3.0, 0.5)
    resolution = c4.radio("Resolution", ["Hourly", "Daily"], horizontal=True)
    series = hourly[var].interpolate(limit=6)                   # fill short gaps, keep long ones as NaN
    label = WEATHER_LABELS[var]
    if resolution == "Daily":
        series = series.resample("D").sum() if var in ("precipitation", "rain", "snowfall") \
            else series.resample("D").mean()
    fig, stats, outliers = spc_outliers(series, cutoff_days=cutoff, n_std=n_std, title=label)
    st.plotly_chart(fig, width="stretch")
    left, right = st.columns([1, 2])
    left.dataframe(stats.astype(str).rename("value"), width="stretch")
    right.dataframe(outliers.sort_values("value", ascending=False), hide_index=True, width="stretch", height=320)
    st.caption("Limits = low-pass (seasonal) part + median ± k · 1.4826 · MAD of the high-pass values (SATV), "
               "moved back to the original scale. SATV itself is not plotted.")

with tab_lof:
    c1, c2, c3 = st.columns(3)
    var = c1.selectbox("Weather property", variables, index=variables.index("temperature_2m"),
                       format_func=WEATHER_LABELS.get, key="lof_var")
    contamination = c2.slider("Proportion of anomalies (%)", 0.1, 5.0, 1.0, 0.1) / 100
    neighbours = c3.slider("Number of neighbours", 5, 100, 20)
    fig, stats, anomalies = lof_anomalies(hourly[var].interpolate(limit=6), contamination, neighbours,
                                          title=WEATHER_LABELS[var])
    st.plotly_chart(fig, width="stretch")
    left, right = st.columns([1, 2])
    left.dataframe(stats.astype(str).rename("value"), width="stretch")
    right.dataframe(anomalies, hide_index=True, width="stretch", height=320)
    st.caption("LOF compares the local density of each hour (scaled time, scaled value) with its neighbours'. "
               "Score ≈ 1 is normal; the highest scores are the most unusual hours.")
