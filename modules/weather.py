"""open-meteo download of ERA5 reanalysis data and its MongoDB store (no Streamlit imports).

Docs: https://open-meteo.com/en/docs/historical-weather-api
The "Historical Weather" sub-section uses the archive endpoint below; choosing
"ERA5" under "Reanalysis models" adds models=era5 to the request.

Part 4: the regional mean for one region and year is stored as ONE document in
MongoDB (collection "weather_hourly"). Every page and the forecasting model read
from there, so open-meteo is only asked once per region and year.
"""
import time
from datetime import date, timedelta

import pandas as pd
import requests

from modules.regions import N_POINTS_YEAR, pick_locations

ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"

# Hourly variables: precipitation and temperature are required, the rest are
# relevant for hydropower (snow builds reservoirs, wind/cloud/pressure describe weather).
# Max 10 variables: more than 10 counts as extra API calls in open-meteo's quota.
HOURLY_VARIABLES = [
    "temperature_2m",          # °C
    "precipitation",           # mm (rain + snow water equivalent)
    "rain",                    # mm
    "snowfall",                # cm
    "relative_humidity_2m",    # %
    "wind_speed_10m",          # km/h
    "wind_gusts_10m",          # km/h
    "cloud_cover",             # %
    "surface_pressure",        # hPa
]

# Labels for menus and axes
WEATHER_LABELS = {
    "temperature_2m": "Temperature (°C)",
    "precipitation": "Precipitation (mm)",
    "rain": "Rain (mm)",
    "snowfall": "Snowfall (cm)",
    "relative_humidity_2m": "Relative humidity (%)",
    "wind_speed_10m": "Wind speed (km/h)",
    "wind_gusts_10m": "Wind gusts (km/h)",
    "cloud_cover": "Cloud cover (%)",
    "surface_pressure": "Surface pressure (hPa)",
}

# How each variable becomes a weekly value: amounts are summed, states are averaged
WEEKLY_AGG = {v: ("sum" if v in ("precipitation", "rain", "snowfall") else "mean") for v in HOURLY_VARIABLES}

LOCATIONS_PER_REQUEST = 10     # open-meteo accepts comma-separated lists of coordinates
ERA5_DELAY_DAYS = 7            # ERA5 is published with about 5 days delay


def _request(lats, lons, start: str, end: str, variables, retries: int = 6) -> list[dict]:
    """One API call for several locations.

    open-meteo answers HTTP 429 when the per-minute limit is reached, so we wait a
    minute and try again. A daily limit cannot be waited out and raises an error.
    """
    params = {
        "latitude": ",".join(f"{v:.5f}" for v in lats),
        "longitude": ",".join(f"{v:.5f}" for v in lons),
        "start_date": start, "end_date": end,
        "hourly": ",".join(variables),
        "models": "era5",
        "timezone": "GMT",      # UTC: no duplicated/missing hours at daylight saving changes
    }
    for _ in range(retries):
        resp = requests.get(ARCHIVE_URL, params=params, timeout=120)
        if resp.status_code == 429:
            reason = resp.json().get("reason", "") if resp.content else ""
            if "Daily" in reason or "Hourly" in reason:   # cannot be waited out here
                raise RuntimeError(f"open-meteo: {reason}")
            time.sleep(61)                                  # minutely limit -> wait it out
            continue
        resp.raise_for_status()
        data = resp.json()
        return data if isinstance(data, list) else [data]   # one location -> dict, several -> list
    raise RuntimeError("open-meteo rate limit: try again later or use fewer locations")


