"""Page 3: ENTSO-E cross-border flows read from MongoDB (two columns)."""
import calendar

import matplotlib.pyplot as plt
import streamlit as st

from modules.analysis import flows_for_year, monthly_series
from modules.data_loader import load_flows

st.title("Cross-border power flows")

try:
    flows = load_flows()
except Exception as exc:  # missing secrets or no network to MongoDB
    st.error(f"Could not read from MongoDB: {exc}")
    st.stop()
if flows.empty:
    st.warning("The MongoDB collection is empty. Run the part 2 notebook first.")
    st.stop()

left, right = st.columns(2)

with left:
    st.subheader("Total flow in and out")
    connection = st.radio("Connection", sorted(flows["connection"].unique()))
    years = sorted(flows.loc[flows["connection"] == connection, "year"].unique())
    year = st.selectbox("Year", years, index=len(years) - 1)
    rows = flows_for_year(flows, connection, year)
    totals = rows.groupby("direction")["total_mwh"].sum() / 1000  # MWh -> GWh
    fig, ax = plt.subplots()
    ax.pie(totals, labels=totals.index, autopct="%1.1f%%", startangle=90)
    ax.set_title(f"{connection}, {year}: export vs import (GWh)")
    st.pyplot(fig)

with right:
    st.subheader("Hourly flow per direction")
    available = sorted(rows["month"].unique())
    months = st.pills(
        "Months", available, selection_mode="multi", default=available[:1],
        format_func=lambda m: calendar.month_abbr[m],
    )
    series = monthly_series(rows, months or [])
    if series.empty:
        st.info("Select at least one month.")
    else:
        fig, ax = plt.subplots()
        for direction, grp in series.groupby("direction"):
            ax.plot(grp["ts"], grp["mw"], label=direction)
        ax.set_xlabel("Time (UTC)")
        ax.set_ylabel("Flow (MW)")
        ax.set_title(f"{connection}, {year}")
        ax.legend()
        ax.grid(True, linestyle="--", alpha=0.5)
        fig.autofmt_xdate()
        st.pyplot(fig)

with st.expander("Data source"):
    st.markdown(
        "Physical cross-border flows (document type A11) from the **ENTSO-E Transparency "
        "Platform**, fetched with the REST API for the last two years, stored in Cassandra, "
        "aggregated with Spark and saved in MongoDB Atlas. *export* = Norway to neighbour, "
        "*import* = neighbour to Norway. Values are hourly averages in MW (hourly MW = MWh)."
    )
