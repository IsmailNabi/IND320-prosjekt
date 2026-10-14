"""Data filtering and transformation used by notebook and Streamlit pages."""
import pandas as pd


def add_area_names(df: pd.DataFrame, areas: pd.DataFrame) -> pd.DataFrame:
    """Attach human-readable area names; fall back to 'TYPE number'."""
    out = df.merge(areas, on=["area_type", "area_number"], how="left")
    fallback = out["area_type"] + " " + out["area_number"].astype(str)
    out["name"] = out["name"].fillna(fallback)
    return out


def month_options(df: pd.DataFrame) -> list[str]:
    """Ordered list of 'YYYY-MM' labels present in the data."""
    return sorted(df["month"].dropna().unique().tolist())


def filter_interval(df: pd.DataFrame, first_month: str, last_month: str) -> pd.DataFrame:
    """Keep rows between two 'YYYY-MM' labels (inclusive)."""
    return df[(df["month"] >= first_month) & (df["month"] <= last_month)].copy()


def minmax_normalize(series: pd.Series) -> pd.Series:
    """Scale to 0-1 so columns with different units can share one axis."""
    span = series.max() - series.min()
    return (series - series.min()) / span if span else series * 0.0


def sparkline_table(df: pd.DataFrame, metric: str) -> pd.DataFrame:
    """One row per area: list of values over the period (for LineChartColumn) + stats."""
    rows = []
    for name, grp in df.sort_values("date").groupby("name"):
        values = grp[metric].dropna()
        rows.append({
            "Area": name,
            "Trend": values.tolist(),
            "Min": values.min(), "Max": values.max(), "Mean": values.mean(),
        })
    return pd.DataFrame(rows)


def flows_for_year(flows: pd.DataFrame, connection: str, year: int) -> pd.DataFrame:
    """Rows (one per month and direction) for one connection and year."""
    return flows[(flows["connection"] == connection) & (flows["year"] == year)]


def monthly_series(rows: pd.DataFrame, months: list[int]) -> pd.DataFrame:
    """Flatten stored month documents into a long table: direction, ts, mw."""
    parts = []
    for _, r in rows[rows["month"].isin(months)].iterrows():
        parts.append(pd.DataFrame({"direction": r["direction"], "ts": pd.to_datetime(r["ts"]), "mw": r["mw"]}))
    return pd.concat(parts, ignore_index=True) if parts else pd.DataFrame(columns=["direction", "ts", "mw"])
