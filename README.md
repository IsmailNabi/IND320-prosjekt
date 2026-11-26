# IND320 – Norwegian reservoirs, weather and markets

Project work in IND320 (Data to Decision) at NMBU, autumn 2026, by Ismail Nabi.
A Streamlit app and four Jupyter notebooks that combine Norwegian reservoir statistics with
weather, power exchange and exchange-rate data.

**App:** https://ismail.streamlit.app

## What the app does
| Group | Pages |
|---|---|
| Explore | Map of price/water areas (click to select, time frame slider), reservoir overview |
| Anomalies | STL decomposition and spectrogram of the filling degree; weather outliers (SATV/SPC) and anomalies (LOF) |
| Prediction | Sliding window correlation weather vs reservoir; forecast of the filling degree (River SNARIMAX / lag-based ML) |
| Markets | Cross-border power flows (ENTSO-E); NOK exchange rates (Norges Bank) |

## Data sources
- **NVE Magasinstatistikk API** – weekly reservoir filling since 1995 (live)
- **open-meteo Historical Weather API (ERA5)** – hourly weather, averaged over random points per area; stored once per area and year in MongoDB
- **Norges Bank API** – daily EUR/USD exchange rates (live)
- **ENTSO-E Transparency Platform** – cross-border flows, processed with Cassandra + Spark (part 2) and stored in MongoDB
- **atlas.nve.no** – area shapefiles, converted to GeoJSON for the map

## Repository structure
```
main.py                 Streamlit entry point (menu, global area selector)
pages/                  one file per app page
modules/                shared code used by the app and the notebooks
  api.py, weather.py, currency.py   data download (NVE/ENTSO-E, open-meteo, Norges Bank)
  regions.py            areas, sampled points, GeoJSON
  outliers.py, decomposition.py, correlation.py, forecast.py   analyses
  plots.py, theme.py    Plotly figures and the app theme
  data_loader.py, selectors.py      Streamlit caching and shared selections
notebooks/              project_work_part1-4.ipynb (development, log and AI usage)
data/                   shapefiles, GeoJSON, sampled points, forecast defaults, app sketch
.streamlit/config.toml  app theme
```

## Run locally
```bash
uv sync                          # install the exact versions from uv.lock
uv run streamlit run main.py     # start the app
```
Credentials (MongoDB, ENTSO-E token) are read from `No_sync/secrets.toml` locally and from
Streamlit's secrets online. They are never committed.
