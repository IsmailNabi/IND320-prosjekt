"""Page: About - links, what the app shows and where the data come from.

The work log and AI usage are documented in the Jupyter Notebooks (one per
project part) on GitHub, not in the app (feedback from part 2).
"""
import streamlit as st

st.title("About")

st.markdown(
    """
### Links
* **GitHub:** [IND320-prosjekt](https://github.com/IsmailNabi/IND320-prosjekt)
  (code, notebooks with work log and AI usage)
* **App:** [ismail.streamlit.app](https://ismail.streamlit.app/)

### How to use the app
Choose an **area** in the sidebar. It is a global setting used by all pages:
the reservoir table and plots show all areas of the chosen type, while the
analysis and weather pages use the chosen area. Settings that only apply to one
page (month interval, smoother lengths, DCT cut-off, ...) are on that page.

### Pages
| Group | Page | Content |
|---|---|---|
| Reservoirs (NVE) | Reservoir table | One row per area with a trend sparkline |
| | Reservoir plots | Time series per area type, with dates |
| | STL & spectrogram | Seasonal-trend decomposition and spectrogram of the filling degree |
| Weather (open-meteo) | Outliers & anomalies | SPC outliers in precipitation, LOF anomalies in temperature |
| Power flows (ENTSO-E) | Cross-border flows | Power exchange with neighbouring countries |

### Data sources
* **NVE Magasinstatistikk API**: weekly reservoir filling since 1995, downloaded live.
* **open-meteo Historical Weather API (ERA5)**: hourly weather, downloaded live for the
  chosen area. The locations are 1000 random points per area, sampled from NVE shapefiles
  (atlas.nve.no) and stored in MongoDB.
* **ENTSO-E Transparency Platform**: cross-border physical flows, processed with
  Cassandra and Spark and stored in MongoDB.
"""
)
