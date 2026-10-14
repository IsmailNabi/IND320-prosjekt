"""Page 4: links, work log and AI usage."""
import streamlit as st

st.title("About, log and AI usage")
st.markdown(
    """
### Project links
* **GitHub:** [IND320-prosjekt](https://github.com/IsmailNabi/IND320-prosjekt)
* **App:** [ismail.streamlit.app](https://ismail.streamlit.app/)

### Log
Part 2 replaced the CSV file with live data and added two databases. I reused the repository and Streamlit app from part 1 and work on a separate branch until peer review is finished.

I started with the NVE Magasinstatistikk API, which needs no key. It has four endpoints; I use HentOffentligData for weekly values since 1995 and HentOmråder for area names. The areas are NO (the whole country), EL (five price areas) and VASS (four watercourse areas). My part 1 experience with the time columns helped: the data has one row per week and area, so my earlier plots mixed several areas in one line, and the app looked for a date column that is actually called dato_Id. Dates are now parsed properly and every plot shows one area, or one line per area. My first area-name function failed because the API returned a list instead of the nested structure in the documentation, so it now handles both shapes.

For ENTSO-E I created an account, got a security token and fetched physical cross-border flows for nine connections, both directions, for two years. About half of the hourly values were missing. Forward-filling omitted points did not change that. Instead, the two directions of a cable almost never had data in the same hour, so I assumed a missing hour in one direction means zero flow when the other direction is reported. Very few hours were missing in both directions, and afterwards Cassandra held 315,360 rows, exactly 9 x 2 x 17,520 hours.

The data went into Cassandra (in Docker) through Spark, was read back with Spark and aggregated to one document per connection, direction, year and month. These 450 documents are stored in MongoDB Atlas. The setup took the most time: a MongoDB authentication error (solved with a new password), Spark advertising my computer’s hostname instead of localhost (fixed with spark.driver.host), and PySpark 3.5 clashing with pandas 3 and Python 3.12, which I avoided with an explicit schema and collect() instead of toPandas().

In Streamlit I rebuilt the pages. The table and plot pages use st.radio for area type and a select slider for the month interval, and the all-columns plot is min-max normalised for one area. The flow page has two columns with a pie chart (radio and year), a line plot (st.pills for months) and an expander documenting the source. Credentials live in No_sync/secrets.toml locally and in Streamlit secrets online, never on GitHub. Code repeated in part 1 now sits in the modules folder.

AI usage

I used Claude (Anthropic) as a programming assistant throughout part 2, and Gemini and Copilot earlier in the course. The AI helped me to:

Design the project structure and move repeated code into shared modules (helpers, API access, analysis, database access).
Write the first versions of the NVE and ENTSO-E API code, the Spark and Cassandra cells, the MongoDB code and the Streamlit pages.
Debug errors I ran into: the NVE response format, MongoDB authentication, the Spark hostname problem, the PySpark and pandas incompatibility, the missing ENTSO-E hours and a duplicate page name in Streamlit.

I ran all code myself, read the error messages and results, and decided on the data handling choices, such as the zero-flow assumption. I verified results by checking row counts (for example 315,360 rows in Cassandra) and that the plots matched the data. Passwords and API tokens were kept out of the AI conversation and out of GitHub.

"""
)
