import pandas as pd
import streamlit as st
from modules.data_loader import get_data

# Retrieve dataset from shared module
df = get_data()

st.title("Table View - Reservoir Summary")

if df.empty:
    st.warning(
        "No data available. Please verify that 'data/reservoirs.csv' exists."
    )
else:
    # Map technical column names to user-friendly labels
    COLUMN_NAME_MAP = {
        "fyllingsgrad": "Fyllingsgrad",
        "kapasitet_TWh": "Kapasitet (TWh)",
        "fylling_TWh": "Magasininnhold (TWh)",
        "fyllingsgrad_forrige_uke": "Fyllingsgrad (forrige uke)",
        "endring_fyllingsgrad": "Endring i fyllingsgrad",
    }

    # Filter columns actually present in the dataset
    data_columns = [col for col in df.columns if col in COLUMN_NAME_MAP]

    if not data_columns:
        st.error("No matching indicator columns found in the loaded dataset.")
    else:
        # Helper function to sanitize string or float columns into pure numeric values
        def clean_numeric_series(series):
            s = series.astype(str).str.replace(",", ".")
            return pd.to_numeric(s, errors="coerce")

        # Build summary table data structure
        summary_data = []
        first_month_df = df.iloc[:5]

        for col in data_columns:
            numeric_series = clean_numeric_series(df[col]).dropna()
            first_month_series = clean_numeric_series(
                first_month_df[col]
            ).dropna()

            summary_data.append({
                "Metric": COLUMN_NAME_MAP[col],
                "First Month Trend": first_month_series.tolist(),
                "Min Value": numeric_series.min(),
                "Max Value": numeric_series.max(),
                "Mean Value": numeric_series.mean(),
            })

        summary_df = pd.DataFrame(summary_data)

        # Display summary dataframe using Streamlit column configurations
        st.subheader("📊 Key Indicators Summary")

        st.dataframe(
            summary_df,
            column_config={
                "Metric": st.column_config.TextColumn(
                    "Indikator / Variabel",
                    help="Name of the reservoir metric",
                    width="medium",
                ),
                "First Month Trend": st.column_config.LineChartColumn(
                    "Trend (Første måned)",
                    help="Micro-trend over the first month",
                    width="large",
                ),
                "Min Value": st.column_config.NumberColumn(
                    "Minimumsverdi", format="%.4f"
                ),
                "Max Value": st.column_config.NumberColumn(
                    "Maksimumsverdi", format="%.4f"
                ),
                "Mean Value": st.column_config.NumberColumn(
                    "Gjennomsnitt", format="%.4f"
                ),
            },
            hide_index=True,
            use_container_width=True,
        )

        st.divider()

        # Detailed trend inspection section
        st.subheader("📈 Detailed Trend Inspection")
        st.write(
            "Select an indicator below to inspect its detailed development"
            " over time with exact axes."
        )

        available_options = {COLUMN_NAME_MAP[col]: col for col in data_columns}

        selected_label = st.selectbox(
            "Choose Metric to Display:", options=list(available_options.keys())
        )

        selected_col = available_options[selected_label]

        # Prepare explicit dataframe for dedicated chart rendering
        clean_series = (
            clean_numeric_series(df[selected_col])
            .dropna()
            .reset_index(drop=True)
        )

        chart_df = pd.DataFrame({
            "Måling / Uke": range(1, len(clean_series) + 1),
            selected_label: clean_series,
        })

        # Render line chart with explicit X and Y axes
        st.line_chart(
            chart_df,
            x="Måling / Uke",
            y=selected_label,
            height=350,
        )