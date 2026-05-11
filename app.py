import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go
import datetime
import numpy as np

# --- PAGE CONFIG ---
st.set_page_config(page_title="Eastbourne Wind", layout="wide")

# --- CLEAN CSS FOR MOBILE ---
st.markdown("""
    <style>
        [data-testid="stHeader"], header { visibility: hidden; height: 0; }
        .stAppViewContainer { top: -45px !important; }
        .stApp { background-color: #3d5a73; color: #f8f9fa; }
        .block-container { 
            padding-top: 3.5rem !important; 
            padding-left: 0.5rem !important;
            padding-right: 0.5rem !important;
        }
        .custom-title {
            text-align: center;
            font-size: 1.8rem;
            font-weight: 700;
            color: #ffffff;
            margin-bottom: 0.5rem;
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
def get_weather_data():
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": LAT, "longitude": LON,
        "hourly": ["wind_speed_10m", "wind_direction_10m"],
        "daily": ["sunrise", "sunset"],
        "timezone": "Pacific/Auckland", "wind_speed_unit": "kn", "forecast_days": 7
    }
    r = requests.get(url, params=params).json()
    df = pd.DataFrame({
        "time": pd.to_datetime(r["hourly"]["time"]),
        "speed": r["hourly"]["wind_speed_10m"],
        "dir": r["hourly"]["wind_direction_10m"]
    })
    sun = pd.DataFrame({
        "date": pd.to_datetime(r["daily"]["time"]).date,
        "sunrise": pd.to_datetime(r["daily"]["sunrise"]),
        "sunset": pd.to_datetime(r["daily"]["sunset"])
    })
    return df, sun

try:
    df_hourly, df_sun = get_weather_data()

    segments = []
    for _, day in df_sun.iterrows():
        sunrise, sunset = day['sunrise'], day['sunset']
        seg_dur = (sunset - sunrise) / 3
        
        for i in range(3):
            t0, t1 = sunrise + (i*seg_dur), sunrise + ((i+1)*seg_dur)
            mask = (df_hourly['time'] >= t0) & (df_hourly['time'] < t1)
            d = df_hourly[mask]
            if not d.empty:
                rads = np.deg2rad(d['dir'])
                avg_dir = np.rad2deg(np.arctan2(np.sin(rads).mean(), np.cos(rads).mean())) % 360
                segments.append({
                    "x_id": f"{day['date']}_{i}", 
                    "speed": d['speed'].mean(), 
                    "dir": avg_dir
                })
        segments.append({"x_id": f"{day['date']}_spacer", "spacer": True})

    fig = go.Figure()

    for s in segments:
        if "spacer" in s:
            fig.add_trace(go.Bar(x=[s['x_id']], y=[1], marker_color="rgba(0,0,0,0)", showlegend=False, hoverinfo='skip'))
            continue
        
        fig.add_trace(go.Bar(
            x=[s['x_id']], y=[1], 
            marker_color=get_color(s['speed']), 
            showlegend=False, hoverinfo='none'
        ))

        heading = (s['dir'] + 180) % 360
        y_pos = 0.5 if (75 < s['dir'] < 105 or 255 < s['dir'] < 285) else (0.35 if 105 <= s['dir'] <= 255 else 0.75)
        
        fig.add_annotation(
            x=s['x_id'], y=y_pos, text="➤", showarrow=False, 
            textangle=heading-90, font=dict(size=14, color="white")
        )
        
        fig.add_annotation(
            x=s['x_id'], y=-0.35, text=f"<b>{round(s['speed'])}</b>", 
            showarrow=False, font=dict(size=11, color="white")
        )

    fig.update_layout(
        height=220, 
        margin=dict(l=5, r=5, t=30, b=10), 
        template="plotly_dark", 
        paper_bgcolor='rgba(0,0,0,0)', 
        plot_bgcolor='rgba(0,0,0,0)', 
        bargap=0,
        xaxis=dict(
            showgrid=False, 
            tickmode='array', 
            tickvals=[f"{d}_1" for d in df_sun['date']], 
            ticktext=[f"<b>{d.strftime('%a')}</b>" for d in df_sun['date']], 
            side="top", 
            # FIXED: tickfont color set to white
            tickfont=dict(size=12, color="white"),
            fixedrange=True
        ),
        yaxis=dict(visible=False, range=[-0.7, 1], fixedrange=True)
    )

    st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

except Exception as e:
    st.error(f"Layout Error: {e}")
