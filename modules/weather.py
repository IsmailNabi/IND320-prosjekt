"""open-meteo download of ERA5 reanalysis data (no Streamlit imports).

Docs: https://open-meteo.com/en/docs/historical-weather-api
The "Historical Weather" sub-section uses the archive endpoint below; choosing
"ERA5" under "Reanalysis models" adds models=era5 to the request.
"""
import time

import pandas as pd
import requests

from modules.regions import pick_locations

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

LOCATIONS_PER_REQUEST = 10     # open-meteo accepts comma-separated lists of coordinates


def _request(lats, lons, start: str, end: str, variables, retries: int = 4) -> list[dict]:
    """One API call for several locations. Retries with back-off on HTTP 429 (rate limit)."""
    params = {
        "latitude": ",".join(f"{v:.5f}" for v in lats),
        "longitude": ",".join(f"{v:.5f}" for v in lons),
        "start_date": start, "end_date": end,
        "hourly": ",".join(variables),
        "models": "era5",
        "timezone": "GMT",      # UTC: no duplicated/missing hours at daylight saving changes
    }
    for attempt in range(retries):
        resp = requests.get(ARCHIVE_URL, params=params, timeout=120)
        if resp.status_code == 429:                     # too many requests -> wait and retry
            time.sleep(15 * (attempt + 1))
            continue
        resp.raise_for_status()
        data = resp.json()
        return data if isinstance(data, list) else [data]   # one location -> dict, several -> list
    raise RuntimeError("open-meteo rate limit: try again later or use fewer locations")


def download_weather(region: str, start: str, end: str, points: pd.DataFrame,
                     n_locations: int = 10, variables=HOURLY_VARIABLES, seed: int = 0) -> pd.DataFrame:
    """Download hourly ERA5 data for a region and time interval.

    Parameters
    ----------
    region : region identifier, e.g. "EL-3" (= NO3) or "VASS-1", see modules.regions
    start, end : time interval as "YYYY-MM-DD" (inclusive)
    points : table of sampled locations (region, point_id, lon, lat)
    n_locations : how many of the region's sampled points to download (distinct ERA5 cells)

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
    return pd.concat(frames, ignore_index=True)


def regional_mean(weather: pd.DataFrame) -> pd.DataFrame:
    """Average over all downloaded locations: one row per hour, indexed by time."""
    numeric = weather.drop(columns=["point_id", "lon", "lat"])
    return numeric.groupby("time").mean()
