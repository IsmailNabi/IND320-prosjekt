"""Cached loaders for Streamlit (the only module that imports Streamlit)."""
import pandas as pd
import streamlit as st

from modules import api, db
from modules.config import get_secrets
from modules.analysis import add_area_names
from modules.helpers import prepare_reservoir_df


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
