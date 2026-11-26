"""Entry point: streamlit run main.py

Part 4 structure (see the sketch in the part 4 notebook):

    Home
    ├── Explore      : Map & time frame, Reservoir overview
    ├── Anomalies    : STL & spectrogram, Weather outliers (SPC/LOF)
    ├── Prediction   : Weather vs reservoir correlation, Forecast
    ├── Markets      : Cross-border flows, Exchange rates
    └── About

st.navigation draws the grouped menu. The global area selector (and the time
frame set on the map page) is drawn in the sidebar on every page and stored in
st.session_state, so all pages follow the same selection.
"""
import streamlit as st

from modules import theme  # noqa: F401  (registers the Plotly template for all pages)
from modules.data_loader import load_reservoirs
from modules.selectors import area_selector
from modules.theme import GROUP_COLORS, page_header

st.set_page_config(page_title="IND320 - Energy App", page_icon="💧", layout="wide")

PAGES = {
    "Explore": [
        st.Page("pages/1_Map.py", title="Map & time frame", icon="🗺️"),
        st.Page("pages/2_Reservoir_Overview.py", title="Reservoir overview", icon="📊"),
    ],
    "Anomalies": [
        st.Page("pages/3_Decomposition.py", title="STL & spectrogram", icon="🌀"),
        st.Page("pages/4_Weather_Anomalies.py", title="Weather outliers", icon="🌧️"),
    ],
    "Prediction": [
        st.Page("pages/5_Correlation.py", title="Weather vs reservoir", icon="🔗"),
        st.Page("pages/6_Forecast.py", title="Forecast", icon="🔮"),
    ],
    "Markets": [
        st.Page("pages/7_Cross_Border_Flows.py", title="Cross-border flows", icon="🔌"),
        st.Page("pages/8_Exchange_Rates.py", title="Exchange rates", icon="💱"),
    ],
}
ABOUT = st.Page("pages/9_About.py", title="About", icon="📝")

DESCRIPTIONS = {
    "Explore": "Map of the areas, choose area and time frame; overview of the reservoir data.",
    "Anomalies": "Seasonal decomposition of reservoir filling; outliers and anomalies in the weather.",
    "Prediction": "How weather relates to reservoir filling, and forecasts of the coming months.",
    "Markets": "Power exchange with neighbouring countries and NOK exchange rates.",
}


def home():
    """Front page: one card per group, each pointing to its pages."""
    page_header("Norwegian reservoirs, weather and markets", "Start",
                "IND320 project · NVE Magasinstatistikk, open-meteo (ERA5), ENTSO-E and Norges Bank")
    st.markdown("Pick an **area** in the sidebar or click one on the map. The choice follows you to every page.")
    cols = st.columns(2)
    for k, (group, pages) in enumerate(PAGES.items()):
        with cols[k % 2].container(border=True):
            st.markdown(f"<h4 style='color:{GROUP_COLORS[group]};margin:0'>{group}</h4>",
                        unsafe_allow_html=True)
            st.caption(DESCRIPTIONS[group])
            for page in pages:
                st.page_link(page)


nav = st.navigation({"Start": [st.Page(home, title="Home", icon="🏠", default=True)], **PAGES,
                     "About": [ABOUT]})

# Global sidebar selector. If NVE cannot be reached, the app still opens with a message.
try:
    area_selector(load_reservoirs())
except Exception as exc:
    st.sidebar.error(f"Could not load reservoir data from NVE: {exc}")
nav.run()
