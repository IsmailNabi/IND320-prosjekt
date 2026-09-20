import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="Plot View", layout="wide")
st.title("Interactive Reservoir Plots")

@st.cache_data
def load_data():
    df = pd.read_csv("data/reservoirs.csv")
    df['dato_Id'] = pd.to_datetime(df['dato_Id'])
    df['month_year'] = df['dato_Id'].dt.strftime('%Y-%m')
    df = df.sort_values('dato_Id').reset_index(drop=True)
    return df

df = load_data()

# Unique months for the slider selection
unique_months = sorted(df['month_year'].unique())

selected_months = st.select_slider(
    "Select Month Range:",
    options=unique_months,
    value=(unique_months[0], unique_months[min(5, len(unique_months)-1)])
)

# Filter dataset based on selected month range
filtered_df = df[(df['month_year'] >= selected_months[0]) & (df['month_year'] <= selected_months[1])]

# Dropdown menu to choose a specific column or all
numeric_cols = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]
col_options = ["All Columns"] + numeric_cols
selected_col = st.selectbox("Select Column to Plot:", options=col_options)

# Plotting logic
if selected_col == "All Columns":
    fig = px.line(
        filtered_df, 
        x='dato_Id', 
        y=numeric_cols,
        title=f"Reservoir Data from {selected_months[0]} to {selected_months[1]}",
        labels={"dato_Id": "Date", "value": "Value", "variable": "Metric"}
    )
else:
    fig = px.line(
        filtered_df, 
        x='dato_Id', 
        y=selected_col,
        title=f"{selected_col} from {selected_months[0]} to {selected_months[1]}",
        labels={"dato_Id": "Date", selected_col: selected_col}
    )

st.plotly_chart(fig, use_container_width=True)