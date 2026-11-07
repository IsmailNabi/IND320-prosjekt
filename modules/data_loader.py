"""Cached loaders for Streamlit (the only module that imports Streamlit).

Part 3 adds load_points() and load_weather() at the bottom; the part 2
functions are unchanged.
"""
import pandas as pd
import streamlit as st

from modules import api, db, weather
from modules.analysis import add_area_names
from modules.config import get_secrets
from modules.helpers import prepare_reservoir_df
from modules.regions import POINTS_FILE


@st.cache_data(ttl=6 * 3600, show_spinner="Downloading reservoir data from NVE...")
def load_reservoirs() -> pd.DataFrame:
    """Reservoir statistics straight from the NVE API (cached for 6 hours)."""
    df = prepare_reservoir_df(api.fetch_reservoirs_raw())
    return add_area_names(df, api.fetch_areas())


@st.cache_resource
def get_mongo():
    """One MongoDB client per app. Credentials come from No_sync/secrets.toml or st.secrets, never from GitHub."""
    s = get_secrets()["mongo"]
    return db.get_client(db.build_uri(s["user"], s["password"], s["host"]))


@st.cache_data(ttl=3600, show_spinner="Reading flow data from MongoDB...")
def load_flows() -> pd.DataFrame:
    """Monthly cross-border flow documents curated by Spark in the notebook."""
    database = get_secrets()["mongo"]["database"]
    docs = get_mongo()[database]["entsoe_flows_monthly"].find({}, {"_id": 0})
    return pd.DataFrame(list(docs))


# ------------------------------------------------------------------ part 3
@st.cache_data(show_spinner="Reading sample locations...")
def load_points() -> pd.DataFrame:
    """The 1000 random locations per region, sampled in the part 3 notebook.

    Read from MongoDB (collection sample_points). If MongoDB is unreachable the
    copy in data/sample_points.csv (same content, committed to GitHub) is used.
    """
    try:
        database = get_secrets()["mongo"]["database"]
        docs = list(get_mongo()[database]["sample_points"].find({}, {"_id": 0}))
        if docs:
            return pd.DataFrame(docs)
    except Exception:
        pass
    return pd.read_csv(POINTS_FILE)


@st.cache_data(ttl=24 * 3600, show_spinner="Downloading ERA5 weather data from open-meteo...")
def load_weather(region: str, year: int, n_locations: int) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Hourly ERA5 data for one region and year, averaged over n_locations points.

    This is the "hidden" download: it is triggered automatically by the area
    selector and cached for 24 hours, so each region/year is only fetched once.
    Returns (hourly regional mean, table of the locations that were used).
    """
    raw = weather.download_weather(region, f"{year}-01-01", f"{year}-12-31", load_points(), n_locations)
    locations = raw[["point_id", "lon", "lat"]].drop_duplicates().reset_index(drop=True)
    return weather.regional_mean(raw), locations

