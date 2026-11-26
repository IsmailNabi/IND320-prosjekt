"""Selections shared by all pages (Streamlit session state).

Design (parts 3-4):
* AREA is global. It is chosen in the sidebar or by clicking on the map, and
  every page that shows one area uses it.
* PERIOD (time frame) is global too. It is chosen on the map page and reused as
  the training period of the forecast page, so the two stay in sync.
* Settings that only make sense on one page (smoother lengths, DCT cut-off,
  model parameters, ...) stay local on that page.

Streamlit does not allow changing a widget's value after the widget is drawn
in the same run, so a map click stores a "pending" area and reruns the app;
the sidebar applies it before drawing its widgets.
"""
from datetime import date

import streamlit as st

from modules.helpers import AREA_TYPES
from modules.regions import region_key


def area_selector(reservoirs) -> None:
    """Draw the radio (area type) and selectbox (area) in the sidebar."""
    pending = st.session_state.pop("pending_area", None)
    if pending:                                           # set by a click on the map
        st.session_state["area_type"], st.session_state["area_number"] = pending

    with st.sidebar:
        st.markdown("### Area (all pages)")
        area_type = st.radio("Area type", list(AREA_TYPES), format_func=AREA_TYPES.get, key="area_type")

        # Areas of the chosen type, e.g. EL -> 1..5 with names 'NO 1'..'NO 5'
        names = (reservoirs[reservoirs["area_type"] == area_type]
                 .drop_duplicates("area_number").set_index("area_number")["name"].sort_index())
        numbers = names.index.tolist()
        if st.session_state.get("area_number") not in numbers:   # type changed -> first area
            st.session_state["area_number"] = numbers[0]
        st.selectbox("Area", numbers, format_func=lambda n: names[n], key="area_number",
                     help="Also set by clicking an area on the map.")
        start, end = get_period()
        st.caption(f"Time frame: {start:%d.%m.%Y} – {end:%d.%m.%Y} (set on the map page)")


def select_area(area_type: str, area_number: int) -> None:
    """Change the global area from code (e.g. a map click) and redraw the app."""
    st.session_state["pending_area"] = (area_type, int(area_number))
    st.rerun()


def selected_area() -> tuple[str, int, str]:
    """(area_type, area_number, region key) chosen in the sidebar, e.g. ('EL', 3, 'EL-3')."""
    area_type = st.session_state.get("area_type", "EL")
    area_number = int(st.session_state.get("area_number", 1))
    return area_type, area_number, region_key(area_type, area_number)


def get_period() -> tuple[date, date]:
    """Global time frame (start, end). Default: the last eight years up to today."""
    if "period" not in st.session_state:
        today = date.today()
        st.session_state["period"] = (date(today.year - 8, 1, 1), today)
    return st.session_state["period"]


def set_period(start: date, end: date) -> None:
    st.session_state["period"] = (start, end)
