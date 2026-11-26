"""Explore: reservoir data overview (part 1-2 pages joined in part 4).

The LineChartColumn table and the time series plots show the same data, so they
are now two tabs on one page. The area type comes from the global sidebar
selection; the month interval is local and starts at the global time frame.
"""
import streamlit as st

from modules.analysis import filter_interval, minmax_normalize, month_options, sparkline_table
from modules.data_loader import load_reservoirs
from modules.helpers import AREA_TYPES, METRIC_LABELS
from modules.plots import reservoir_lines, reservoir_normalized
from modules.selectors import get_period, selected_area
from modules.theme import page_header

page_header("Reservoir overview", "Explore", "Weekly data from NVE Magasinstatistikk (live API).")
df = load_reservoirs()
area_type, area_number, _ = selected_area()
type_df = df[df["area_type"] == area_type]
st.caption(f"Area type: **{AREA_TYPES[area_type]}** (change it in the sidebar)")

# Month interval: local, but its default is the end of the global time frame
months = month_options(type_df)
_, end = get_period()
default_last = min(f"{end:%Y-%m}", months[-1])
default_first = months[max(0, months.index(default_last) - 11)] if default_last in months else months[0]
first, last = st.select_slider("Month interval", options=months, value=(default_first, default_last))
interval = filter_interval(type_df, first, last)

tab_table, tab_plot = st.tabs(["Table with trend lines", "Plots"])

with tab_table:
    metric = st.selectbox("Metric for the trend column", list(METRIC_LABELS), format_func=METRIC_LABELS.get)
    table = sparkline_table(interval, metric)
    st.dataframe(
        table, hide_index=True, width="stretch",
        column_config={
            "Area": st.column_config.TextColumn("Area"),
            "Trend": st.column_config.LineChartColumn(f"{METRIC_LABELS[metric]} ({first} to {last})"),
            "Min": st.column_config.NumberColumn(format="%.3f"),
            "Max": st.column_config.NumberColumn(format="%.3f"),
            "Mean": st.column_config.NumberColumn(format="%.3f"),
        },
    )

with tab_plot:
    ALL = "All columns together (selected area, normalized)"
    choice = st.selectbox("Column", list(METRIC_LABELS) + [ALL], format_func=lambda c: METRIC_LABELS.get(c, c))
    if choice == ALL:
        # Different units -> one area, every column scaled to 0-1
        area_df = interval[interval["area_number"] == area_number].sort_values("date")
        st.plotly_chart(reservoir_normalized(area_df, METRIC_LABELS, minmax_normalize), width="stretch")
        st.caption("Normalization removes units, so compare shapes, not levels.")
    else:
        st.plotly_chart(reservoir_lines(interval, choice, METRIC_LABELS[choice]), width="stretch")
