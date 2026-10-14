"""Page 2: time series plots with real dates on the x-axis."""
import matplotlib.pyplot as plt
import streamlit as st

from modules.analysis import filter_interval, minmax_normalize, month_options
from modules.data_loader import load_reservoirs
from modules.helpers import AREA_TYPES, METRIC_LABELS

st.title("Reservoir plots")
df = load_reservoirs()

area_type = st.radio("Area type", list(AREA_TYPES), format_func=AREA_TYPES.get, horizontal=True)
type_df = df[df["area_type"] == area_type]

months = month_options(type_df)
first, last = st.select_slider("Month interval", options=months, value=(months[0], months[0]))
type_df = filter_interval(type_df, first, last)

ALL = "All columns together (one area, normalized)"
choice = st.selectbox("Column", [ALL] + list(METRIC_LABELS), format_func=lambda c: METRIC_LABELS.get(c, c))

fig, ax = plt.subplots(figsize=(10, 5))
if choice == ALL:
    # Different units and scales -> pick ONE area and scale each column to 0-1
    names = sorted(type_df["name"].unique())
    area = st.selectbox("Area", names)
    area_df = type_df[type_df["name"] == area].sort_values("date")
    for col, label in METRIC_LABELS.items():
        ax.plot(area_df["date"], minmax_normalize(area_df[col]), marker="o", label=label)
    ax.set_ylabel("Normalized value (0 = min, 1 = max in period)")
    ax.set_title(f"{area}: all columns, min-max normalized")
else:
    # Same unit across areas of the same type -> one line per area
    for name, grp in type_df.sort_values("date").groupby("name"):
        ax.plot(grp["date"], grp[choice], marker="o", label=name)
    ax.set_ylabel(METRIC_LABELS[choice])
    ax.set_title(f"{METRIC_LABELS[choice]} per area ({first} to {last})")

ax.set_xlabel("Date")
ax.grid(True, linestyle="--", alpha=0.5)
ax.legend(fontsize=8)
fig.autofmt_xdate()
st.pyplot(fig)
st.caption("Source: NVE Magasinstatistikk API. Normalization removes units, so compare shapes, not levels.")
