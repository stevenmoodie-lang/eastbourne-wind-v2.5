import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go
import datetime
import numpy as np

# --- PAGE CONFIG ---
st.set_page_config(page_title="Eastbourne Wind - Simple", layout="wide")

st.markdown("""
    <style>
        .stApp { background-color: #3d5a73; color: #f8f9fa; }
        .block-container { padding-top: 1.5rem; padding-bottom: 0rem; }
    </style>
""", unsafe_allow_html=True)

# --- SETTINGS ---
LAT, LON = -41.291, 174.894  # Eastbourne Beach

def get_color(knots):
    if knots < 5: return "rgba(173, 216, 230, 1.0)"    # lightblue
    if knots <= 10: return "rgba(30, 144, 255, 1.0)"  # dodgerblue
    if knots <= 15: return "rgba(0, 128, 0, 1.0)"      # green
    if knots <= 19: return "rgba(255, 200, 50, 1.0)"   # amber
    if knots <= 28: return "rgba(255, 0, 0, 1.0)"      # red
    return "rgba(139, 0, 0, 1.0)"                      # darkred

def get_arrow_y(deg):
    """
    Position based on where the wind is FROM.
    Northerly (from N) -> Top
    Southerly (from S) -> Bottom
    """
    if (deg >= 337.5) or (deg < 22.5): return 0.8  # Northerly
    if (157.5 <= deg < 202.5): return 0.2          # Southerly
    return 0.5                                      # Other (Middle)

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
    
    # Process Hourly
    df = pd.DataFrame({
        "time": pd.to_datetime(r["hourly"]["time"]),
        "speed": r["hourly"]["wind_speed_10m"],
        "dir": r["hourly"]["wind_direction_10m"]
    })
    
    # Process Sun Data - FIXED THE .date ERROR HERE
    sun = pd.DataFrame({
        "date": pd.to_datetime(r["daily"]["time"]).date,
        "sunrise": pd.to_datetime(r["daily"]["sunrise"]),
        "sunset": pd.to_datetime(r["daily"]["sunset"])
    })
    return df, sun

# --- DATA PROCESSING ---
try:
    df_hourly, df_sun = get_eastbourne_data()

    segments = []
    for _, day in df_sun.iterrows():
        sunrise, sunset = day['sunrise'], day['sunset']
        # Divide daylight into 3 equal segments
        seg_duration = (sunset - sunrise) / 3
        
        for i in range(3):
            t0 = sunrise + (i * seg_duration)
            t1 = sunrise + ((i + 1) * seg_duration)
            
            mask = (df_hourly['time'] >= t0) & (df_hourly['time'] < t1)
            seg_data = df_hourly[mask]
            
            if not seg_data.empty:
                # Vector average for wind direction (more accurate)
                rads = np.deg2rad(seg_data['dir'])
                avg_dir = np.rad2deg(np.arctan2(np.sin(rads).mean(), np.cos(rads).mean())) % 360
                
                segments.append({
                    "day_label": day['date'].strftime("%a %d"),
                    "seg_num": i,
                    "speed": seg_data['speed'].mean(),
                    "dir": avg_dir,
                    "x_id": f"{day['date']}_{i}"
                })
        
        # Add a "Spacer" segment after each day for visual separation
        segments.append({"x_id": f"{day['date']}_spacer", "spacer": True})

    # --- UI ---
    st.title("Eastbourne Wind Outlook")

    fig = go.Figure()

    for s in segments:
        if "spacer" in s:
            # Add an invisible bar to act as a gap
            fig.add_trace(go.Bar(x=[s['x_id']], y=[1], marker_color="rgba(0,0,0,0)", showlegend=False, hoverinfo='skip'))
            continue

        # Color based on speed
        color = get_color(s['speed'])
        
        # Draw the main segment bar
        fig.add_trace(go.Bar(
            x=[s['x_id']], y=[1],
            marker_color=color,
            showlegend=False,
            hoverinfo='none'
        ))

        # Arrow logic: Points where wind is HEADING
        heading = (s['dir'] + 180) % 360
        
        fig.add_annotation(
            x=s['x_id'], y=get_arrow_y(s['dir']),
            text="➤", showarrow=False,
            textangle=heading - 90,
            font=dict(size=22, color="white")
        )

        # Wind Speed Label (centered)
        fig.add_annotation(
            x=s['x_id'], y=0.5,
            text=f"<b>{round(s['speed'])}</b>",
            showarrow=False,
            font=dict(size=13, color="white"),
            # Shift text if it clashes with the arrow
            yshift=22 if get_arrow_y(s['dir']) == 0.5 else 0
        )

    # Date Labels (placed below the groups)
    unique_days = df_sun['date']
    tick_vals = [f"{d}_1" for d in unique_days] # Center label on the middle segment
    tick_text = [f"<b>{d.strftime('%a')}</b>" for d in unique_days]

    fig.update_layout(
        height=200,
        margin=dict(l=10, r=10, t=10, b=30),
        template="plotly_dark",
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        bargap=0, # We handle gaps via spacer bars
        xaxis=dict(
            showgrid=False, 
            tickmode='array',
            tickvals=tick_vals,
            ticktext=tick_text,
            fixedrange=True
        ),
        yaxis=dict(showgrid=False, visible=False, range=[0, 1], fixedrange=True)
    )

    st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

except Exception as e:
    st.error(f"Error initializing simple view: {e}")

st.info("Top arrow = Northerly | Bottom arrow = Southerly | Middle = Other. Arrow points where wind is heading.")
