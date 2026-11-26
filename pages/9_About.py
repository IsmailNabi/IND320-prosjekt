"""About: links, how the app is organised, and the data sources.

The work log and AI usage are documented in the Jupyter Notebooks (one per
project part) on GitHub, not in the app (feedback from part 2).
"""
import streamlit as st

from modules.theme import page_header

page_header("About", "About")
st.markdown(
    """
### Links
* **GitHub:** [IND320-prosjekt](https://github.com/IsmailNabi/IND320-prosjekt)
  (code, README and the notebooks with work log and AI usage)
* **App:** [ismail.streamlit.app](https://ismail.streamlit.app/)

### How the app is organised
The menu has four groups, each with its own colour (shown above every page title):

| Group | Pages | Question |
|---|---|---|
| Explore | Map & time frame, Reservoir overview | What do the data look like? |
| Anomalies | STL & spectrogram, Weather outliers | What is normal, and what is not? |
| Prediction | Weather vs reservoir, Forecast | What drives the filling, and what comes next? |
| Markets | Cross-border flows, Exchange rates | Power exchange and currency |

**Global selections** (sidebar, stored in the session): the *area* (also set by clicking the map)
and the *time frame* (set on the map page, used as the training period of the forecast).
Settings that only belong to one page stay on that page.

### Data sources
* **NVE Magasinstatistikk API**: weekly reservoir filling since 1995, downloaded live.
* **open-meteo (ERA5)**: hourly weather, mean of sampled points per area. Downloaded once per
  area and year, then stored in MongoDB.
* **Norges Bank API**: daily NOK exchange rates (EUR, USD), downloaded live.
* **ENTSO-E**: cross-border physical flows, processed with Cassandra and Spark and stored in MongoDB.
* **atlas.nve.no**: shapefiles of the areas, converted to GeoJSON for the map.
"""
)
