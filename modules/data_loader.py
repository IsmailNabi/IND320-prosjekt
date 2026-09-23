import pandas as pd
import streamlit as st


@st.cache_data
def load_data(file_path: str = "data/reservoirs.csv") -> pd.DataFrame:
    """Loads reservoir dataset from CSV file and caches the result in memory."""
    try:
        df = pd.read_csv(file_path)
        return df
    except FileNotFoundError:
        st.error(f"Data file not found at path: {file_path}")
        return pd.DataFrame()


def get_data() -> pd.DataFrame:
    """Retrieves dataset from session state, or loads it if not already present."""
    if "df" not in st.session_state:
        st.session_state["df"] = load_data()

    return st.session_state["df"]