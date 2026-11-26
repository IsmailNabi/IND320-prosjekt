"""Shared look of the app: colours, Plotly template and page headers.

The same colours are set for Streamlit in .streamlit/config.toml, so the
interactive Plotly charts match the rest of the app. Each menu group has its
own accent colour, shown as a coloured band above the page title, so the user
can see which part of the app is active.
"""
import plotly.graph_objects as go
import plotly.io as pio

PRIMARY = "#0072B2"      # blue (buttons, sliders, main lines)
ACCENT = "#D55E00"       # vermillion (outliers, selected area): strong contrast to blue
TEXT = "#1B2A34"
GRID = "#D9E3EA"
BACKGROUND = "#FFFFFF"

# Line colours used in this order by every chart: the Okabe-Ito palette, which stays
# distinguishable for people with colour vision deficiency (lecture "Colours and symbols")
COLORWAY = ["#0072B2", "#E69F00", "#009E73", "#CC79A7", "#56B4E9", "#D55E00", "#F0E442", "#000000"]
SEQUENTIAL = "Viridis"   # perceptually uniform scale for maps and heatmaps

# One accent colour per menu group
GROUP_COLORS = {
    "Start": "#0072B2",
    "Explore": "#0072B2",
    "Anomalies": "#E69F00",
    "Prediction": "#CC79A7",
    "Markets": "#009E73",
    "About": "#6B7B86",
}

# Plotly template: font, colours and light grid as in the Streamlit theme
pio.templates["ind320"] = go.layout.Template(
    layout=dict(
        font=dict(family="Source Sans Pro, sans-serif", color=TEXT, size=13),
        colorway=COLORWAY,
        paper_bgcolor=BACKGROUND,
        plot_bgcolor=BACKGROUND,
        xaxis=dict(gridcolor=GRID, zerolinecolor=GRID, linecolor=GRID),
        yaxis=dict(gridcolor=GRID, zerolinecolor=GRID, linecolor=GRID),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0),
        margin=dict(l=60, r=20, t=70, b=50),
        hovermode="x unified",
        colorscale=dict(sequential=SEQUENTIAL, diverging="RdBu"),
    )
)
pio.templates.default = "plotly_white+ind320"


def page_header(title: str, group: str, intro: str | None = None) -> None:
    """Coloured group label + title, so the active menu group is easy to see."""
    import streamlit as st

    color = GROUP_COLORS.get(group, PRIMARY)
    st.markdown(
        f"<div style='border-left:6px solid {color};padding:2px 0 2px 12px;margin-bottom:4px;"
        f"color:{color};font-weight:600;letter-spacing:.05em;text-transform:uppercase;"
        f"font-size:.8rem'>{group}</div>",
        unsafe_allow_html=True,
    )
    st.title(title)
    if intro:
        st.caption(intro)
