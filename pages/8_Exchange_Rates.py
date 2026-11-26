"""Markets: NOK exchange rates (EUR, USD) straight from Norges Bank's API.

The rates can be used as exogenous variables in the forecast. They are
business-daily; the weekly view uses the same weeks as Magasinstatistikk.
"""
import pandas as pd
import streamlit as st

from modules.currency import to_weekly
from modules.data_loader import load_exchange_rates
from modules.plots import exchange_rates
from modules.selectors import get_period
from modules.theme import page_header

page_header("Exchange rates", "Markets", "NOK per EUR and per USD from Norges Bank (live API, cached for a day).")
start, end = get_period()

try:
    rates = load_exchange_rates(f"{start.year}-01-01")
except Exception as exc:
    st.error(f"Norges Bank could not be reached: {exc}")
    st.stop()

resolution = st.radio("Resolution", ["Daily (business days)", "Weekly (NVE weeks)"], horizontal=True)
shown = rates if resolution.startswith("Daily") else to_weekly(rates)
shown = shown.loc[pd.Timestamp(start):pd.Timestamp(end)]
if shown.empty:
    st.warning("No rates in the chosen time frame.")
    st.stop()

st.plotly_chart(exchange_rates(shown), width="stretch")
c1, c2 = st.columns(2)
for col, cur in zip((c1, c2), shown.columns):
    change = shown[cur].iloc[-1] / shown[cur].iloc[0] - 1
    col.metric(f"NOK per {cur}, {shown.index[-1]:%d.%m.%Y}", f"{shown[cur].iloc[-1]:.3f}", f"{change:+.1%} in time frame")

with st.expander("Data source and time"):
    st.markdown(
        "Norges Bank's open data API, data set **EXR** (series `B.EUR.NOK.SP` and `B.USD.NOK.SP`). "
        "One rate per business day, fixed around 14:15 Norwegian time; dates have no time zone and "
        "weekends/holidays are missing. For the weekly view the mean of each NVE week (ending Sunday) is used."
    )
