import streamlit as st
import pandas as pd

st.set_page_config(page_title="Table View", layout="wide")
st.title("Data Summary & Line Charts")

@st.cache_data
def load_data():
    df = pd.read_csv("data/reservoirs.csv")
    df['dato_Id'] = pd.to_datetime(df['dato_Id'])
    df = df.sort_values('dato_Id').reset_index(drop=True)
    return df

df = load_data()

# Extract the first month in the dataset
first_month = df['dato_Id'].dt.to_period('M').iloc[0]
df_first_month = df[df['dato_Id'].dt.to_period('M') == first_month]

# Build a summary where each column from the CSV becomes a row in the table
summary_rows = []
for col in df.columns:
    if pd.api.types.is_numeric_dtype(df[col]):
        summary_rows.append({
            "Column Name": col,
            "First Month Trend": df_first_month[col].tolist(),
            "Min Value": df[col].min(),
            "Max Value": df[col].max(),
            "Mean Value": df[col].mean()
        })

summary_df = pd.DataFrame(summary_rows)

# Display the table with LineChartColumn
st.dataframe(
    summary_df,
    column_config={
        "First Month Trend": st.column_config.LineChartColumn(
            "First Month Trend",
            width="medium"
        ),
    },
    hide_index=True,
    use_container_width=True
)