def download_weather(region: str, start: str, end: str, points: pd.DataFrame,
                     n_locations: int = N_POINTS_YEAR, variables=HOURLY_VARIABLES, seed: int = 0,
                     progress=None) -> pd.DataFrame:
    """Download hourly ERA5 data for a region and time interval.

    Parameters
    ----------
    region : region identifier, e.g. "EL-3" (= NO3) or "VASS-1", see modules.regions
    start, end : time interval as "YYYY-MM-DD" (inclusive)
    points : table of sampled locations (region, point_id, lon, lat)
    n_locations : how many of the region's sampled points to download (distinct ERA5 cells)
    progress : optional function(share_done) used to drive a progress bar

    Returns a long DataFrame: time, point_id, lon, lat, <one column per variable>.
    """
    locs = pick_locations(points, region, n_locations, seed)   # look up lon/lat pairs
    frames = []
    for i in range(0, len(locs), LOCATIONS_PER_REQUEST):
        chunk = locs.iloc[i:i + LOCATIONS_PER_REQUEST]
        results = _request(chunk["lat"], chunk["lon"], start, end, variables)
        for (_, loc), res in zip(chunk.iterrows(), results):
            df = pd.DataFrame(res["hourly"])
            df["time"] = pd.to_datetime(df["time"])
            df.insert(1, "point_id", loc["point_id"])
            df.insert(2, "lon", loc["lon"])
            df.insert(3, "lat", loc["lat"])
            frames.append(df)
        if progress:
            progress(min(1.0, (i + len(chunk)) / len(locs)))
    return pd.concat(frames, ignore_index=True)


def regional_mean(weather: pd.DataFrame) -> pd.DataFrame:
    """Average over all downloaded locations: one row per hour, indexed by time."""
    numeric = weather.drop(columns=["point_id", "lon", "lat"])
    return numeric.groupby("time").mean()


def to_weekly(hourly: pd.DataFrame) -> pd.DataFrame:
    """Hourly regional means -> weekly values on the same weeks as Magasinstatistikk.

    NVE dates each week by its last day (Sunday), so the weeks end on Sunday
    ("W-SUN", labelled by the right edge). Amounts are summed, states averaged.
    Incomplete weeks at the edges are dropped.
    """
    agg = {c: WEEKLY_AGG.get(c, "mean") for c in hourly.columns}
    weekly = hourly.resample("W-SUN", label="right", closed="right").agg(agg)
    hours = hourly.iloc[:, 0].resample("W-SUN", label="right", closed="right").count()
    return weekly[hours >= 7 * 24 - 2]                     # full weeks only (DST-safe)


# ------------------------------------------------------------- MongoDB store
def _year_end(year: int) -> date:
    """Last day with ERA5 data for a year (the current year is not finished)."""
    return min(date(year, 12, 31), date.today() - timedelta(days=ERA5_DELAY_DAYS))


def year_from_store(collection, region: str, year: int, points: pd.DataFrame,
                    n_locations: int = N_POINTS_YEAR, progress=None) -> pd.DataFrame:
    """Hourly regional mean for one region and year: from MongoDB, or downloaded once.

    One document per (region, year, number of points). For the running year the
    document is downloaded again when it is more than a week behind.
    """
    doc_id = f"{region}_{year}_n{n_locations}"
    end = _year_end(year)
    doc = collection.find_one({"_id": doc_id})
    if doc is None or pd.Timestamp(doc["end"]).date() < end - timedelta(days=7):
        raw = download_weather(region, f"{year}-01-01", end.isoformat(), points, n_locations,
                               progress=progress)
        mean = regional_mean(raw)
        doc = {"_id": doc_id, "region": region, "year": year, "n_points": n_locations,
               "end": end.isoformat(), "time": list(mean.index.to_pydatetime())}
        doc.update({v: mean[v].round(4).tolist() for v in mean.columns})
        collection.replace_one({"_id": doc_id}, doc, upsert=True)
    values = {v: doc[v] for v in HOURLY_VARIABLES if v in doc}
    return pd.DataFrame(values, index=pd.DatetimeIndex(doc["time"], name="time"))


def history_from_store(collection, region: str, first_year: int, last_year: int,
                       points: pd.DataFrame, n_locations: int, progress=None) -> pd.DataFrame:
    """Several years of hourly regional means (one stored document per year)."""
    years = list(range(first_year, last_year + 1))
    parts = []
    for k, year in enumerate(years):
        step = (lambda share, k=k: progress((k + share) / len(years))) if progress else None
        parts.append(year_from_store(collection, region, year, points, n_locations, step))
    return pd.concat(parts).sort_index()
