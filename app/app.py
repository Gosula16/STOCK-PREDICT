import os
from datetime import datetime, timedelta

import pandas as pd
import plotly.express as px
import streamlit as st

from utils import align_actuals_and_forecasts, load_actuals_jan2024, load_forecasts_jan2024


st.set_page_config(
    page_title="Wind Forecast Monitor",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("UK Wind Power Forecast Monitoring")

st.markdown(
    """This app shows *actual* vs *forecast* wind generation for the UK (January 2024).

- Actuals are taken from BMRS `FUELHH` (fuelType=WIND)
- Forecasts are taken from BMRS `WINDFOR`

Use the controls to select a date range and the forecast horizon (hours)."""
)

# Controls
col1, col2 = st.sidebar.columns(2)

with col1:
    start_date = st.date_input("Start date", value=datetime(2024, 1, 1))
    end_date = st.date_input("End date", value=datetime(2024, 1, 7))

with col2:
    horizon = st.slider("Forecast horizon (hours)", min_value=0, max_value=48, value=4, step=1)

st.sidebar.markdown("---")
st.sidebar.markdown("**API Key** (optional): Set `BMRS_API_KEY` in environment variables.")

# Load data
@st.cache_data(show_spinner=False)
def _load_data():
    a = load_actuals_jan2024()
    f = load_forecasts_jan2024()
    return a, f

try:
    actuals_df, forecasts_df = _load_data()
except Exception as e:
    st.error(
        "Unable to load BMRS data. Make sure BMRS_API_KEY is set in your environment and you have network access.\n"
        + str(e)
    )
    st.stop()


# Align data for visualization
selected = align_actuals_and_forecasts(
    actuals_df, forecasts_df, horizon_hours=horizon, start=start_date, end=end_date
)

if selected.empty:
    st.warning("No data available for the selected date range and horizon. Try expanding the range.")
    st.stop()

# Display metrics
col_actual, col_forecast = st.columns(2)
col_actual.metric("Data points (actual)", len(selected.dropna(subset=["actual"])))
col_forecast.metric("Data points (forecast)", len(selected.dropna(subset=["forecast"])))

# Compute basic error metrics
selected = selected.dropna(subset=["forecast", "actual"])
selected["error"] = selected["forecast"] - selected["actual"]
selected["abs_error"] = selected["error"].abs()

mae = selected["abs_error"].mean()
rmse = (selected["error"] ** 2).mean() ** 0.5
p50 = selected["abs_error"].quantile(0.5)
p90 = selected["abs_error"].quantile(0.9)

st.markdown("### Forecast Error Summary")
col1, col2, col3, col4 = st.columns(4)
col1.metric("MAE", f"{mae:.2f} MW")
col2.metric("RMSE", f"{rmse:.2f} MW")
col3.metric("Median abs error", f"{p50:.2f} MW")
col4.metric("90th pct abs error", f"{p90:.2f} MW")

# Plot
st.markdown("### Actual vs Forecast")

fig = px.line(
    selected,
    x="startTime",
    y=["actual", "forecast"],
    labels={"value": "Generation (MW)", "startTime": "Time"},
    title=f"Actual vs Forecast (horizon={horizon}h)",
)
fig.update_layout(legend_title_text="Series")
st.plotly_chart(fig, use_container_width=True)

st.markdown("---")

st.markdown(
    "### Notes\n\n- Forecasts are selected as the latest available forecast created at least the horizon hours before the target time.\n- Some timestamps may be missing if forecasts were not available at the required lead time."  
)

if st.checkbox("Show raw data", value=False):
    st.dataframe(selected)
