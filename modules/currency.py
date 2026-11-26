"""Exchange rates from Norges Bank (NB) (no Streamlit imports).

API docs: https://app.norges-bank.no/query/index.html#/en/
The data set EXR holds the official exchange rates. A series key is
FREQ.BASE_CUR.QUOTE_CUR.TENOR, e.g. B.EUR.NOK.SP = business-daily NOK per EUR, spot.
No API key is needed.

Time: NB publishes one rate per business day, fixed around 14:15 Norwegian time.
The dates carry no time zone, and weekends/holidays have no rate.
"""
import io

import pandas as pd
import requests

NB_URL = "https://data.norges-bank.no/api/data/EXR/B.{currencies}.NOK.SP"


def fetch_exchange_rates(currencies=("EUR", "USD"), start: str = "2015-01-01",
                         end: str | None = None) -> pd.DataFrame:
    """Download daily exchange rates (NOK per 1 unit of each currency) from Norges Bank.

    Parameters
    ----------
    currencies : currency codes, e.g. ("EUR", "USD")
    start, end : "YYYY-MM-DD"; end=None means up to today

    Returns a DataFrame indexed by date with one column per currency.
    """
    params = {"format": "csv", "startPeriod": start, "locale": "en"}
    if end:
        params["endPeriod"] = end
    resp = requests.get(NB_URL.format(currencies="+".join(currencies)), params=params, timeout=60)
    resp.raise_for_status()

    # NB's CSV is ';'-separated; read everything as text and convert ourselves
    raw = pd.read_csv(io.StringIO(resp.text), sep=None, engine="python", dtype=str)
    cols = {c.upper(): c for c in raw.columns}
    base = cols.get("BASE_CUR")
    period = cols.get("TIME_PERIOD")
    value = cols.get("OBS_VALUE")
    mult = cols.get("UNIT_MULT")
    if not (base and period and value):
        raise ValueError(f"Unexpected columns from Norges Bank: {list(raw.columns)}")

    rates = pd.DataFrame({
        "date": pd.to_datetime(raw[period]),
        "currency": raw[base],
        "rate": pd.to_numeric(raw[value].str.replace(",", "."), errors="coerce"),
    })
    if mult:                                   # e.g. JPY is quoted per 100 units
        rates["rate"] /= 10 ** pd.to_numeric(raw[mult], errors="coerce").fillna(0)
    table = rates.pivot_table(index="date", columns="currency", values="rate").sort_index()
    table.columns.name = None
    return table[[c for c in currencies if c in table.columns]]


def to_weekly(rates: pd.DataFrame) -> pd.DataFrame:
    """Daily business-day rates -> weekly means on NVE's weeks (ending Sunday)."""
    return rates.resample("W-SUN", label="right", closed="right").mean().dropna(how="all")
