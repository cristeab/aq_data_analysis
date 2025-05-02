#!/usr/bin/env python3

import os
from influxdb_client import InfluxDBClient
import streamlit as st

ORG = "home"
URL = "http://192.168.77.81:8086"
BUCKET = "temperature"
TOKEN = os.environ.get("INFLUX_TOKEN")

@st.cache_data
def get_gas_resistance(time_range=30):
    client = InfluxDBClient(url=URL, token=TOKEN, org=ORG)
    query_api = client.query_api()
    result_df = query_api.query_data_frame(f'from(bucket:"{BUCKET}") '
    f'|> range(start: -{time_range}m) '
    '|> filter(fn: (r) => r._measurement == "ambient_data") '
    '|> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")')
    client.close()

    return result_df

chart_df = get_gas_resistance()
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
