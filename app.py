import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go
import datetime
import numpy as np

# --- PAGE CONFIG ---
st.set_page_config(page_title="Eastbourne Wind", layout="wide")

# --- CSS FOR SPACING & TITLE ---
st.markdown("""
    <style>
        /* Adds space at the very top of the page */
        .block-container { 
            padding-top: 4rem !important; 
            padding-bottom: 0rem; 
        }
        .stApp { background-color: #3d5a73; color: #f8f9fa; }
        
        /* Custom Title Styling */
        .main-title {
            text-align: center;
            font-size: 2.5rem;
            font-weight: 700;
            margin-bottom: 2rem;
            color: #ffffff;
            font-family: 'Source Sans Pro', sans-serif;
        }
    </style>
    <div class="main-title">Eastbourne Wind</div>
""", unsafe_allow_html=True)

# --- SETTINGS ---
LAT, LON = -41.291, 174.894 

def get_color(knots):
    if knots <= 6: return "rgba(173, 216, 230, 1.0)"    # Light Blue
    if knots <= 11: return "rgba(135, 206, 250, 1.0)"   # Lighter Blue
    if knots <= 15: return "rgba(0, 128, 0, 1.0)"       # Green
    if knots <= 19: return "rgba(255, 200, 50, 1.0)"    # Amber
    if knots <= 28: return "rgba(255, 0, 0, 1.0)"       # Red
    return "rgba(139, 0, 0, 1.0)"                       # Dark Red

def get_arrow_y(deg):
    if (75 < deg < 105) or (255 < deg < 285):
        return 0.65 
    if (105 <= deg <= 255):
        return 0.42 
    return 0.88     

@st.cache_data(ttl=600)
def get_eastbourne_data():
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": LAT, "longitude": LON,
        "hourly": ["wind_speed_10m", "wind_direction_10m"],
        "daily": ["sunrise", "sunset"],
        "timezone": "Pacific/Auckland", "wind_speed_unit": "kn", "forecast_days": 7
    }
    r = requests.get(url, params=params).json()
    df = pd.DataFrame({"time": pd.to_datetime(r["hourly"]["time"]), "speed": r["hourly"]["wind_speed_10m"], "dir": r["hourly"]["wind_direction_10m"]})
    sun = pd.DataFrame({"date": pd.to_datetime(r["daily"]["time"]).date, "sunrise": pd.to_datetime(r["daily"]["sunrise"]), "sunset": pd.to_datetime(r["daily"]["sunset"])})
    return df, sun

try:
    df_hourly, df_sun = get_eastbourne_data()
    segments = []

    for _, day in df_sun.iterrows():
        sunrise, sunset = day['sunrise'], day['sunset']
        seg_duration = (sunset - sunrise) / 3
        for i in range(3):
            t0, t1 = sunrise + (i * seg_duration), sunrise + ((i + 1) * seg_duration)
            mask = (df_hourly['time'] >= t0) & (df_hourly['time'] < t1)
            seg_data = df_hourly[mask]
            if not seg_data.empty:
                rads = np.deg2rad(seg_data['dir'])
                avg_dir = np.rad2deg(np.arctan2(np.sin(rads).mean(), np.cos(rads).mean())) % 360
                segments.append({"day_label": day['date'].strftime("%a %d"), "seg_num": i, "speed": seg_data['speed'].mean(), "dir": avg_dir, "x_id": f"{day['date']}_{i}"})
        segments.append({"x_id": f"{day['date']}_spacer", "spacer": True})

    fig = go.Figure()

    for s in segments:
        if "spacer" in s:
            fig.add_trace(go.Bar(x=[s['x_id']], y=[1], marker_color="rgba(0,0,0,0)", showlegend=False, hoverinfo='skip'))
            continue

        fig.add_trace(go.Bar(x=[s['x_id']], y=[1], marker_color=get_color(s['speed']), showlegend=False, hoverinfo='none'))

        heading = (s['dir'] + 180) % 360
        fig.add_annotation(
            x=s['x_id'], y=get_arrow_y(s['dir']),
            text="➤", showarrow=False,
            textangle=heading - 90,
            font=dict(size=20, color="white") 
        )

        fig.add_annotation(
            x=s['x_id'], y=0.12,
            text=f"<b>{round(s['speed'])}</b>",
            showarrow=False,
            font=dict(size=12, color="rgba(255,255,255,0.95)"),
        )

    tick_vals = [f"{d}_1" for d in df_sun['date']]
    tick_text = [f"<b>{d.strftime('%a')}</b>" for d in df_sun['date']]

    fig.update_layout(
        height=160,
        margin=dict(l=10, r=10, t=30, b=45),
        template="plotly_dark",
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        bargap=0,
        xaxis=dict(
            showgrid=False, tickmode='array', tickvals=tick_vals, ticktext=tick_text, 
            fixedrange=True, tickfont=dict(size=13, color="white")
        ),
        yaxis=dict(showgrid=False, visible=False, range=[0, 1], fixedrange=True)
    )

    st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

except Exception as e:
    st.error(f"Error: {e}")
