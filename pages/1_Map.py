"""Explore: interactive map of the Magasinstatistikk areas.

* GeoJSON outlines (converted from the NVE shapefiles in the part 4 notebook).
* Colour by filling degree (price areas or water areas) or by a weather property.
* The TIME FRAME slider sets the global period (also used by the forecast page).
* Clicking an area selects it for all pages and gives it a thick, contrasting outline.
"""
from datetime import date, timedelta

import branca.colormap as cm
import folium
import pandas as pd
import streamlit as st
from streamlit_folium import st_folium

from modules.data_loader import load_geojson, load_reservoirs, load_weather_year
from modules.regions import N_POINTS_HISTORY
from modules.selectors import get_period, select_area, selected_area, set_period
from modules.theme import ACCENT, page_header
from modules.weather import WEATHER_LABELS, to_weekly

page_header("Map & time frame", "Explore",
            "Click an area to select it for all pages. The time frame is shared with the forecast page.")
df = load_reservoirs()
sel_type, sel_number, _ = selected_area()

# ---- controls -------------------------------------------------------------------
c1, c2, c3 = st.columns([1, 1, 2])
LAYERS = {"EL": "Price areas", "VASS": "Water areas", "NO": "Norway"}
layer = c1.radio("Areas", list(LAYERS), format_func=LAYERS.get, index=list(LAYERS).index(sel_type),
                 horizontal=True)
colour_by = c2.selectbox("Colour by", ["filling_degree"] + list(WEATHER_LABELS),
                         format_func=lambda v: "Filling degree (reservoirs)" if v == "filling_degree"
                         else WEATHER_LABELS[v])
start, end = get_period()
period = c3.slider("Time frame", min_value=date(1995, 1, 1), max_value=date.today(),
                   value=(start, end), step=timedelta(weeks=1), format="DD.MM.YYYY")
if period != (start, end):
    set_period(*period)
start, end = period

# ---- values per area ------------------------------------------------------------
areas = df[df["area_type"] == layer]
end_ts = pd.Timestamp(end)
if colour_by == "filling_degree":
    # filling degree in the last NVE week of the time frame
    week = areas[areas["date"] <= end_ts]["date"].max()
    values = areas[areas["date"] == week].set_index("area_number")["filling_degree"]
    legend = f"Filling degree, week ending {week:%d.%m.%Y}"
else:
    # weather property, weekly values averaged over the last 4 weeks of the time frame
    span = c3.select_slider("Weather aggregated over", [1, 4, 13], value=4,
                            format_func=lambda w: f"last {w} week(s) of the time frame")
    first = end_ts - pd.Timedelta(weeks=span)
    years = sorted({first.year, end_ts.year})
    values = {}
    with st.spinner("Getting weather for each area (downloaded once, then stored in MongoDB)..."):
        try:
            for number in sorted(areas["area_number"].unique()):
                hourly = pd.concat([load_weather_year(f"{layer}-{number}", y, N_POINTS_HISTORY) for y in years])
                weekly = to_weekly(hourly)[colour_by]
                values[number] = weekly[(weekly.index > first) & (weekly.index <= end_ts)].mean()
        except Exception as exc:
            st.error(f"Weather could not be loaded ({exc}). Showing outlines only.")
    values = pd.Series(values, dtype=float)
    legend = f"{WEATHER_LABELS[colour_by]}, mean of weeks {first:%d.%m}–{end_ts:%d.%m.%Y}"

# ---- map ------------------------------------------------------------------------
geo = load_geojson(layer)
valid = values.dropna()
# Viridis: perceptually uniform and readable with colour vision deficiency
colormap = (cm.LinearColormap(["#440154", "#3B528B", "#21918C", "#5EC962", "#FDE725"],
                              vmin=valid.min(), vmax=valid.max(), caption=legend)
            if len(valid) and valid.min() < valid.max() else None)


def style(feature):
    """Transparent fill by value; the selected area gets a thick contrasting outline,
    the others are toned down ("focus and defocus", lecture "Colours and symbols")."""
    props = feature["properties"]
    value = values.get(props["area_number"])
    chosen = props["area_type"] == sel_type and props["area_number"] == sel_number
    return {
        "fillColor": colormap(value) if colormap is not None and pd.notna(value) else "#CCCCCC",
        "fillOpacity": 0.7 if chosen else 0.4,
        "color": ACCENT if chosen else "#33505F",
        "weight": 5 if chosen else 1.2,
    }


for feature in geo["features"]:                          # value shown in the tooltip
    v = values.get(feature["properties"]["area_number"])
    feature["properties"]["value"] = "–" if pd.isna(v) else f"{v:.2f}"

m = folium.Map(location=[65, 14], zoom_start=4, tiles="OpenStreetMap")
folium.GeoJson(geo, style_function=style, highlight_function=lambda f: {"weight": 3, "color": ACCENT},
               tooltip=folium.GeoJsonTooltip(["name", "value"], aliases=["Area", "Value"])).add_to(m)
if colormap is not None:
    colormap.add_to(m)

left, right = st.columns([3, 1])
with left:
    out = st_folium(m, height=620, use_container_width=True, key=f"map_{layer}",
                    returned_objects=["last_active_drawing", "last_clicked"])
# st_folium keeps returning the LAST click, also after the area was changed in the
# sidebar. Only a click at a new position counts as a new selection.
out = out or {}
click_pos = out.get("last_clicked")
if out.get("last_active_drawing") and click_pos and click_pos != st.session_state.get("map_click"):
    st.session_state["map_click"] = click_pos
    props = out["last_active_drawing"]["properties"]
    if (props["area_type"], props["area_number"]) != (sel_type, sel_number):
        select_area(props["area_type"], props["area_number"])   # reruns with the new selection

with right:
    st.metric("Selected area", df.loc[(df["area_type"] == sel_type) & (df["area_number"] == sel_number),
                                      "name"].iloc[0])
    st.metric("Time frame", f"{(end - start).days // 7} weeks")
    st.dataframe(pd.DataFrame({"Area": [f["properties"]["name"] for f in geo["features"]],
                               "Value": [f["properties"]["value"] for f in geo["features"]]}),
                 hide_index=True, width="stretch")

with st.expander("About the map"):
    st.markdown(
        "Outlines: price areas (*Budområder*) and NVE regions from atlas.nve.no, converted to GeoJSON. "
        "Water areas follow the TA feedback: East = RS + RØ and the North region RM + RN is used for the "
        "weather of both VASS3 and VASS4 (drawn as RM and RN so they can be clicked separately). "
        "Weather: ERA5 from open-meteo, mean of 20 sampled points per area."
    )
