"""Regions and random sample points (part 3).

Links the Magasinstatistikk areas (NO, EL, VASS) to polygons from the NVE
shapefiles (atlas.nve.no) and samples random locations inside each region.

* EL 1-5  -> "Budområder" shapefile (NO 1 - NO 5), one-to-one.
* VASS 1-4 -> "NVE_Region" shapefile. The task says "East is split into RS+RØ,
  and North is split into RM+RN". Using the area descriptions from the
  HentOmråder endpoint this gives:
      VASS1 Sørøst-Norge = RØ + RS
      VASS2 Vest-Norge   = RV
      VASS3 Midt-Norge   = RM
      VASS4 Nord-Norge   = RN
  (Small mismatch: VASS3 includes southern Nordland, which lies in RN.)
* NO 0 (whole country) -> union of all five NVE regions.

geopandas is only needed to SAMPLE the points (notebook). The Streamlit app
reads the finished points from MongoDB / CSV, so it never imports geopandas.
"""
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SHAPE_DIR = ROOT / "data" / "shapefiles"
BUD_FILE = SHAPE_DIR / "budomrader" / "budomrader.shp"
REGION_FILE = SHAPE_DIR / "nve_region" / "NVE_Region.shp"
POINTS_FILE = ROOT / "data" / "sample_points.csv"

# Magasinstatistikk area -> list of NVE region codes (column REGION in NVE_Region.shp)
VASS_TO_NVE_REGIONS = {
    1: ["RØ", "RS"],   # Sørøst-Norge ("East is split into RS+RØ")
    2: ["RV"],         # Vest-Norge
    3: ["RM"],         # Midt-Norge   ("North is split into RM+RN")
    4: ["RN"],         # Nord-Norge
}

# All region keys used by the app/notebook, written as "TYPE-number", e.g. "EL-3"
REGION_KEYS = ["NO-0"] + [f"EL-{i}" for i in range(1, 6)] + [f"VASS-{i}" for i in range(1, 5)]


def region_key(area_type: str, area_number: int) -> str:
    """Build the region identifier used everywhere, e.g. ('EL', 3) -> 'EL-3'."""
    return f"{area_type}-{int(area_number)}"


def load_region_polygons():
    """Return a GeoDataFrame (EPSG:25833, metres) with one polygon per region key.

    EPSG:25833 is the CRS of both shapefiles. Sampling is done in metres so
    that every square km has the same chance of being picked.
    """
    import geopandas as gpd  # imported here: only the notebook needs it

    bud = gpd.read_file(BUD_FILE)
    nve = gpd.read_file(REGION_FILE, encoding="utf-8")  # keeps 'RØ' readable

    rows = []
    # EL: 'NO 1' -> EL-1 ... 'NO 5' -> EL-5
    for _, r in bud.iterrows():
        number = int(str(r["budomr"]).replace("NO", "").strip())
        rows.append({"region": region_key("EL", number), "geometry": r.geometry})
    # VASS: merge the NVE regions listed in VASS_TO_NVE_REGIONS
    for number, codes in VASS_TO_NVE_REGIONS.items():
        geom = nve[nve["REGION"].isin(codes)].geometry.union_all()
        rows.append({"region": region_key("VASS", number), "geometry": geom})
    # NO: the whole country
    rows.append({"region": "NO-0", "geometry": nve.geometry.union_all()})

    return gpd.GeoDataFrame(rows, crs=bud.crs).set_index("region").loc[REGION_KEYS]


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
    frames = []
    for region, geom in polygons.geometry.items():
        xy = sample_points_in_polygon(geom, n, rng)
        pts = gpd.GeoSeries(gpd.points_from_xy(xy[:, 0], xy[:, 1]), crs=polygons.crs).to_crs(4326)
        frames.append(pd.DataFrame({
            "region": region, "point_id": np.arange(n),
            "lon": pts.x.round(5), "lat": pts.y.round(5),
        }))
    return pd.concat(frames, ignore_index=True)


def era5_cell(lon: pd.Series, lat: pd.Series) -> pd.Series:
    """ERA5 grid cell id (0.25 degree grid). Points in the same cell give identical data."""
    return (lon / 0.25).round().astype(int).astype(str) + "_" + (lat / 0.25).round().astype(int).astype(str)


def pick_locations(points: pd.DataFrame, region: str, n_locations: int = 10, seed: int = 0) -> pd.DataFrame:
    """Choose n_locations of a region's 1000 points, at most one per ERA5 grid cell.

    Downloading all 1000 points would exceed open-meteo's free daily quota and many
    points share the same ~25 km ERA5 cell anyway, so a random subset of distinct
    cells gives practically the same regional average at a fraction of the cost.
    """
    pts = points[points["region"] == region].sample(frac=1, random_state=seed)  # shuffle
    pts = pts.assign(cell=era5_cell(pts["lon"], pts["lat"])).drop_duplicates("cell")
    return pts.head(n_locations).drop(columns="cell").reset_index(drop=True)
