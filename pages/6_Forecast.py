"""Prediction: forecast of reservoir filling with River (SNARIMAX or lag-based ML).

* Training data: the global time frame (set on the map page) ends the training
  period; the history length counts backwards from there. The horizon is the
  number of weeks forecast after it.
* Model, parameters and exogenous variables (weather properties, EUR/USD)
  are all selectable. The defaults are the best setting from the notebook's
  backtest (data/forecast_defaults.json).
* Dynamic forecasting: every forecast week is fed back as input to the next.
* Bonus: an 80 % prediction interval from quantile-loss models.
"""
from datetime import date

import pandas as pd
import streamlit as st

from modules.currency import to_weekly as currency_weekly
from modules.data_loader import load_exchange_rates, load_reservoirs, weather_weekly_with_progress
from modules.decomposition import filling_series
from modules.forecast import build_dataset, forecast_filling, load_defaults
from modules.plots import forecast_animation
from modules.selectors import get_period, selected_area, set_period
from modules.theme import page_header
from modules.weather import WEATHER_LABELS

page_header("Forecast of reservoir filling", "Prediction",
            "Online models from the River library, trained on weekly data. Press Run after changing settings.")
df = load_reservoirs()
area_type, area_number, region = selected_area()
area_name = df.loc[(df["area_type"] == area_type) & (df["area_number"] == area_number), "name"].iloc[0]
defaults = load_defaults()
start, end = get_period()

EXOG = {f"weather:{v}": WEATHER_LABELS[v] for v in ("precipitation", "temperature_2m", "snowfall", "rain")}
EXOG.update({"currency:EUR": "NOK per EUR", "currency:USD": "NOK per USD"})

with st.form("forecast_settings"):
    c1, c2, c3 = st.columns(3)
    model = c1.radio("Model", ["snarimax", "lag_ml"], index=["snarimax", "lag_ml"].index(defaults["model"]),
                     format_func={"snarimax": "SNARIMAX", "lag_ml": "Lag-based ML"}.get, horizontal=True)
    train_end = c2.date_input("Training ends (= end of the time frame)", value=end,
                              min_value=date(2000, 1, 1), max_value=date.today())
    history_years = c3.slider("History length (years)", 2, 15, int(defaults["history_years"]))
    c1, c2 = st.columns([1, 2])
    horizon = c1.slider("Horizon (weeks)", 4, 52, int(defaults["horizon"]))
    exog = c2.multiselect("Exogenous variables (data sources)", list(EXOG), default=[e for e in defaults["exog"] if e in EXOG],
                          format_func=EXOG.get)

    with st.expander("Model parameters", expanded=False):
        c1, c2, c3, c4 = st.columns(4)
        p = c1.number_input("p (AR order)", 0, 6, int(defaults["p"]))
        d = c2.number_input("d (differencing)", 0, 2, int(defaults["d"]))
        q = c3.number_input("q (MA order)", 0, 6, int(defaults["q"]))
        m = c4.number_input("m (season length, weeks)", 1, 104, int(defaults["m"]))
        c1, c2, c3, c4 = st.columns(4)
        sp = c1.number_input("sp (seasonal AR)", 0, 3, int(defaults["sp"]))
        sd = c2.number_input("sd (seasonal differencing)", 0, 1, int(defaults["sd"]))
        sq = c3.number_input("sq (seasonal MA)", 0, 3, int(defaults["sq"]))
        lr = c4.select_slider("Learning rate", [0.001, 0.003, 0.01, 0.03, 0.05, 0.1], value=min([0.001, 0.003, 0.01, 0.03, 0.05, 0.1], key=lambda v: abs(v - defaults["lr"])))
        c1, c2 = st.columns(2)
        n_lags = c1.number_input("Lags (lag-based ML)", 1, 12, int(defaults["n_lags"]))
        epochs = c2.number_input("Passes over the history (lag-based ML)", 1, 10, int(defaults["epochs"]))
        intervals = st.toggle("Show 80 % prediction interval (quantile loss)", value=True)
    run = st.form_submit_button("Run forecast", type="primary")

# The training end is the end of the global time frame (synced with the map page)
if train_end != end:
    set_period(start, train_end)
first_year = train_end.year - history_years

try:
    filling = filling_series(df, area_type, area_number)
    weather = None
    if any(e.startswith("weather:") for e in exog):
        last_year = min(train_end.year + 1, date.today().year)      # also the forecast weeks, if known
        weather = weather_weekly_with_progress(region, first_year, last_year)
    rates = currency_weekly(load_exchange_rates(f"{first_year}-01-01")) if any(
        e.startswith("currency:") for e in exog) else None
except Exception as exc:
    st.error(f"Input data could not be loaded: {exc}")
    st.stop()


@st.cache_data(show_spinner="Training the model...", max_entries=50)
def run_forecast(data: pd.DataFrame, **settings):
    """Cached: the same settings give the same forecast without training again."""
    return forecast_filling(data, **settings)


data = build_dataset(filling, weather, rates)
try:
    result = run_forecast(data, model=model, exog=exog, history_years=history_years, horizon=horizon,
                          train_end=pd.Timestamp(train_end), p=p, d=d, q=q, sp=sp, sd=sd, sq=sq, m=m,
                          n_lags=n_lags, lr=lr, epochs=epochs, quantiles=(0.1, 0.9) if intervals else None)
except ValueError as exc:
    st.warning(str(exc))
    st.stop()

title = f"{area_name}: {horizon}-week forecast from {train_end:%d.%m.%Y} ({'SNARIMAX' if model == 'snarimax' else 'lag-based ML'})"
st.plotly_chart(forecast_animation(result.table, title), width="stretch")

if result.metrics:
    cols = st.columns(len(result.metrics))
    for col, (name, value) in zip(cols, result.metrics.items()):
        col.metric(name, f"{value:.3f}" if isinstance(value, float) else value)
    st.caption("Errors are computed for forecast weeks where the real filling degree is already known.")
else:
    st.caption("The forecast lies in the future, so it cannot be scored yet. Move the training end back to test it.")

with st.expander("Forecast table"):
    st.dataframe(result.table[result.table["part"] == "forecast"].drop(columns="part"), hide_index=True,
                 width="stretch")
with st.expander("How the forecast works"):
    st.markdown(
        "The model learns one week at a time from the history (River is an online-learning library). "
        "The forecast is **dynamic**: each predicted week is used as input for the next one. "
        "Future weather is unknown, so the average of the same calendar week in the training years is used; "
        "exchange rates are kept at their last value. The interval comes from two extra models trained with "
        "the quantile loss (10 % and 90 %)."
    )
