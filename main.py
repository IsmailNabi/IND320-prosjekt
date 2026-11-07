"""Entry point: streamlit run main.py

Uses st.navigation so the sidebar menu is generated from the page list.
Part 3: a global area selector in the sidebar (modules/selectors.py) and two
new pages. The pages are grouped by data source and ordered from overview
(tables/plots) to analysis (decomposition, outliers).
"""
import streamlit as st

from modules.data_loader import load_reservoirs
from modules.selectors import area_selector

st.set_page_config(page_title="IND320 - Energy App", layout="wide")


def home():
    """Landing page."""
    st.title("IND320 - Norwegian Reservoirs, Weather and Power Flows")
    st.markdown(
        """
        Choose an **area** in the sidebar. It is used by all pages.

        **Reservoirs (NVE)**
        * **Reservoir table**: one row per area with a trend sparkline
        * **Reservoir plots**: time series per area type, with dates
        * **STL & spectrogram**: seasonal-trend decomposition and spectrogram of the filling degree

        **Weather (open-meteo, ERA5)**
        * **Outliers & anomalies**: SPC outliers in precipitation and LOF anomalies in temperature

        **Power flows (ENTSO-E)**
        * **Cross-border flows**: power exchange (pie chart and line plot)

        **Documentation**
        * **About**: links, how to use the app and data sources

        Reservoir data come live from the NVE API, weather data live from open-meteo
        (downloaded automatically for the chosen area). Flow data and the sampled
        weather locations are stored in MongoDB.
        """
    )


pages = {
    "Start": [st.Page(home, title="Home", icon="🏠", default=True)],
    "Reservoirs (NVE)": [
        st.Page("pages/1_Reservoir_Table.py", title="Reservoir table", icon="📊"),
        st.Page("pages/2_Reservoir_Plots.py", title="Reservoir plots", icon="📈"),
        st.Page("pages/5_Reservoir_Decomposition.py", title="STL & spectrogram", icon="🌀"),
    ],
    "Weather (open-meteo)": [
        st.Page("pages/6_Weather_Outliers.py", title="Outliers & anomalies", icon="🌧️"),
    ],
    "Power flows (ENTSO-E)": [
        st.Page("pages/3_Cross_Border_Flows.py", title="Cross-border flows", icon="🔌"),
    ],
    "Documentation": [
        st.Page("pages/4_About_and_Log.py", title="About", icon="📝"),
    ],
}

nav = st.navigation(pages)
area_selector(load_reservoirs())   # global sidebar selector, drawn below the menu on every page
nav.run()
