"""Cached loaders for Streamlit (the only module besides the pages that imports Streamlit).

Caching strategy (part 4):
* st.cache_data   - data frames from APIs/MongoDB, with a time-to-live (ttl)
                    so new data appear without restarting the app.
* st.cache_resource - the MongoDB client (one connection shared by all users).
* MongoDB itself  - weather is stored per region and year (collection
                    "weather_hourly"), so open-meteo is asked only once ever.
"""
import pandas as pd
import streamlit as st

from modules import api, currency, db, regions, weather
from modules.analysis import add_area_names
from modules.config import get_secrets
from modules.helpers import prepare_reservoir_df
from modules.regions import N_POINTS_HISTORY, N_POINTS_YEAR, POINTS_FILE


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


def _collection(name: str):
    return get_mongo()[get_secrets()["mongo"]["database"]][name]


@st.cache_data(ttl=3600, show_spinner="Reading flow data from MongoDB...")
def load_flows() -> pd.DataFrame:
    """Monthly cross-border flow documents curated by Spark in the notebook."""
    docs = _collection("entsoe_flows_monthly").find({}, {"_id": 0})
    return pd.DataFrame(list(docs))


@st.cache_data(show_spinner="Reading sample locations...")
def load_points() -> pd.DataFrame:
    """The 1000 random locations per region, sampled in the notebook.

    Read from MongoDB (collection sample_points). If MongoDB is unreachable the
    copy in data/sample_points.csv (same content, committed to GitHub) is used.
    """
    try:
        docs = list(_collection("sample_points").find({}, {"_id": 0}))
        if docs:
            return pd.DataFrame(docs)
    except Exception:
        pass
    return pd.read_csv(POINTS_FILE)


@st.cache_data(ttl=24 * 3600, show_spinner="Getting ERA5 weather (downloaded from open-meteo the first time)...")
def load_weather_year(region: str, year: int, n_locations: int = N_POINTS_YEAR) -> pd.DataFrame:
    """Hourly regional mean weather for one region and year.

    Read from MongoDB; only downloaded from open-meteo (and stored) the first time.
    If MongoDB is down, the data are downloaded directly so the page still works.
    """
    from pymongo.errors import PyMongoError

    points = load_points()
    try:
        collection = _collection("weather_hourly")
        return weather.year_from_store(collection, region, year, points, n_locations)
    except (PyMongoError, KeyError, RuntimeError) as exc:
        if "open-meteo" in str(exc):
            raise                                        # rate limit: let the page explain it
        # MongoDB missing or unreachable: download directly (not stored)
        start, end = f"{year}-01-01", weather._year_end(year).isoformat()
        return weather.regional_mean(weather.download_weather(region, start, end, points, n_locations))


@st.cache_data(ttl=24 * 3600, show_spinner=False)
def load_weather_weekly(region: str, first_year: int, last_year: int) -> pd.DataFrame:
    """Weekly weather (NVE weeks) for several years, from the stored yearly documents."""
    parts = [load_weather_year(region, y, N_POINTS_HISTORY) for y in range(first_year, last_year + 1)]
    return weather.to_weekly(pd.concat(parts).sort_index())


def weather_weekly_with_progress(region: str, first_year: int, last_year: int) -> pd.DataFrame:
    """Same as load_weather_weekly, but shows a progress bar while years are fetched.

    Years already in MongoDB/cache return immediately; a missing year can take
    a minute (open-meteo's per-minute limit), so the user sees how far it has come.
    """
    years = list(range(first_year, last_year + 1))
    bar = st.progress(0.0, text="Getting weather history...")
    for k, year in enumerate(years):
        bar.progress(k / len(years), text=f"Getting weather for {year} ({k + 1} of {len(years)})...")
        load_weather_year(region, year, N_POINTS_HISTORY)
    bar.empty()
    return load_weather_weekly(region, first_year, last_year)


@st.cache_data(ttl=24 * 3600, show_spinner="Downloading exchange rates from Norges Bank...")
def load_exchange_rates(start: str = "2010-01-01") -> pd.DataFrame:
    """Daily NOK per EUR and USD, straight from Norges Bank's API (cached for a day)."""
    return currency.fetch_exchange_rates(("EUR", "USD"), start)


@st.cache_data(show_spinner=False)
def load_geojson(area_type: str) -> dict:
    """Map outlines for one area type (converted from the shapefiles in the notebook)."""
    return regions.read_geojson(area_type)
