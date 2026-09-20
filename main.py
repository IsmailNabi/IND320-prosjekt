import streamlit as st

st.set_page_config(page_title="IND320 Reservoir App", layout="wide")

st.title("IND320 - Reservoir Data App")

st.sidebar.header("Navigation")
st.sidebar.info("Use the menu above to navigate between the pages.")

st.markdown("""
### Welcome to Project Part 2
This is a Streamlit application visualizing reservoir storage levels and TWh capacity for Norwegian water reservoirs.

* **Page 1 (Home):** Project Overview
* **Page 2 (Table View):** Data table with `LineChartColumn` for the first month
* **Page 3 (Plot View):** Interactive visualizations with filtering
* **Page 4 (Log/About):** Project log and AI declaration
""")