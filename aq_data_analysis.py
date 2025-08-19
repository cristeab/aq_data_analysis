#!/usr/bin/env python3

import os
from datetime import datetime, timedelta, timezone
from influxdb_client_3 import InfluxDBClient3
import streamlit as st


AUTH_SCHEME = "Bearer"
URL = "http://192.168.77.44:8181"
TOKEN = os.environ.get("INFLUXDB3_AUTH_TOKEN")

if not TOKEN:
    st.error("INFLUXDB3_AUTH_TOKEN environment variable is not set.")
    st.stop()

@st.cache_data
def get_data(bucket, measurement, minutes=30, stop_time_local=None):
    if stop_time_local is None:
        stop_time_local = datetime.now()

    # Make it timezone-aware (UTC)
    stop_time_utc = stop_time_local.astimezone(timezone.utc)
    start_time_utc = stop_time_utc - timedelta(minutes=minutes)

    # Format for InfluxDB (RFC 3339 with Z suffix)
    start_time_str = start_time_utc.isoformat().replace('+00:00', 'Z')
    stop_time_str = stop_time_utc.isoformat().replace('+00:00', 'Z')

    client = InfluxDBClient3(host=URL, token=TOKEN, database=bucket, auth_scheme=AUTH_SCHEME)
    sql = (
        f'SELECT * FROM "{measurement}" '
        f'WHERE time >= \'{start_time_str}\' AND time <= \'{stop_time_str}\''
    )
    result_df = client.query(query=sql, language="sql", mode="pandas")
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

# Add combo box for selecting the bucket
bucket_name = st.selectbox("Select Bucket", ["temperature", "noise", "aqi", "pm", "light"])

# Select measurement based on the selected bucket
if bucket_name == "temperature":
    measurement = "ambient_data"
elif bucket_name == "noise":
    measurement = "noise_level"
elif bucket_name == "aqi":
    measurement = "air_quality_data"
elif bucket_name == "pm":
    sensor_index = st.selectbox("Select AQ Sensor", [0, 1])
    measurement = f"air_quality_data_{sensor_index}"
elif bucket_name == "light":
    measurement = "light_data"
else:    
    st.error("No measurement for the selected bucket.")
    st.stop()

chart_df = get_data(bucket=bucket_name, measurement=measurement, minutes=time_range_min, stop_time_local=stop_datetime)

# Filter columns to exclude those starting with "_" or named "result" or "table"
valid_columns = [col for col in chart_df.columns if not col.startswith("_") and col not in ["result", "table", "time"]]

# Add a combo box for selecting the column name
column_name = st.selectbox(f"Select Column from bucket {bucket_name}", valid_columns)

#ensure there is data for the selected time range
if column_name not in chart_df.columns:
    st.error("No data found for the selected time range.")
    st.stop()

if column_name == "gas":
    # Convert gas resistance to kilo-ohms
    chart_df[column_name] = chart_df[column_name] / 1000
    pretty_name = "Gas Resistance (kOhms)"
elif column_name == "temperature":
    pretty_name = "Temperature (Celsius)"
elif column_name == "relative_humidity":
    pretty_name = "Humidity (%)"
elif column_name == "pressure":
    pretty_name = "Pressure (hPa)"
elif column_name == "iaq":
    pretty_name = "IAQ Index"
elif column_name == "noise_level":
    pretty_name = "Noise Level (dB)"
elif column_name == "pm25_cf1_aqi":
    pretty_name = "10-min AQI"
elif column_name == "visible_light_lux":
    pretty_name = "Visible Light (lux)"
elif column_name == "us_index":
    pretty_name = "UV Index"
else:
    pretty_name = column_name

# Round to one digit after the decimal point
chart_df[column_name] = chart_df[column_name].round(1)
chart_df.rename(columns={"time": "Date-Time", column_name: pretty_name},
                inplace=True)
st.title(pretty_name)
st.write("## Line Chart")
st.line_chart(chart_df, x="Date-Time", y=pretty_name)
