import streamlit as st

st.set_page_config(page_title="Log & AI Usage", layout="wide")
st.title("Log & AI Usage Declaration")

st.markdown("""
### Project Links
* **GitHub Repository:** [IND320-prosjekt](https://github.com/IsmailNabi/IND320-prosjekt)
* **Live App:** [https://ismail.streamlit.app/](https://ismail.streamlit.app/)

---

### Compulsory Work Log (300 - 500 words)
In this project, I set up a modern development pipeline utilizing VS Code, `uv` for dependency management, Git/GitHub for version control, and Streamlit Community Cloud for automated deployments. Working with Jupyter Notebook provided an interactive environment to inspect and clean the dataset (`reservoirs.csv`). The original column names were reviewed, and data formatting was applied to handle date parsing seamlessly. Visualizations in matplotlib demonstrated how dual Y-axes are necessary when comparing metrics with different scales, such as percentage filling degree versus total capacity in TWh. 

Transitioning from Jupyter Notebook to Streamlit allowed me to turn static data explorations into an interactive web application. By structuring the app with a modular page layout inside the `pages/` directory, the code remains clean and maintainable. Streamlit's caching mechanism (`@st.cache_data`) was introduced to ensure fast load times during page switches. Building interactive widgets like `st.select_slider` and `st.selectbox` provided a user-friendly interface to filter temporal ranges and explore specific metrics dynamically.

---

### AI Usage Declaration
AI tools (specifically Google Gemini and GitHub Copilot) were used throughout this project to assist with:
1. Environment setup and resolving Python dependency issues (`uv`).
2. Debugging import errors and circular reference bugs.
3. Structuring Pandas transformation scripts and Plotly multi-column visualizations.
""")