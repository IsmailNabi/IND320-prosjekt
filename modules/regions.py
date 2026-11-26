"""Regions, map shapes and random sample points.

Links the Magasinstatistikk areas (NO, EL, VASS) to polygons from the NVE
shapefiles (atlas.nve.no).

* EL 1-5   -> "Budområder" (NO 1 - NO 5), one-to-one.
* NO 0     -> all of Norway (union of all NVE regions).
* VASS 1-4 -> "NVE_Region" (RV, RM, RN, RØ, RS).

Part 4 (TA feedback on part 3): the precipitation regions are grouped as
East = RS + RØ and North = RM + RN (one combined North region). Weather for
VASS3 and VASS4 is therefore sampled from the same North region. On the map
the two areas are still drawn with their own outlines (RM and RN), so a user
can click on each of them.

geopandas is only needed in the notebook (sampling, GeoJSON export). The
Streamlit app reads the finished points from MongoDB/CSV and the map shapes
from data/geojson, so it never imports geopandas.
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SHAPE_DIR = ROOT / "data" / "shapefiles"
BUD_FILE = SHAPE_DIR / "budomrader" / "budomrader.shp"
REGION_FILE = SHAPE_DIR / "nve_region" / "NVE_Region.shp"
POINTS_FILE = ROOT / "data" / "sample_points.csv"
GEOJSON_DIR = ROOT / "data" / "geojson"

# Weather regions (where points are sampled): East = RØ+RS, North = RM+RN
VASS_WEATHER_REGIONS = {
    1: ["RØ", "RS"],   # Sørøst-Norge = East
    2: ["RV"],         # Vest-Norge   = West
    3: ["RM", "RN"],   # Midt-Norge   -> combined North
    4: ["RM", "RN"],   # Nord-Norge   -> combined North
}
# Map outlines (what the user clicks on): one shape per VASS area
VASS_MAP_REGIONS = {1: ["RØ", "RS"], 2: ["RV"], 3: ["RM"], 4: ["RN"]}

# All region keys used by the app/notebook, written as "TYPE-number", e.g. "EL-3"
REGION_KEYS = ["NO-0"] + [f"EL-{i}" for i in range(1, 6)] + [f"VASS-{i}" for i in range(1, 5)]

# Number of sampled points averaged per region (TA feedback: use more than 10).
# One point for one year costs ~26 calls of open-meteo's 10 000 free calls per day.
N_POINTS_YEAR = 50       # one year of hourly weather (outlier pages, map)
N_POINTS_HISTORY = 20    # several years of weather (forecasting history)


def region_key(area_type: str, area_number: int) -> str:
    """Build the region identifier used everywhere, e.g. ('EL', 3) -> 'EL-3'."""
    return f"{area_type}-{int(area_number)}"


def split_key(region: str) -> tuple[str, int]:
    """'EL-3' -> ('EL', 3)."""
    area_type, number = region.split("-")
    return area_type, int(number)


def load_region_polygons(kind: str = "weather"):
    """GeoDataFrame (EPSG:25833, metres) with one polygon per region key.

    kind="weather": VASS3 and VASS4 both use the combined North region (sampling).
    kind="map":     VASS3 = RM and VASS4 = RN (outlines on the map).
    """
    import geopandas as gpd  # imported here: only the notebook needs it

    bud = gpd.read_file(BUD_FILE)
    nve = gpd.read_file(REGION_FILE, encoding="utf-8")  # keeps 'RØ' readable
    vass = VASS_WEATHER_REGIONS if kind == "weather" else VASS_MAP_REGIONS

    rows = []
    for _, r in bud.iterrows():                             # 'NO 1' -> EL-1 ...
        number = int(str(r["budomr"]).replace("NO", "").strip())
        rows.append({"region": region_key("EL", number), "geometry": r.geometry})
    for number, codes in vass.items():
        geom = nve[nve["REGION"].isin(codes)].geometry.union_all()
        rows.append({"region": region_key("VASS", number), "geometry": geom})
    rows.append({"region": "NO-0", "geometry": nve.geometry.union_all()})

    return gpd.GeoDataFrame(rows, crs=bud.crs).set_index("region").loc[REGION_KEYS]


def export_geojson(names: dict | None = None, tolerance_m: float = 1000) -> dict:
    """Convert the map shapes to GeoJSON (one file per area type) for the Streamlit map.

    The outlines are simplified (tolerance in metres) so the files stay small and the
    map is fast, then converted to longitude/latitude (EPSG:4326) as GeoJSON requires.
    names: optional {region key: display name}. Returns {area type: file path}.
    """
    polygons = load_region_polygons("map")
    simple = polygons.copy()
    simple["geometry"] = simple.geometry.simplify(tolerance_m, preserve_topology=True)
    simple = simple.to_crs(4326).reset_index()
    simple["area_type"] = simple["region"].str.split("-").str[0]
    simple["area_number"] = simple["region"].str.split("-").str[1].astype(int)
    simple["name"] = simple["region"].map(names or {}).fillna(simple["region"])

    GEOJSON_DIR.mkdir(parents=True, exist_ok=True)
    files = {}
    for area_type, part in simple.groupby("area_type"):
        path = GEOJSON_DIR / f"{area_type}.geojson"
        path.write_text(part.to_json(drop_id=True))
        files[area_type] = path
    return files


def read_geojson(area_type: str) -> dict:
    """GeoJSON FeatureCollection for one area type (used by the app, no geopandas)."""
    return json.loads((GEOJSON_DIR / f"{area_type}.geojson").read_text())


def sample_points_in_polygon(polygon, n: int, rng: np.random.Generator) -> np.ndarray:
    """Uniform random points inside a polygon by rejection sampling.

    Draw points in the bounding box, keep those inside, repeat until n points.
    Returns an (n, 2) array of x, y in the polygon's CRS.
    """
    from shapely import contains_xy, prepare

    prepare(polygon)                      # speeds up many point-in-polygon tests
    xmin, ymin, xmax, ymax = polygon.bounds
    found = []
    while sum(len(f) for f in found) < n:
        x = rng.uniform(xmin, xmax, 5 * n)
        y = rng.uniform(ymin, ymax, 5 * n)
        inside = contains_xy(polygon, x, y)
        found.append(np.column_stack([x[inside], y[inside]]))
    return np.vstack(found)[:n]


def sample_region_points(polygons, n: int = 1000, seed: int = 320) -> pd.DataFrame:
    """Sample n random locations per region; returns region, point_id, lon, lat (WGS84)."""
    import geopandas as gpd

    rng = np.random.default_rng(seed)     # fixed seed -> reproducible points
    frames, drawn = [], {}
    for region, geom in polygons.geometry.items():
        # Regions with the same shape (VASS3 and VASS4 = North) get the SAME points,
        # so they also get exactly the same weather.
        key = geom.wkb
        if key not in drawn:
            drawn[key] = sample_points_in_polygon(geom, n, rng)
        xy = drawn[key]
        pts = gpd.GeoSeries(gpd.points_from_xy(xy[:, 0], xy[:, 1]), crs=polygons.crs).to_crs(4326)
        frames.append(pd.DataFrame({
            "region": region, "point_id": np.arange(n),
            "lon": pts.x.round(5), "lat": pts.y.round(5),
        }))
    return pd.concat(frames, ignore_index=True)


def era5_cell(lon: pd.Series, lat: pd.Series) -> pd.Series:
    """ERA5 grid cell id (0.25 degree grid). Points in the same cell give identical data."""
    return (lon / 0.25).round().astype(int).astype(str) + "_" + (lat / 0.25).round().astype(int).astype(str)


def pick_locations(points: pd.DataFrame, region: str, n_locations: int = N_POINTS_YEAR,
                   seed: int = 0) -> pd.DataFrame:
    """Choose n_locations of a region's 1000 points, at most one per ERA5 grid cell.

    Many of the 1000 points share an ERA5 cell (~25 km) and would return identical
    data, so picking distinct cells gives more information per API call.
    """
    pts = points[points["region"] == region].sample(frac=1, random_state=seed)  # shuffle
    pts = pts.assign(cell=era5_cell(pts["lon"], pts["lat"])).drop_duplicates("cell")
    return pts.head(n_locations).drop(columns="cell").reset_index(drop=True)
