import streamlit as st
from modules.data_loader import get_data


class ReservoirApp:
    """Main application class for the IND320 Reservoir project."""

    def __init__(self):
        self._configure_page()

        # Define application page structure (Page 3 removed)
        self._pages_structure = {
            "📊 Data & Summaries": [
                ("Table View", "pages/1_Table_View.py"),
            ],
            "📈 Visualizations": [
                ("Plot View", "pages/2_Plot_View.py"),
            ],
        }

        self._pages = self._create_pages()
        self._home_page = st.Page(self._home, title="Home", icon="🏠")

    def _configure_page(self):
        """Configure initial page parameters and layout."""
        st.set_page_config(
            page_title="IND320 - Reservoir App",
            layout="wide",
            initial_sidebar_state="expanded",
        )

    def _create_pages(self):
        """Convert page structure dictionary into st.Page objects."""
        pages = {}
        for group, items in self._pages_structure.items():
            pages[group] = [st.Page(path, title=title) for title, path in items]
        return pages

    def _home(self):
        """Render Home page landing layout."""
        st.title("IND320 - Norwegian Reservoir Storage App")
        st.markdown(
            """
            ### Welcome to Project Part 2
            This application visualizes reservoir storage levels and energy capacity (TWh) for Norwegian water reservoirs.
            
            Use the sidebar navigation menu on the left to access:
            * **Table View:** Key summary metrics with micro-trend line charts and detailed inspection.
            * **Plot View:** Interactive visualizations and filtering options.
            
            ---
            **Course:** IND320 - Data Science & Visualization  
            **Tech Stack:** Streamlit, Pandas, Python
            """
        )

    def _hide_default_nav(self):
        """Hide standard Streamlit page listing from the sidebar."""
        st.markdown(
            """
            <style>
                [data-testid="stSidebarNav"] { display: none; }
            </style>
            """,
            unsafe_allow_html=True,
        )

    def _render_sidebar(self):
        """Render custom categorized sidebar navigation."""
        with st.sidebar:
            st.markdown("### 🧭 Navigation")

            if st.button("🏠 Home", use_container_width=True):
                st.switch_page(self._home_page)

            st.divider()

            for group_name, items in self._pages_structure.items():
                with st.expander(group_name, expanded=True):
                    for (title, path), page in zip(
                        items, self._pages[group_name]
                    ):
                        if st.button(
                            title, use_container_width=True, key=f"nav_{path}"
                        ):
                            st.switch_page(page)

    def run(self):
        """Execute application logic, initialize dataset, and start navigation engine."""
        # Initialize session state dataset
        get_data()

        # Render custom sidebar structure
        self._hide_default_nav()
        self._render_sidebar()

        # Build full pages list for Streamlit navigation engine
        all_pages = [page for group in self._pages.values() for page in group]
        nav = st.navigation([self._home_page] + all_pages)
        nav.run()


if __name__ == "__main__":
    app = ReservoirApp()
    app.run()