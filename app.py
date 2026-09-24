import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
from datetime import datetime

st.set_page_config(page_title="PS2 Retro Market & Sentiment Tracker", page_icon="🎮", layout="wide")

@st.cache_data(ttl=60)  # Lower cache TTL to refresh quickly when CSV updates
def load_data():
    try:
        df = pd.read_csv("ps2_sentiment_history.csv")
        df['Date'] = pd.to_datetime(df['Date'])
        return df
    except Exception:
        # Fallback if CSV doesn't exist yet
        return pd.DataFrame()

df = load_data()

if df.empty:
    st.warning("⚠️ No data found in `ps2_sentiment_history.csv`. Please trigger your GitHub Action scraper!")
    st.stop()

# Ensure regional price columns exist in DataFrame even if old CSV entries miss them
for col in ['Price_US_USD', 'Price_PAL_USD', 'Price_JP_USD']:
    if col not in df.columns:
        df[col] = df.get('CIB_Price_USD', np.nan)

latest_date = df['Date'].max()
latest_df = df[df['Date'] == latest_date].copy()

def calculate_signal(row):
    price = row.get('Price_US_USD') or row.get('CIB_Price_USD') or 0
    hype = row.get('Hype_Index', 0)
    if hype > 65 and price < 80:
        return "🟢 BUY SIGNAL"
    elif hype > 80 and price > 150:
        return "🔴 OVERHEATED"
    else:
        return "🟡 STABLE HOLD"

latest_df['Market_Signal'] = latest_df.apply(calculate_signal, axis=1)

# --- HEADER & METRICS ---
st.title("🎮 PS2 Market Sentiment & Regional Price Dashboard")
st.caption("Tracking NTSC-U, PAL, and NTSC-J real eBay CIB sales alongside web sentiment.")

col1, col2, col3, col4 = st.columns(4)
top_hype = latest_df.loc[latest_df['Hype_Index'].idxmax()]
top_price = latest_df.loc[latest_df['CIB_Price_USD'].idxmax()]

col1.metric("Highest Hype Index", f"{top_hype['Game']}", f"{top_hype['Hype_Index']} pts")
col2.metric("Most Expensive Title", f"{top_price['Game']}", f"${top_price['CIB_Price_USD']:.2f}" if pd.notnull(top_price['CIB_Price_USD']) else "N/A")
col3.metric("Total Tracked Titles", len(latest_df))
col4.metric("Last Pipeline Sync", latest_date.strftime("%Y-%m-%d"))

st.divider()

# --- CHARTS ---
tab1, tab2 = st.columns([1, 1])

with tab1:
    st.subheader("📈 Hype Index vs. CIB Market Price")
    latest_df['Bubble_Size'] = latest_df['Mercari_Listings'].apply(lambda x: max(int(x), 5) if pd.notnull(x) else 5)

    fig_scatter = px.scatter(
        latest_df,
        x="Hype_Index",
        y="CIB_Price_USD",
        color="Market_Signal",
        hover_name="Game",
        size="Bubble_Size",
        size_max=25,
        hover_data={
            "Hype_Index": ":.1f",
            "Price_US_USD": ":$.2f",
            "Price_PAL_USD": ":$.2f",
            "Price_JP_USD": ":$.2f",
            "Mercari_Listings": True,
            "Bubble_Size": False
        },
        labels={"Hype_Index": "Hype Index Score", "CIB_Price_USD": "Primary Price (USD)"},
        template="plotly_dark",
        height=450
    )
    st.plotly_chart(fig_scatter, use_container_width=True)

with tab2:
    st.subheader("📜 Historical Price & Sentiment Trend")
    selected_game = st.selectbox("Select Benchmark Title", df['Game'].unique())
    game_history = df[df['Game'] == selected_game].sort_values("Date")
    
    fig_line = go.Figure()
    fig_line.add_trace(go.Scatter(x=game_history['Date'], y=game_history['CIB_Price_USD'], name="CIB Price ($)", line=dict(color='#00CE06', width=3)))
    fig_line.add_trace(go.Scatter(x=game_history['Date'], y=game_history['Hype_Index'], name="Hype Index", yaxis="y2", line=dict(color='#FF4B4B', width=2, dash='dot')))
    
    fig_line.update_layout(
        template="plotly_dark",
        height=400,
        yaxis=dict(title="Price (USD)"),
        yaxis2=dict(title="Hype Index", overlaying="y", side="right"),
        legend=dict(x=0, y=1.1, orientation="h")
    )
    st.plotly_chart(fig_line, use_container_width=True)

# --- REGIONAL DATA TABLE ---
st.subheader("⚡ Current Market Signals & Regional Metrics (Converted to USD)")

cols_to_show = [c for c in ['Game', 'Market_Signal', 'Price_US_USD', 'Price_PAL_USD', 'Price_JP_USD', 'Hype_Index', 'Google_Trend_Score', 'Mercari_Listings'] if c in latest_df.columns]

st.dataframe(
    latest_df[cols_to_show],
    column_config={
        "Price_US_USD": st.column_config.NumberColumn("NTSC-U (US)", format="$%.2f"),
        "Price_PAL_USD": st.column_config.NumberColumn("PAL (EU/UK)", format="$%.2f"),
        "Price_JP_USD": st.column_config.NumberColumn("NTSC-J (Japan)", format="$%.2f"),
        "Hype_Index": st.column_config.ProgressColumn("Hype Index", min_value=0, max_value=100),
    },
    use_container_width=True,
    hide_index=True
)
