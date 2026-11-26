"""Forecasting reservoir filling with River (no Streamlit imports).

Two model families, both learned online (one observation at a time) with River:

* "snarimax": time_series.SNARIMAX, River's (S)easonal (N)on-linear ARIMA with
  e(X)ogenous inputs. Parameters p/d/q and seasonal sp/sd/sq with period m.
* "lag_ml":   a linear regression on lagged values of the filling degree (last
  weeks and the same week last year), the week of the year and exogenous inputs.

Time resolution: WEEKLY. Magasinstatistikk is weekly, so a finer resolution adds
no information about the target, while hourly weather would make learning ~170x
slower. Weather and exchange rates are therefore aggregated to the same weeks.

Forecasts are DYNAMIC: each forecast week is fed back as input for the next.
Exogenous values for future weeks are unknown, so they are replaced by the
average of the same calendar week in the training years (weather), or by the
last known value (exchange rates).

Bonus: prediction intervals come from extra models trained with the quantile
(pinball) loss, optim.losses.Quantile(alpha), e.g. alpha = 0.1 and 0.9.
"""
import json
import math
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd
from river import linear_model, optim, preprocessing, time_series

DEFAULTS_FILE = Path(__file__).resolve().parents[1] / "data" / "forecast_defaults.json"
TARGET = "filling_degree"
WEEKS_PER_YEAR = 52

# Settings used when the notebook has not written data/forecast_defaults.json yet
BUILTIN_DEFAULTS = {
    "model": "snarimax", "history_years": 8, "horizon": 26, "exog": [],
    "p": 2, "d": 0, "q": 0, "sp": 1, "sd": 1, "sq": 0, "m": WEEKS_PER_YEAR,
    "n_lags": 4, "lr": 0.01, "epochs": 3,
}
PARAM_KEYS = list(BUILTIN_DEFAULTS)


def load_defaults() -> dict:
    """Best settings found in the notebook's backtest (falls back to built-in values)."""
    if DEFAULTS_FILE.exists():
        stored = json.loads(DEFAULTS_FILE.read_text())
        return {**BUILTIN_DEFAULTS, **{k: v for k, v in stored.items() if k in PARAM_KEYS}}
    return dict(BUILTIN_DEFAULTS)


def save_defaults(settings: dict) -> Path:
    """Store the best settings so the Streamlit app uses them as its defaults."""
    DEFAULTS_FILE.parent.mkdir(parents=True, exist_ok=True)
    DEFAULTS_FILE.write_text(json.dumps({k: settings[k] for k in PARAM_KEYS if k in settings}, indent=2))
    return DEFAULTS_FILE


# ------------------------------------------------------------------ data
def build_dataset(filling: pd.Series, weather_weekly: pd.DataFrame | None = None,
                  currency_weekly: pd.DataFrame | None = None) -> pd.DataFrame:
    """One row per NVE week: the target plus the selectable exogenous columns.

    filling: weekly filling degree indexed by NVE's week dates (Sundays).
    weather_weekly / currency_weekly: weekly tables on the same Sunday dates.
    Weather columns are prefixed "weather:", currencies "currency:".
    """
    data = filling.rename(TARGET).to_frame()
    if weather_weekly is not None:
        data = data.join(weather_weekly.add_prefix("weather:"), how="left")
    if currency_weekly is not None:
        data = data.join(currency_weekly.add_prefix("currency:"), how="left")
    return data.sort_index()


def _future_exog(train: pd.DataFrame, future_index: pd.DatetimeIndex, exog: list[str]) -> list[dict]:
    """Exogenous values for weeks we have not seen: weekly climatology / last value."""
    if not exog:
        return [{} for _ in future_index]
    week = train.index.isocalendar().week.astype(int)
    climatology = train[exog].groupby(week.values).mean()
    last = train[exog].ffill().iloc[-1]
    rows = []
    for ts in future_index:
        w = min(int(ts.isocalendar().week), climatology.index.max())
        row = {}
        for col in exog:
            if col.startswith("currency:"):
                row[col] = float(last[col])
            else:
                row[col] = float(climatology.loc[w, col]) if w in climatology.index else float(last[col])
        rows.append(row)
    return rows


