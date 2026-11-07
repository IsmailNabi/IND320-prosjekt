"""Global area selector shown in the sidebar on every page (Streamlit).

Design choice (part 3): the area is a GLOBAL setting. The reservoir pages, the
STL/spectrogram page and the weather page all describe the same area, so the
user picks it once in the sidebar and it follows them between pages.
Page-specific settings (month interval, smoother lengths, DCT cut-off, ...)
stay LOCAL on each page because they only make sense there.

The values are kept in st.session_state["area_type"] and ["area_number"].
"""
import streamlit as st

from modules.helpers import AREA_TYPES
from modules.regions import region_key


def area_selector(reservoirs) -> None:
    """Draw the radio (area type) and selectbox (area) in the sidebar."""
    with st.sidebar:
        st.markdown("### Area (all pages)")
        area_type = st.radio("Area type", list(AREA_TYPES), format_func=AREA_TYPES.get, key="area_type")

        # Areas of the chosen type, e.g. EL -> 1..5 with names 'NO 1'..'NO 5'
        names = (reservoirs[reservoirs["area_type"] == area_type]
                 .drop_duplicates("area_number").set_index("area_number")["name"].sort_index())
        numbers = names.index.tolist()
        if st.session_state.get("area_number") not in numbers:   # type changed -> reset to first area
            st.session_state["area_number"] = numbers[0]
        st.selectbox("Area", numbers, format_func=lambda n: names[n], key="area_number",
                     help="Used by the analysis and weather pages. The table and plot pages show all areas of the type.")


def selected_area() -> tuple[str, int, str]:
    """(area_type, area_number, region key) chosen in the sidebar, e.g. ('EL', 3, 'EL-3')."""
    area_type = st.session_state.get("area_type", "EL")
    area_number = int(st.session_state.get("area_number", 1))
    return area_type, area_number, region_key(area_type, area_number)
