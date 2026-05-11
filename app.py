import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import datetime
import numpy as np

# --- PAGE CONFIG ---
st.set_page_config(page_title="Eastbourne Wind", layout="wide")

# --- CSS: HIDE HEADER & MOBILE FIX ---
st.markdown("""
    <style>
        [data-testid="stHeader"], header { visibility: hidden; height: 0; }
        .stAppViewContainer { top: -45px !important; }
        .stApp { background-color: #3d5a73; color: #f8f9fa; }
        .block-container { 
            padding-top: 3rem !important; 
            padding-left: 0.5rem !important;
            padding-right: 0.5rem !important;
        }
        .custom-title {
            text-align: center;
            font-size: 1.8rem;
            font-weight: 700;
            color: #ffffff;
            margin-bottom: 0.8rem;
        }
    </style>
    <div class="custom-title">Eastbourne Wind</div>
""", unsafe_allow_html=True)

# --- SETTINGS & RATINGS ---
LAT, LON = -41.291, 174.894

def get_color(knots):
    if knots <= 6: return "rgba(173, 216, 230, 1.0)"    
    if knots <= 11: return "rgba(135, 206, 250, 1.0)"   
    if knots <= 15: return "rgba(0, 128, 0, 1.0)"       
    if knots <= 19: return "rgba(255, 200, 50, 1.0)"    
    if knots <= 28: return "rgba(255, 0, 0, 1.0)"       
    return "rgba(139, 0, 0, 1.0)"                       

@st.cache_data(ttl=600)
def get_dashboard_data():
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": LAT, "longitude": LON,
        "hourly": ["wind_speed_10m", "wind_gusts_10m", "wind_direction_10m"],
        "daily": ["sunrise", "sunset"],
        "timezone": "Pacific/Auckland", "wind_speed_unit": "kn", "forecast_days": 7
    }
    r = requests.get(url, params=params).json()
    df = pd.DataFrame({
        "time": pd.to_datetime(r["hourly"]["time"]),
        "speed": r["hourly"]["wind_speed_10m"],
        "gust": r["hourly"]["wind_gusts_10m"],
        "dir": r["hourly"]["wind_direction_10m"]
    })
    sun = pd.DataFrame({
        "date": pd.to_datetime(r["daily"]["time"]).date,
        "sunrise": pd.to_datetime(r["daily"]["sunrise"]),
        "sunset": pd.to_datetime(r["daily"]["sunset"])
    })
    
    tide_times = pd.date_range(start=df['time'].min(), periods=24*7, freq='h')
    tide_heights = [1.0 + 0.6 * np.sin(2 * np.pi * (t.hour + t.minute/60) / 12.4) for t in tide_times]
    df_tide = pd.DataFrame({"time": tide_times, "height": tide_heights})
    
    return df, sun, df_tide

try:
    df, sun, df_tide = get_dashboard_data()
    # Correcting 'now' for NZ timezone offset
    now = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=12))).replace(tzinfo=None)

    # --- CREATE SUBPLOTS ---
    fig = make_subplots(
        rows=3, cols=1, 
        shared_xaxes=True, 
        vertical_spacing=0.02,
        row_heights=[0.02, 0.15, 0.10]
    )

    # 1. HEATSTRIP
    for i in range(len(df)):
        fig.add_trace(go.Bar(
            x=[df.iloc[i]['time']], y=[1],
            marker_color=get_color(df.iloc[i]['speed']),
            showlegend=False, hoverinfo='none'
        ), row=1, col=1)

    # 2. WIND LINE
    fig.add_trace(go.Scatter(x=df['time'], y=df['gust'], fill='tonexty', fillcolor='rgba(255,255,255,0.05)', line=dict(width=0), showlegend=False), row=2, col=1)
    fig.add_trace(go.Scatter(x=df['time'], y=df['speed'], line=dict(color='white', width=2), showlegend=False), row=2, col=1)

    # 3. TIDE
    fig.add_trace(go.Scatter(x=df_tide['time'], y=df_tide['height'], fill='tozeroy', fillcolor='rgba(0, 212, 255, 0.2)', line=dict(color='#00d4ff', width=2), showlegend=False), row=3, col=1)

    # NIGHT SHADING & NOW LINE
    for i in range(len(sun)-1):
        fig.add_vrect(x0=sun.iloc[i]['sunset'], x1=sun.iloc[i+1]['sunrise'], fillcolor="rgba(0,0,0,0.3)", layer="below", line_width=0)
    fig.add_vline(x=now, line_width=1.5, line_dash="dash", line_color="white", opacity=0.8)

    # LAYOUT
    fig.update_layout(
        height=450,
        margin=dict(l=10, r=10, t=20, b=20),
        template="plotly_dark",
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        bargap=0,
        xaxis3=dict(showgrid=False, tickformat="%a", dtick=86400000.0, tickfont=dict(size=10), fixedrange=True),
        xaxis=dict(visible=False, fixedrange=True),
        xaxis2=dict(visible=False, fixedrange=True),
        yaxis=dict(visible=False, fixedrange=True),
        # FIXED: Using nested title font dictionary
        yaxis2=dict(
            title=dict(text="Knots", font=dict(size=10)), 
            showgrid=True, gridcolor='rgba(255,255,255,0.05)', 
            zeroline=False, fixedrange=True
        ),
        yaxis3=dict(visible=False, fixedrange=True)
    )

    st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

except Exception as e:
    st.error(f"Dashboard Error: {e}")