def _week_features(ts: pd.Timestamp) -> dict:
    """Week of year as a point on a circle, so week 52 and week 1 are neighbours."""
    angle = 2 * math.pi * ts.isocalendar().week / 52.18
    return {"week_sin": math.sin(angle), "week_cos": math.cos(angle)}


# ------------------------------------------------------------------ models
def _regressor(lr: float, loss=None):
    """Standardised inputs + linear regression trained with SGD (River's usual set-up)."""
    return preprocessing.StandardScaler() | linear_model.LinearRegression(
        optimizer=optim.SGD(lr), loss=loss or optim.losses.Squared(), intercept_lr=lr)


def _fit_snarimax(y: pd.Series, X: pd.DataFrame, s: dict, loss=None) -> time_series.SNARIMAX:
    model = time_series.SNARIMAX(p=s["p"], d=s["d"], q=s["q"], m=s["m"], sp=s["sp"], sd=s["sd"],
                                 sq=s["sq"], regressor=_regressor(s["lr"], loss))
    for ts, value in y.items():
        model.learn_one(float(value), X.loc[ts].to_dict() if len(X.columns) else None)
    return model


def _lag_row(history: list[float], ts: pd.Timestamp, exog_row: dict, n_lags: int) -> dict:
    """Features for one week: last n_lags values, same week last year, season, exogenous."""
    row = {f"lag_{k}": history[-k] for k in range(1, n_lags + 1)}
    row["lag_52"] = history[-WEEKS_PER_YEAR]
    row.update(_week_features(ts))
    row.update(exog_row)
    return row


def _fit_lag_ml(y: pd.Series, X: pd.DataFrame, s: dict, loss=None):
    model = _regressor(s["lr"], loss)
    values = y.tolist()
    start = max(s["n_lags"], WEEKS_PER_YEAR)
    for _ in range(int(s["epochs"])):                     # a few passes over the history
        for t in range(start, len(values)):
            x = _lag_row(values[:t], y.index[t], X.iloc[t].to_dict() if len(X.columns) else {}, s["n_lags"])
            model.learn_one(x, values[t])
    return model


def _predict(model, kind: str, y: pd.Series, future: pd.DatetimeIndex, xs: list[dict], s: dict) -> np.ndarray:
    """Dynamic multi-step forecast: predictions are fed back as inputs."""
    if kind == "snarimax":
        return np.array(model.forecast(horizon=len(future), xs=xs if xs and xs[0] else None))
    history = y.tolist()
    out = []
    for ts, x_exog in zip(future, xs):
        pred = model.predict_one(_lag_row(history, ts, x_exog, s["n_lags"]))
        out.append(pred)
        history.append(pred)                               # dynamic: feed the forecast back
    return np.array(out)


@dataclass
class ForecastResult:
    """Forecast table plus the settings and (if the truth is known) its errors."""
    table: pd.DataFrame                 # date, observed, forecast, lower, upper, part
    settings: dict
    metrics: dict = field(default_factory=dict)


