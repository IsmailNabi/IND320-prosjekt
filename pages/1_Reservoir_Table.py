"""Page 1: table with one row per area and a LineChartColumn sparkline."""
import streamlit as st

from modules.analysis import filter_interval, month_options, sparkline_table
from modules.data_loader import load_reservoirs
from modules.helpers import AREA_TYPES, METRIC_LABELS

st.title("Reservoir table")
df = load_reservoirs()

# Radio buttons choose the area type -> one table row per area number of that type
area_type = st.radio("Area type", list(AREA_TYPES), format_func=AREA_TYPES.get, horizontal=True)
type_df = df[df["area_type"] == area_type]

# The slider decides which part of the downloaded data is used (default: first month)
months = month_options(type_df)
first, last = st.select_slider("Month interval", options=months, value=(months[0], months[0]))
metric = st.selectbox("Metric for the trend column", list(METRIC_LABELS), format_func=METRIC_LABELS.get)

table = sparkline_table(filter_interval(type_df, first, last), metric)

st.dataframe(
    table,
    hide_index=True,
    use_container_width=True,
    column_config={
        "Area": st.column_config.TextColumn("Area"),
        "Trend": st.column_config.LineChartColumn(f"{METRIC_LABELS[metric]} ({first} to {last})"),
        "Min": st.column_config.NumberColumn(format="%.3f"),
        "Max": st.column_config.NumberColumn(format="%.3f"),
        "Mean": st.column_config.NumberColumn(format="%.3f"),
    },
)
st.caption("Source: NVE Magasinstatistikk API (weekly values).")
