#!/usr/bin/env python3

import os
from datetime import datetime, timedelta, timezone
from influxdb_client import InfluxDBClient
import streamlit as st

ORG = "home"
URL = "http://192.168.77.81:8086"
BUCKET = "temperature"
TOKEN = os.environ.get("INFLUX_TOKEN")

@st.cache_data
def get_gas_resistance(minutes=30, stop_time=None):
    if stop_time is None:
        stop_time = datetime.now()
    client = InfluxDBClient(url=URL, token=TOKEN, org=ORG)
    query_api = client.query_api()

    # Make it timezone-aware (UTC)
    stop_time_utc = stop_time.replace(tzinfo=timezone.utc)

    start_time_utc = stop_time_utc - timedelta(minutes=minutes)# Format for InfluxDB (RFC 3339 with Z suffix)
    start_time_str = start_time_utc.isoformat().replace('+00:00', 'Z')
    stop_time_str = stop_time_utc.isoformat().replace('+00:00', 'Z')

    print(start_time_str, stop_time_str)

    result_df = query_api.query_data_frame(f'from(bucket:"{BUCKET}") '
    f'|> range(start: {start_time_str}, stop: {stop_time_str}) '
    '|> filter(fn: (r) => r._measurement == "ambient_data") '
    '|> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")')
    client.close()

    return result_df

# Add a slider to select the time range
time_range_min = st.slider("Select time range (minutes)", min_value=10, max_value=10*60, value=30, step=10)

# Add inputs for selecting the stop time
st.write("### Select Stop Time")
stop_date = st.date_input("Stop Date", value=datetime.now().date())
stop_time = st.time_input("Stop Time", value=datetime.now().time())
stop_datetime = datetime.combine(stop_date, stop_time)

# Add a button to reset the stop time to the current date and time
if st.button("Reset Stop Time to Now"):
    stop_datetime = datetime.now()

chart_df = get_gas_resistance(minutes=time_range_min, stop_time=stop_datetime)
# Convert gas resistance to kilo-ohms
chart_df["gas"] = chart_df["gas"] / 1000
# Round to one digit after the decimal point
chart_df["gas"] = chart_df["gas"].round(1)

chart_df.rename(columns={"_time": "Date-Time", "gas": "Gas Resistance (kOhms)"},
                inplace=True)
#print(chart_df)
st.title("Gas Resistance")
st.write("## Line Chart")
st.line_chart(chart_df, x="Date-Time", y="Gas Resistance (kOhms)")
