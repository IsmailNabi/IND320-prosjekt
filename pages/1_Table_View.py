import streamlit as st
import pandas as pd

# 1. Mappe tekniske kolonnenavn til forståelige, norske navn
COLUMN_NAME_MAP = {
    "fyllingsgrad": "Fyllingsgrad",
    "kapasitet_TWh": "Kapasitet (TWh)",
    "fylling_TWh": "Magasininnhold (TWh)",
    "fyllingsgrad_forrige_uke": "Fyllingsgrad (forrige uke)",
    "endring_fyllingsgrad": "Endring i fyllingsgrad"
}

# 2. Filtrer ut uinteressante/tekniske kolonner (omrnr, iso_aar, iso_uke)
data_columns = [col for col in df.columns if col in COLUMN_NAME_MAP]

# 3. Forbered data for tabellen (1 rad per variabel)
summary_data = []

# Finn første måned med data (f.eks. de første 4-5 ukene)
first_month_df = df.iloc[:5]  # eller filtrer på dato

for col in data_columns:
    summary_data.append({
        "Metric": COLUMN_NAME_MAP[col],
        "First Month Trend": first_month_df[col].tolist(),  # Liste med verdier for LineChart
        "Min Value": df[col].min(),
        "Max Value": df[col].max(),
        "Mean Value": df[col].mean()
    })

summary_df = pd.DataFrame(summary_data)

# 4. Vis tabellen i Streamlit med st.column_config
st.subheader("Vannkraft & Magasinindikatorer")

st.dataframe(
    summary_df,
    column_config={
        "Metric": st.column_config.TextColumn(
            "Indikator / Variabel",
            help="Navnet på vannkraftindikatoren",
            width="medium"
        ),
        "First Month Trend": st.column_config.LineChartColumn(
            "Trend (Første måned)",
            help="Utvikling gjennom den første måneden",
            width="medium"
        ),
        "Min Value": st.column_config.NumberColumn(
            "Minimumsverdi",
            format="%.4f"
        ),
        "Max Value": st.column_config.NumberColumn(
            "Maksimumsverdi",
            format="%.4f"
        ),
        "Mean Value": st.column_config.NumberColumn(
            "Gjennomsnitt",
            format="%.4f"
        ),
    },
    hide_index=True,
    use_container_width=True
)