def forecast_filling(data: pd.DataFrame, model: str = "snarimax", exog: list[str] | None = None,
                     history_years: int = 8, horizon: int = 26, train_end=None,
                     p: int = 2, d: int = 0, q: int = 0, sp: int = 1, sd: int = 1, sq: int = 0,
                     m: int = WEEKS_PER_YEAR, n_lags: int = 4, lr: float = 0.01, epochs: int = 3,
                     quantiles: tuple | None = (0.1, 0.9)) -> ForecastResult:
    """Forecast the coming weeks' filling degree for ONE Magasinstatistikk area.

    Parameters
    ----------
    data : output of build_dataset() for one area (weekly rows)
    model : "snarimax" or "lag_ml"
    exog : selected data sources, e.g. ["weather:precipitation", "currency:EUR"]
    history_years : length of the training history before train_end
    horizon : number of weeks to forecast
    train_end : last training week (default: last week with data). If later weeks
                exist in `data`, they are used to score the forecast (backtest).
    p, d, q, sp, sd, sq, m : SNARIMAX orders (m = season length in weeks)
    n_lags, epochs : lag model settings; lr = SGD learning rate (both models)
    quantiles : (low, high) for the prediction interval, None to skip it

    Returns a ForecastResult with history, forecast and interval in one table.
    """
    exog = list(exog or [])
    s = dict(model=model, exog=exog, history_years=history_years, horizon=horizon, p=p, d=d, q=q,
             sp=sp, sd=sd, sq=sq, m=m, n_lags=n_lags, lr=lr, epochs=epochs)
    data = data.dropna(subset=[TARGET])
    train_end = pd.Timestamp(train_end) if train_end is not None else data.index[-1]
    train = data.loc[(data.index > train_end - pd.DateOffset(years=history_years)) & (data.index <= train_end)]
    if len(train) < WEEKS_PER_YEAR + 10:
        raise ValueError("Too little history: choose at least about 1.5 years.")
    if exog:
        train = train.assign(**{c: train[c].interpolate().bfill().ffill() for c in exog})
        if train[exog].isna().any().any():
            raise ValueError("Selected data sources have no values in the training period.")

    y, X = train[TARGET], train[exog]
    step = pd.Timedelta(weeks=1)
    future = pd.date_range(train_end + step, periods=horizon, freq=step)
    xs = _future_exog(train, future, exog)

    fit = _fit_snarimax if model == "snarimax" else _fit_lag_ml
    centre = _predict(fit(y, X, s), model, y, future, xs, s)
    table = pd.DataFrame({"date": future, "forecast": np.clip(centre, 0, 1)})
    if quantiles:
        for name, alpha in zip(("lower", "upper"), quantiles):
            q_model = fit(y, X, s, loss=optim.losses.Quantile(alpha))
            table[name] = np.clip(_predict(q_model, model, y, future, xs, s), 0, 1)
        # the two quantile models are trained separately and can cross: sort them
        table[["lower", "upper"]] = np.sort(table[["lower", "upper"]].to_numpy(), axis=1)

    truth = data[TARGET].reindex(future)
    table["observed"] = truth.to_numpy()
    table["part"] = "forecast"
    hist = pd.DataFrame({"date": train.index, "observed": train[TARGET].to_numpy(), "part": "history"})
    table = pd.concat([hist, table], ignore_index=True)

    metrics = {}
    scored = table.dropna(subset=["observed", "forecast"])
    if len(scored):
        err = scored["forecast"] - scored["observed"]
        metrics = {"MAE": float(err.abs().mean()), "RMSE": float(np.sqrt((err ** 2).mean())),
                   "weeks scored": int(len(scored))}
        if quantiles:
            inside = (scored["observed"] >= scored["lower"]) & (scored["observed"] <= scored["upper"])
            metrics["interval coverage"] = float(inside.mean())
    return ForecastResult(table, s, metrics)


# ------------------------------------------------------------------ backtest
def backtest(data: pd.DataFrame, settings: list[dict], origins: list, horizon: int = 26) -> pd.DataFrame:
    """Score each setting by forecasting from several past origins (rolling-origin test).

    For every origin the model is trained on the history before it and asked for
    `horizon` weeks, which are compared with what really happened.
    Returns one row per setting with the mean MAE/RMSE over the origins.
    """
    rows = []
    for k, s in enumerate(settings):
        scores = []
        for origin in origins:
            res = forecast_filling(data, **{**s, "horizon": horizon, "train_end": origin, "quantiles": None})
            scores.append(res.metrics)
        frame = pd.DataFrame(scores)
        used = {key: value for key, value in res.settings.items() if key != "horizon"}  # incl. defaults
        rows.append({"setting": k, **used, "MAE": frame["MAE"].mean(), "RMSE": frame["RMSE"].mean()})
    return pd.DataFrame(rows).sort_values("MAE").reset_index(drop=True)
