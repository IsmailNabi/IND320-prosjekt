"""Entry point: streamlit run main.py

Uses st.navigation so the sidebar menu is generated from the page list.
"""
import streamlit as st

st.set_page_config(page_title="IND320 - Energy App", layout="wide")


def home():
    """Landing page."""
    st.title("IND320 - Norwegian Reservoirs and Power Flows")
    st.markdown(
        """
        Use the sidebar menu to explore:

        * **Reservoir table** - one row per area with a trend sparkline
        * **Reservoir plots** - time series per area type or one area, with dates
        * **Cross-border flows** - ENTSO-E power exchange (pie chart and line plot)
        * **About & log** - links, work log and AI usage

        Reservoir data comes live from the NVE API. Flow data was fetched from
        ENTSO-E, processed with Cassandra and Spark, and is stored in MongoDB.
        """
    )


pages = {
    "Start": [st.Page(home, title="Home", icon="🏠", default=True)],
    "Reservoirs (NVE)": [
        st.Page("pages/1_Reservoir_Table.py", title="Reservoir table", icon="📊"),
        st.Page("pages/2_Reservoir_Plots.py", title="Reservoir plots", icon="📈"),
    ],
    "Power flows (ENTSO-E)": [
        st.Page("pages/3_Cross_Border_Flows.py", title="Cross-border flows", icon="🔌"),
    ],
    "Documentation": [
        st.Page("pages/4_About_and_Log.py", title="About & log", icon="📝"),
    ],
}
st.navigation(pages).run()
