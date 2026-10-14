"""Shared helper functions (no Streamlit imports, so usable in notebooks too).

Collects the code that was previously duplicated across pages:
column renaming, numeric cleaning and date handling.
"""
import pandas as pd

# Norwegian API/CSV column names -> clear English names (used everywhere)
COLUMN_MAPPING = {
    "dato_Id": "date",
    "omrType": "area_type",
    "omrnr": "area_number",
    "iso_aar": "iso_year",
    "iso_uke": "iso_week",
    "fyllingsgrad": "filling_degree",
    "kapasitet_TWh": "capacity_twh",
    "fylling_TWh": "filling_twh",
    "neste_Publiseringsdato": "next_publication_date",
    "fyllingsgrad_forrige_uke": "filling_degree_prev_week",
    "endring_fyllingsgrad": "change_filling_degree",
}

# Numeric columns that make sense to plot over time, with display labels
METRIC_LABELS = {
    "filling_degree": "Filling degree (fraction)",
    "capacity_twh": "Capacity (TWh)",
    "filling_twh": "Reservoir content (TWh)",
    "filling_degree_prev_week": "Filling degree, previous week",
    "change_filling_degree": "Change in filling degree",
}

# Area types in the NVE API: EL = price areas, NO = country, VASS = watercourses
AREA_TYPES = {"EL": "Price areas (EL)", "NO": "Norway (NO)", "VASS": "Watercourses (VASS)"}


def clean_numeric(series: pd.Series) -> pd.Series:
    """Convert strings with decimal commas to floats (invalid values -> NaN)."""
    return pd.to_numeric(series.astype(str).str.replace(",", "."), errors="coerce")


def date_from_iso_week(iso_year: pd.Series, iso_week: pd.Series) -> pd.Series:
    """Build a date (Monday of the ISO week) from ISO year and ISO week.

    Fallback for rows where the date column is missing or unparsable.
    """
    text = iso_year.astype(int).astype(str) + iso_week.astype(int).astype(str).str.zfill(2) + "1"
    return pd.to_datetime(text, format="%G%V%u", errors="coerce")


def prepare_reservoir_df(raw: pd.DataFrame) -> pd.DataFrame:
    """Rename columns, clean numerics, parse dates and sort chronologically."""
    df = raw.rename(columns=COLUMN_MAPPING).copy()
    for col in METRIC_LABELS:
        if col in df.columns:
            df[col] = clean_numeric(df[col])
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    # Fill missing dates from the ISO year/week columns (lesson from part 1)
    missing = df["date"].isna()
    if missing.any():
        df.loc[missing, "date"] = date_from_iso_week(
            df.loc[missing, "iso_year"], df.loc[missing, "iso_week"]
        )
    df["month"] = df["date"].dt.strftime("%Y-%m")
    return df.sort_values(["area_type", "area_number", "date"]).reset_index(drop=True)
