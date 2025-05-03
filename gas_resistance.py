#!/usr/bin/env python3

import os
import sys
from datetime import datetime, timedelta, timezone
from influxdb_client import InfluxDBClient
import streamlit as st

ORG = "home"
URL = "http://192.168.77.81:8086"
BUCKET = "temperature"
TOKEN = os.environ.get("INFLUX_TOKEN")

if not TOKEN:
    print("Error: INFLUX_TOKEN environment variable is not set.")
    sys.exit(1)

@st.cache_data
def get_gas_resistance(minutes=30, stop_time_local=None):
    if stop_time_local is None:
        stop_time_local = datetime.now()

    # Make it timezone-aware (UTC)
    stop_time_utc = stop_time_local.astimezone(timezone.utc)
    start_time_utc = stop_time_utc - timedelta(minutes=minutes)

    # Format for InfluxDB (RFC 3339 with Z suffix)
    start_time_str = start_time_utc.isoformat().replace('+00:00', 'Z')
    stop_time_str = stop_time_utc.isoformat().replace('+00:00', 'Z')

    client = InfluxDBClient(url=URL, token=TOKEN, org=ORG)
    query_api = client.query_api()
    result_df = query_api.query_data_frame(f'from(bucket:"{BUCKET}") '
    f'|> range(start: {start_time_str}, stop: {stop_time_str}) '
    '|> filter(fn: (r) => r._measurement == "ambient_data") '
    '|> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")')
    client.close()

    return result_df

# Initialize session state for stop_date and stop_time
if "stop_date" not in st.session_state:
    st.session_state.stop_date = datetime.now().date()
if "stop_time" not in st.session_state:
    st.session_state.stop_time = datetime.now().time()

# Define a callback function to reset the date and time
def reset_stop_datetime():
    now = datetime.now()
    st.session_state.stop_date = now.date()
    st.session_state.stop_time = now.time()

# Add inputs for selecting the stop time
col1, col2, col3 = st.columns([2, 2, 1])  # Adjust column widths as needed
with col1:
    stop_date = st.date_input("Stop Date", key="stop_date")
with col2:
    stop_time = st.time_input("Stop Time", key="stop_time")
with col3:
    st.button("Reset Stop Date&Time", on_click=reset_stop_datetime)

# Combine stop_date and stop_time into a datetime object
stop_datetime = datetime.combine(st.session_state.stop_date, st.session_state.stop_time)

# Add a slider to select the time range
time_range_min = st.slider("Time Range (Minutes)", min_value=10, max_value=12*60, value=30, step=10)

chart_df = get_gas_resistance(minutes=time_range_min, stop_time_local=stop_datetime)
#ensure column names are correct
if "gas" not in chart_df.columns:
    st.error("No data found for the selected time range.")
    st.stop()
# Convert gas resistance to kilo-ohms
chart_df["gas"] = chart_df["gas"] / 1000
# Round to one digit after the decimal point
chart_df["gas"] = chart_df["gas"].round(1)

chart_df.rename(columns={"_time": "Date-Time", "gas": "Gas Resistance (kOhms)"},
                inplace=True)

st.title("Gas Resistance")
st.write("## Line Chart")
st.line_chart(chart_df, x="Date-Time", y="Gas Resistance (kOhms)")
