import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st
from modules.data_loader import get_data

# 1. Retrieve dataset from shared data loader module
df = get_data()

st.title("Plot View - Interactive Reservoir Data")

if df.empty:
    st.warning(
        "No data available. Please check that 'data/reservoirs.csv' exists."
    )
else:
    # 2. Map technical column names to user-friendly labels
    COLUMN_NAME_MAP = {
        "fyllingsgrad": "Fyllingsgrad",
        "kapasitet_TWh": "Kapasitet (TWh)",
        "fylling_TWh": "Magasininnhold (TWh)",
        "fyllingsgrad_forrige_uke": "Fyllingsgrad (forrige uke)",
        "endring_fyllingsgrad": "Endring i fyllingsgrad",
    }

    # Filter columns that actually exist in the CSV file
    available_cols = [col for col in df.columns if col in COLUMN_NAME_MAP]

    if not available_cols:
        st.error("No valid metric columns found in the dataset.")
    else:

        # Helper function to clean string/float values (handling comma decimals)
        def clean_numeric_series(series):
            s = series.astype(str).str.replace(",", ".")
            return pd.to_numeric(s, errors="coerce")

        # Copy dataframe and sanitize numeric columns
        df_clean = df.copy()
        for col in available_cols:
            df_clean[col] = clean_numeric_series(df_clean[col])

        # 3. Extract or generate Month labels for the selection slider
        if "dato" in df_clean.columns:
            df_clean["Date"] = pd.to_datetime(
                df_clean["dato"], errors="coerce"
            )
            df_clean["Month"] = df_clean["Date"].dt.strftime("%Y-%m")
        elif "iso_aar" in df_clean.columns and "iso_uke" in df_clean.columns:
            # Build month grouping from ISO year and week number
            df_clean["Month"] = (
                df_clean["iso_aar"].astype(str)
                + " - Month "
                + ((df_clean["iso_uke"].astype(int) - 1) // 4 + 1).astype(str)
            )
        else:
            # Fallback: Group every 4 weekly entries as one month
            df_clean["Month"] = [
                f"Month {(i // 4) + 1}" for i in range(len(df_clean))
            ]

        # Get ordered unique list of months
        unique_months = df_clean["Month"].dropna().unique().tolist()
        if not unique_months:
            unique_months = ["Month 1"]
            df_clean["Month"] = "Month 1"

        st.subheader("📊 Plot Controls & Selection")

        col1, col2 = st.columns([1, 1])

        with col1:
            # Drop-down menu allowing selection of a single column or all columns together
            dropdown_options = ["All Columns Together"] + [
                COLUMN_NAME_MAP[c] for c in available_cols
            ]
            selected_option = st.selectbox(
                "Choose Column to Display:",
                options=dropdown_options,
                help=(
                    "Select an individual metric column or plot all metrics"
                    " together."
                ),
            )

        with col2:
            # Selection slider to pick a subset of months (default is the first month)
            if len(unique_months) == 1:
                selected_month_range = (unique_months[0], unique_months[0])
                st.info(f"Active Month: {unique_months[0]}")
            else:
                selected_month_range = st.select_slider(
                    "Select Subset of Months:",
                    options=unique_months,
                    value=(
                        unique_months[0],
                        unique_months[0],
                    ),  # Default: first month only
                    help=(
                        "Drag the slider handles to filter by a specific month"
                        " or range of months."
                    ),
                )

        # Filter dataset based on selected month range
        if isinstance(selected_month_range, tuple):
            start_m, end_m = selected_month_range
            start_idx = unique_months.index(start_m)
            end_idx = unique_months.index(end_m)

            if start_idx > end_idx:
                start_idx, end_idx = end_idx, start_idx

            allowed_months = unique_months[start_idx : end_idx + 1]
            filtered_df = df_clean[
                df_clean["Month"].isin(allowed_months)
            ].copy()
        else:
            filtered_df = df_clean[
                df_clean["Month"] == selected_month_range
            ].copy()

        # Reset index for sequential plotting along the X-axis
        filtered_df = filtered_df.reset_index(drop=True)

        st.divider()

        # 4. Render customized plot using Matplotlib
        st.subheader("📈 Time Series Visualization")

        fig, ax = plt.subplots(figsize=(10, 5))

        if selected_option == "All Columns Together":
            # Plot all numeric indicator columns on the same chart
            for col in available_cols:
                ax.plot(
                    filtered_df.index + 1,
                    filtered_df[col],
                    marker="o",
                    linewidth=2,
                    label=COLUMN_NAME_MAP[col],
                )

            chart_title = (
                "All Indicators - Overview ("
                f"{selected_month_range[0]} to {selected_month_range[1]})"
            )
            y_axis_label = "Values / Levels"
        else:
            # Find technical column corresponding to selected user label
            target_col = [
                k for k, v in COLUMN_NAME_MAP.items() if v == selected_option
            ][0]
            ax.plot(
                filtered_df.index + 1,
                filtered_df[target_col],
                marker="o",
                color="#1f77b4",
                linewidth=2.5,
                label=selected_option,
            )

            chart_title = (
                f"{selected_option} Development ({selected_month_range[0]} to"
                f" {selected_month_range[1]})"
            )
            y_axis_label = selected_option

        # Apply header title, axis labels, grid and legend formatting
        ax.set_title(chart_title, fontsize=14, fontweight="bold", pad=15)
        ax.set_xlabel(
            "Measurement / Week Index", fontsize=11, labelpad=10
        )
        ax.set_ylabel(y_axis_label, fontsize=11, labelpad=10)
        ax.grid(True, linestyle="--", alpha=0.6)
        ax.legend(loc="best", frameon=True)

        plt.tight_layout()

        # Render the Matplotlib plot in Streamlit
        st.pyplot(fig)