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
        .block-container { padding-top: 1rem; padding-bottom: 0rem; }
        .day-label { font-size: 1rem; font-weight: bold; color: #f8f9fa; margin-bottom: -10px; }
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
    # Determine if it's predominantly North or South
    # 0/360 is North, 180 is South
    if (deg >= 337.5) or (deg < 22.5): return 0.8  # Northerly -> Top
    if (157.5 <= deg < 202.5): return 0.2          # Southerly -> Bottom
    return 0.5                                      # Everything else -> Middle

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
    
    # Process Sun Data
    sun = pd.DataFrame({
        "date": pd.to_datetime(r["daily"]["time"]).date(),
        "sunrise": pd.to_datetime(r["daily"]["sunrise"]),
        "sunset": pd.to_datetime(r["daily"]["sunset"])
    })
    return df, sun

# --- DATA PROCESSING ---
try:
    df_hourly, df_sun = get_eastbourne_data()

    # Create the segmented data
    segments = []
    for _, day in df_sun.iterrows():
        sunrise, sunset = day['sunrise'], day['sunset']
        day_duration = (sunset - sunrise) / 3
        
        for i in range(3):
            seg_start = sunrise + (i * day_duration)
            seg_end = sunrise + ((i + 1) * day_duration)
            
            # Filter hourly data for this segment
            mask = (df_hourly['time'] >= seg_start) & (df_hourly['time'] < seg_end)
            seg_data = df_hourly[mask]
            
            if not seg_data.empty:
                avg_speed = seg_data['speed'].mean()
                avg_dir = seg_data['dir'].mean() # Simplified avg direction
                segments.append({
                    "day": day['date'].strftime("%a %d"),
                    "seg_id": i,
                    "speed": avg_speed,
                    "dir": avg_dir,
                    "label": f"{day['date'].strftime('%a')} Seg {i+1}"
                })

    seg_df = pd.DataFrame(segments)

    # --- UI ---
    st.title("Eastbourne Wind Outlook")

    # --- HEATSTRIP CHART ---
    fig = go.Figure()

    # We use a Bar chart where each bar is one segment
    # To create gaps between days, we add a dummy empty segment or use categorical spacing
    x_labels = []
    colors = []
    
    for i, row in seg_df.iterrows():
        # Create a combined label for the X axis
        x_val = f"{row['day']} | {row['seg_id']}"
        x_labels.append(x_val)
        colors.append(get_color(row['speed']))
        
        # Add the arrow annotation
        # Direction heading = (Wind From + 180) % 360
        heading = (row['dir'] + 180) % 360
        
        fig.add_annotation(
            x=x_val,
            y=get_arrow_y(row['dir']),
            text="➤",
            showarrow=False,
            textangle=heading - 90, # Adjust for SVG rotation
            font=dict(size=18, color="white")
        )
        
        # Add speed text at the very top or bottom to keep it clear
        fig.add_annotation(
            x=x_val, y=0.5,
            text=f"<b>{round(row['speed'])}</b>",
            showarrow=False,
            font=dict(size=12, color="white"),
            yshift=0 if get_arrow_y(row['dir']) != 0.5 else 20 # Offset if arrow is in middle
        )

    fig.add_trace(go.Bar(
        x=x_labels,
        y=[1] * len(x_labels),
        marker_color=colors,
        showlegend=False,
        hoverinfo='skip'
    ))

    # Formatting
    fig.update_layout(
        height=180,
        margin=dict(l=10, r=10, t=40, b=20),
        template="plotly_dark",
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        bargap=0.1, # Gap between segments
        xaxis=dict(
            showgrid=False, 
            ticktext=[label.split(" | ")[0] if i % 3 == 1 else "" for i, label in enumerate(x_labels)],
            tickvals=x_labels,
            fixedrange=True
        ),
        yaxis=dict(showgrid=False, visible=False, range=[0, 1], fixedrange=True)
    )

    st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

except Exception as e:
    st.error(f"Error initializing simple view: {e}")

st.info("The heatstrip shows daylight hours divided into 3 segments. Arrows point where the wind is heading.")
