"""API access: NVE Magasinstatistikk and ENTSO-E (no Streamlit imports)."""
import xml.etree.ElementTree as ET

import numpy as np
import pandas as pd
import requests

# ---------------------------------------------------------------- NVE
NVE_BASE = "https://biapi.nve.no/magasinstatistikk/api/Magasinstatistikk"


def fetch_reservoirs_raw() -> pd.DataFrame:
    """Download the full weekly reservoir statistics (all areas, since 1995)."""
    resp = requests.get(f"{NVE_BASE}/HentOffentligData", timeout=60)
    resp.raise_for_status()
    return pd.DataFrame(resp.json())


def _find_areas(obj):
    """Walk any nesting of lists/dicts and yield dicts that describe one area."""
    if isinstance(obj, dict):
        if "omrnr" in {k.lower() for k in obj}:      # this dict IS an area
            yield obj
        else:                                        # a group: look inside
            for value in obj.values():
                yield from _find_areas(value)
    elif isinstance(obj, list):
        for item in obj:
            yield from _find_areas(item)


def fetch_areas() -> pd.DataFrame:
    """Download area names. Returns columns area_type, area_number, name.

    The response nesting (flat list, or groups land/elspot/vassdrag) is
    handled by _find_areas; column names are matched case-insensitively.
    """
    resp = requests.get(f"{NVE_BASE}/HentOmr%C3%A5der", timeout=30)
    resp.raise_for_status()
    df = pd.DataFrame(list(_find_areas(resp.json())))
    df.columns = [c.lower() for c in df.columns]
    df = df.rename(columns={"omrtype": "area_type", "omrnr": "area_number", "navn": "name"})
    return df[["area_type", "area_number", "name"]].drop_duplicates()


# ------------------------------------------------------------- ENTSO-E
ENTSOE_URL = "https://web-api.tp.entsoe.eu/api"

# EIC codes of bidding zones
ZONES = {
    "NO1": "10YNO-1--------2", "NO2": "10YNO-2--------T", "NO3": "10YNO-3--------J",
    "NO4": "10YNO-4--------9", "NO5": "10Y1001A1001A48H",
    "SE1": "10Y1001A1001A44P", "SE2": "10Y1001A1001A45N", "SE3": "10Y1001A1001A46L",
    "DK1": "10YDK-1--------W", "FI": "10YFI-1--------U", "NL": "10YNL----------L",
    "DE_LU": "10Y1001A1001A82H", "GB": "10YGB----------A",
}

# Cross-border connections: (Norwegian zone, neighbouring zone)
CONNECTIONS = {
    "NO1 - SE3": ("NO1", "SE3"), "NO2 - DK1": ("NO2", "DK1"),
    "NO2 - NL": ("NO2", "NL"), "NO2 - DE_LU": ("NO2", "DE_LU"),
    "NO2 - GB": ("NO2", "GB"), "NO3 - SE2": ("NO3", "SE2"),
    "NO4 - SE1": ("NO4", "SE1"), "NO4 - SE2": ("NO4", "SE2"),
    "NO4 - FI": ("NO4", "FI"),
}

_RESOLUTION_MIN = {"PT15M": 15, "PT30M": 30, "PT60M": 60}


def _parse_flow_xml(xml_text: str) -> pd.Series:
    """Parse an ENTSO-E XML response into an hourly MW series (UTC).

    ENTSO-E may leave out points whose value is unchanged from the previous one
    (variable block curves). Every position in the period is therefore created
    first and gaps are forward-filled, otherwise those hours would be missing.
    """
    root = ET.fromstring(xml_text)
    if root.tag.endswith("Acknowledgement_MarketDocument"):  # 'no data' answer
        return pd.Series(dtype=float)
    pieces = []
    for period in root.findall(".//{*}Period"):
        start = pd.Timestamp(period.find("{*}timeInterval/{*}start").text)
        end = pd.Timestamp(period.find("{*}timeInterval/{*}end").text)
        step = pd.Timedelta(minutes=_RESOLUTION_MIN[period.find("{*}resolution").text])
        n = int((end - start) / step)                       # number of positions in the period
        values = pd.Series(np.nan, index=pd.date_range(start, periods=n, freq=step))
        for point in period.findall("{*}Point"):
            pos = int(point.find("{*}position").text)
            if 1 <= pos <= n:
                values.iloc[pos - 1] = float(point.find("{*}quantity").text)
        pieces.append(values.ffill())                       # unchanged value = previous value
    if not pieces:
        return pd.Series(dtype=float)
    series = pd.concat(pieces)
    series = series[~series.index.duplicated(keep="last")].sort_index()
    # Resolution can be 15 min or 60 min: average to hourly so MW sum = MWh
    return series.resample("1h").mean()


def fetch_flow(token: str, out_zone: str, in_zone: str, start: pd.Timestamp, end: pd.Timestamp) -> pd.Series:
    """Physical flow (A11) from out_zone to in_zone, one request per year (API limit)."""
    parts = []
    slice_start = start
    while slice_start < end:
        slice_end = min(slice_start + pd.DateOffset(years=1), end)
        params = {
            "securityToken": token, "documentType": "A11",
            "out_Domain": ZONES[out_zone], "in_Domain": ZONES[in_zone],
            "periodStart": slice_start.strftime("%Y%m%d%H%M"),
            "periodEnd": slice_end.strftime("%Y%m%d%H%M"),
        }
        resp = requests.get(ENTSOE_URL, params=params, timeout=60)
        if resp.status_code == 200:
            parts.append(_parse_flow_xml(resp.text))
        # other codes (e.g. 400 'no matching data') -> skip this slice
        slice_start = slice_end
    parts = [p for p in parts if not p.empty]
    return pd.concat(parts).sort_index() if parts else pd.Series(dtype=float)


def fetch_connection(token: str, name: str, start: pd.Timestamp, end: pd.Timestamp) -> pd.DataFrame:
    """Both directions of a connection as a long DataFrame: connection, direction, ts, mw.

    'export' = Norway -> neighbour, 'import' = neighbour -> Norway.
    """
    no_zone, other = CONNECTIONS[name]
    frames = []
    for direction, (out_z, in_z) in {"export": (no_zone, other), "import": (other, no_zone)}.items():
        s = fetch_flow(token, out_z, in_z, start, end)
        if not s.empty:
            df = s.rename("mw").rename_axis("ts").reset_index()
            df["ts"] = df["ts"].dt.tz_convert("UTC").dt.tz_localize(None)  # naive UTC
            df.insert(0, "direction", direction)
            df.insert(0, "connection", name)
            frames.append(df)
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame(
        columns=["connection", "direction", "ts", "mw"])