#!/usr/bin/env python3

import os
from influxdb_client import InfluxDBClient
import streamlit as st

ORG = "home"
URL = "http://192.168.77.81:8086"
BUCKET = "temperature"
TOKEN = os.environ.get("INFLUX_TOKEN")

@st.cache
def get_gas_resistance(time_range=20):
    client = InfluxDBClient(url=URL, token=TOKEN, org=ORG)
    query_api = client.query_api()
    result_df = query_api.query_data_frame(f'from(bucket:"{BUCKET}") '
    f'|> range(start: -{time_range}y) '
    '|> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value") '
    '|> keep(columns: ["_time","Measured Fluid", "T (degC)"])')
    client.close()

    return result_df