"""Page 6 (part 3): outliers (SPC) in precipitation and anomalies (LOF) in temperature.

Area: GLOBAL sidebar selector -> decides which weather data are downloaded.
The open-meteo download is integrated and hidden: it starts automatically,
is cached for 24 h and only a short confirmation is shown, so no separate
download page is needed. Year and number of locations are LOCAL settings.
"""
import matplotlib.pyplot as plt
import streamlit as st

from modules.data_loader import load_points, load_reservoirs, load_weather
from modules.outliers import lof_anomalies, spc_outliers
from modules.selectors import selected_area

st.title("Weather: outliers and anomalies")
df = load_reservoirs()
area_type, area_number, region = selected_area()
area_name = df.loc[(df["area_type"] == area_type) & (df["area_number"] == area_number), "name"].iloc[0]

c1, c2 = st.columns([1, 2])
year = c1.selectbox("Year", list(range(2025, 1999, -1)), index=1)   # default 2024, as in the notebook
n_locations = c2.slider("Number of sampled locations to average", 3, 20, 10,
                        help="Each location is a separate ERA5 time series. More = smoother average, slower download.")

try:
    hourly, locations = load_weather(region, year, n_locations)
except Exception as exc:   # no network, rate limit, ...
    st.error(f"Could not download weather data from open-meteo: {exc}")
    st.stop()

st.success(f"ERA5 data for **{area_name}**, {year}: {len(hourly)} hours, mean of {len(locations)} locations.")
with st.expander("Locations used (random sample from the region)"):
    st.map(locations, latitude="lat", longitude="lon", size=4000)
    st.caption(f"{len(load_points().query('region == @region'))} points were sampled in {area_name}; "
               "the ones used lie in different ERA5 grid cells (0.25°).")

tab_spc, tab_lof = st.tabs(["Outliers: precipitation (SPC)", "Anomalies: temperature (LOF)"])

with tab_spc:
    c1, c2, c3 = st.columns(3)
    cutoff = c1.slider("DCT cut-off (days)", 5, 120, 30,
                       help="Variation slower than this is treated as seasonal and removed (high-pass).")
    n_std = c2.slider("Number of robust SDs", 1.0, 6.0, 3.0, 0.5)
    resolution = c3.radio("Resolution", ["Hourly", "Daily"], horizontal=True,
                          help="Daily = sum per day. Hourly precipitation has many zero hours.")
    prec = hourly["precipitation"]
    label = "Precipitation (mm/h)"
    if resolution == "Daily":
        prec, label = prec.resample("D").sum(), "Precipitation (mm/day)"
    fig, stats, outliers = spc_outliers(prec, cutoff_days=cutoff, n_std=n_std, title=label)
    st.pyplot(fig)
    plt.close(fig)
    left, right = st.columns([1, 2])
    left.dataframe(stats.astype(str).rename("value"), width="stretch")
    right.dataframe(outliers.sort_values("value", ascending=False), hide_index=True,
                    width="stretch", height=320)
    st.caption("Limits = low-pass (seasonal) part + median ± k · 1.4826 · MAD of the high-pass values (SATV), "
               "moved back to the original scale. SATV itself is not plotted.")

with tab_lof:
    c1, c2 = st.columns(2)
    contamination = c1.slider("Proportion of anomalies (%)", 0.1, 5.0, 1.0, 0.1) / 100
    neighbours = c2.slider("Number of neighbours", 5, 100, 20)
    fig, stats, anomalies = lof_anomalies(hourly["temperature_2m"], contamination, neighbours,
                                          title="Temperature (°C)")
    st.pyplot(fig)
    plt.close(fig)
    left, right = st.columns([1, 2])
    left.dataframe(stats.astype(str).rename("value"), width="stretch")
    right.dataframe(anomalies, hide_index=True, width="stretch", height=320)
    st.caption("LOF compares the local density of each hour (scaled time, scaled temperature) with its neighbours'. "
               "Score ≈ 1 is normal; the highest scores are the most unusual hours.")

with st.expander("Data source and method"):
    st.markdown(
        "Hourly **ERA5 reanalysis** from the **open-meteo** archive API, downloaded on demand for the "
        "area chosen in the sidebar. Locations: 1000 random points per region sampled from NVE shapefiles "
        "(price areas and NVE regions, atlas.nve.no) and stored in MongoDB; a subset is averaged. "
        "Outlier methods: lecture notes *Outlier statistics* (SPC, MAD) and *Anomaly detection* (LOF)."
    )
