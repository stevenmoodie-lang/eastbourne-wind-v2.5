import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go
import datetime
import numpy as np

# --- PAGE CONFIG ---
st.set_page_config(page_title="Eastbourne Wind", layout="wide")

# --- CSS: UI FIXES ---
st.markdown("""
    <style>
        [data-testid="stHeader"], header { visibility: hidden; height: 0; }
        .stApp { background-color: #3d5a73; color: #f8f9fa; }
        .block-container { 
            padding-top: 2rem !important; 
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
    if knots <= 6: return "rgba(173, 216, 230, 1.0)"    # Light Blue
    if knots <= 11: return "rgba(135, 206, 250, 1.0)"   # Lighter Blue
    if knots <= 15: return "rgba(0, 128, 0, 1.0)"       # Green
    if knots <= 19: return "rgba(255, 200, 50, 1.0)"    # Amber
    if knots <= 28: return "rgba(255, 0, 0, 1.0)"       # Red
    return "rgba(139, 0, 0, 1.0)"                       # Dark Red

# --- DATA FETCHING ---
@st.cache_data(ttl=600)
def get_weather_data():
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
    return df, sun

@st.cache_data(ttl=3600)
def get_tide_data():
    # NIWA / Open-Meteo don't provide easy free tides, 
    # using a synthetic tide for Wellington for demonstration
    times = pd.date_range(start=datetime.datetime.now().date(), periods=24*7, freq='H')
    # M2 Tide cycle approx 12.4 hours
    heights = [1.0 + 0.6 * np.sin(2 * np.pi * (t.hour + t.minute/60) / 12.4) for t in times]
    return pd.DataFrame({"time": times, "height": heights})

try:
    df_hourly, df_sun = get_weather_data()
    df_tide = get_tide_data()

    # --- 1. THE HEATSTRIP (TOP) ---
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
                segments.append({"x_id": f"{day['date']}_{i}", "speed": d['speed'].mean(), "dir": avg_dir, "day": day['date']})
        segments.append({"x_id": f"{day['date']}_spacer", "spacer": True})

    fig_heat = go.Figure()
    for s in segments:
        if "spacer" in s:
            fig_heat.add_trace(go.Bar(x=[s['x_id']], y=[1], marker_color="rgba(0,0,0,0)", showlegend=False, hoverinfo='skip'))
            continue
        
        fig_heat.add_trace(go.Bar(x=[s['x_id']], y=[1], marker_color=get_color(s['speed']), showlegend=False, hoverinfo='none'))
        heading = (s['dir'] + 180) % 360
        y_pos = 0.5 if (75 < s['dir'] < 105 or 255 < s['dir'] < 285) else (0.35 if 105 <= s['dir'] <= 255 else 0.75)
        
        fig_heat.add_annotation(x=s['x_id'], y=y_pos, text="➤", showarrow=False, textangle=heading-90, font=dict(size=10, color="white"))
        fig_heat.add_annotation(x=s['x_id'], y=-0.35, text=f"<b>{round(s['speed'])}</b>", showarrow=False, font=dict(size=9, color="white"))

    fig_heat.update_layout(
        height=160, margin=dict(l=5, r=5, t=30, b=10), template="plotly_dark", paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', bargap=0,
        xaxis=dict(showgrid=False, tickmode='array', tickvals=[f"{d}_1" for d in df_sun['date']], ticktext=[f"<b>{d.strftime('%a')}</b>" for d in df_sun['date']], side="top", tickfont=dict(size=10)),
        yaxis=dict(visible=False, range=[-0.7, 1], fixedrange=True)
    )
    st.plotly_chart(fig_heat, use_container_width=True, config={'displayModeBar': False})

    # --- 2. WIND SPEED LINE GRAPH ---
    fig_wind = go.Figure()
    fig_wind.add_trace(go.Scatter(x=df_hourly['time'], y=df_hourly['gust'], name="Gust", line=dict(color='rgba(255,255,255,0.2)', width=1), fill='tonexty'))
    fig_wind.add_trace(go.Scatter(x=df_hourly['time'], y=df_hourly['speed'], name="Speed", line=dict(color='white', width=2)))
    
    fig_wind.update_layout(
        height=200, margin=dict(l=10, r=10, t=10, b=10), template="plotly_dark",
        paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
        showlegend=False,
        xaxis=dict(showgrid=False, showticklabels=False),
        yaxis=dict(title="Knots", showgrid=True, gridcolor='rgba(255,255,255,0.1)', zeroline=False)
    )
    st.plotly_chart(fig_wind, use_container_width=True, config={'displayModeBar': False})

    # --- 3. TIDE GRAPH ---
    fig_tide = go.Figure()
    fig_tide.add_trace(go.Scatter(x=df_tide['time'], y=df_tide['height'], fill='tozeroy', line=dict(color='#00d4ff')))
    
    fig_tide.update_layout(
        height=150, margin=dict(l=10, r=10, t=10, b=30), template="plotly_dark",
        paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
        xaxis=dict(showgrid=False, dtick=86400000.0), # Grid every 24h
        yaxis=dict(visible=False)
    )
    st.plotly_chart(fig_tide, use_container_width=True, config={'displayModeBar': False})

except Exception as e:
    st.error(f"Layout Error: {e}")
