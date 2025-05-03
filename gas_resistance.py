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
time_range_min = st.slider("Time Range (Minutes)", min_value=10, max_value=24*60, value=6*60, step=10)

chart_df = get_gas_resistance(minutes=time_range_min, stop_time_local=stop_datetime)

# Filter columns to exclude those starting with "_" or named "result" or "table"
valid_columns = [col for col in chart_df.columns if not col.startswith("_") and col not in ["result", "table"]]

# Add a combo box for selecting the column name
column_name = st.selectbox(f"Select Column from bucket {BUCKET}", valid_columns)

#ensure there is data for the selected time range
if column_name not in chart_df.columns:
    st.error("No data found for the selected time range.")
    st.stop()

if column_name == "gas":
    # Convert gas resistance to kilo-ohms
    chart_df[column_name] = chart_df[column_name] / 1000
    # Round to one digit after the decimal point
    chart_df[column_name] = chart_df[column_name].round(1)
    pretty_name = "Gas Resistance (kOhms)"
elif column_name == "temperature":
    chart_df[column_name] = chart_df[column_name].round(1)
    pretty_name = "Temperature (Celsius)"
elif column_name == "relative_humidity":
    chart_df[column_name] = chart_df[column_name].round(1)
    pretty_name = "Humidity (%)"
elif column_name == "pressure":
    chart_df[column_name] = chart_df[column_name].round(1)
    pretty_name = "Pressure (hPa)"
elif column_name == "iaq":
    chart_df[column_name] = chart_df[column_name].round(1)
    pretty_name = "IAQ Index"
else:
    pretty_name = column_name

chart_df.rename(columns={"_time": "Date-Time", column_name: pretty_name},
                inplace=True)
st.title(pretty_name)
st.write("## Line Chart")
st.line_chart(chart_df, x="Date-Time", y=pretty_name)
