import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
from datetime import datetime

# Page Configuration
st.set_page_config(
    page_title="PS2 Retro Market & Sentiment Tracker",
    page_icon="🎮",
    layout="wide"
)

# Custom Styling
st.markdown("""
<style>
    .metric-card {
        background-color: #1E1E2E;
        padding: 15px;
        border-radius: 10px;
        border-left: 5px solid #7D56C4;
    }
    .stApp {
        background-color: #0E0E17;
    }
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# DATA LOADING & CACHING
# ---------------------------------------------------------
@st.cache_data(ttl=3600)
def load_data():
    try:
        df = pd.read_csv("ps2_sentiment_history.csv")
        df['Date'] = pd.to_datetime(df['Date'])
        return df
    except Exception:
        # Generate mock historical dataset if CSV doesn't exist yet
        dates = pd.date_range(end=datetime.today(), periods=30)
        games = ["Silent Hill 2", "Rule of Rose", "Kuon", "Def Jam Fight for NY", "God of War"]
        data = []
        for d in dates:
            for g in games:
                base_price = 120.0 if "Rule" in g or "Kuon" in g else 45.0
                data.append({
                    "Date": d,
                    "Game": g,
                    "CIB_Price_USD": round(base_price + np.random.normal(0, 5), 2),
                    "Hype_Index": round(np.random.uniform(20, 85), 2),
                    "Google_Trend_Score": np.random.randint(10, 90),
                    "News_Mentions": np.random.randint(0, 5),
                    "Mercari_Listings": np.random.randint(5, 50),
                    "RA_Active_Achievements": np.random.randint(10, 200),
                    "HLTB_Main_Hours": 12.5
                })
        return pd.DataFrame(data)

df = load_data()

# ---------------------------------------------------------
# HEADER & NAVIGATION
# ---------------------------------------------------------
st.title("🎮 PS2 Market Sentiment & Signal Dashboard")
st.caption("Automated daily intelligence tracking pricing, search volume, news coverage, and active player interest.")

latest_date = df['Date'].max()
latest_df = df[df['Date'] == latest_date].copy()

# Signal Signal Logic
def calculate_signal(row):
    if row['Hype_Index'] > 65 and row['CIB_Price_USD'] < 80:
        return "🟢 BUY SIGNAL (High Hype / Moderate Price)"
    elif row['Hype_Index'] > 80 and row['CIB_Price_USD'] > 150:
        return "🔴 OVERHEATED (Peak Demand / High Price)"
    else:
        return "🟡 STABLE HOLD"

latest_df['Market_Signal'] = latest_df.apply(calculate_signal, axis=1)

# ---------------------------------------------------------
# METRIC HIGHLIGHTS
# ---------------------------------------------------------
col1, col2, col3, col4 = st.columns(4)

top_hype = latest_df.loc[latest_df['Hype_Index'].idxmax()]
top_price = latest_df.loc[latest_df['CIB_Price_USD'].idxmax()]

col1.metric("Highest Hype Index", f"{top_hype['Game']}", f"{top_hype['Hype_Index']} pts")
col2.metric("Most Expensive Title", f"{top_price['Game']}", f"${top_price['CIB_Price_USD']:.2f}")
col3.metric("Total Tracked Titles", len(latest_df))
col4.metric("Last Pipeline Sync", latest_date.strftime("%Y-%m-%d"))

st.divider()

# ---------------------------------------------------------
# CHARTS & VISUALIZATIONS
# ---------------------------------------------------------
tab1, tab2, tab3 = st.columns([2, 2, 1])

with tab1:
    st.subheader("📈 Hype Index vs. CIB Market Price")
    fig_scatter = px.scatter(
        latest_df,
        x="Hype_Index",
        y="CIB_Price_USD",
        color="Market_Signal",
        text="Game",
        size="Mercari_Listings",
        labels={"Hype_Index": "Hype Index Score", "CIB_Price_USD": "CIB Price (USD)"},
        template="plotly_dark",
        height=450
    )
    fig_scatter.update_traces(textposition='top center')
    st.plotly_chart(fig_scatter, use_container_width=True)

with tab2:
    st.subheader("📜 Historical Price & Sentiment Trend")
    selected_game = st.selectbox("Select Benchmark Title", df['Game'].unique())
    game_history = df[df['Game'] == selected_game].sort_values("Date")
    
    fig_line = go.Figure()
    fig_line.add_trace(go.Scatter(x=game_history['Date'], y=game_history['CIB_Price_USD'], name="CIB Price ($)", line=dict(color='#00CEO6', width=3)))
    fig_line.add_trace(go.Scatter(x=game_history['Date'], y=game_history['Hype_Index'], name="Hype Index", yaxis="y2", line=dict(color='#FF4B4B', width=2, dash='dot')))
    
    fig_line.update_layout(
        template="plotly_dark",
        height=400,
        yaxis=dict(title="Price (USD)"),
        yaxis2=dict(title="Hype Index", overlaying="y", side="right"),
        legend=dict(x=0, y=1.1, orientation="h")
    )
    st.plotly_chart(fig_line, use_container_width=True)

# ---------------------------------------------------------
# MARKET SIGNALS & RAW DATA TABLE
# ---------------------------------------------------------
st.subheader("⚡ Current Market Signals & Raw Metrics")

st.dataframe(
    latest_df[['Game', 'Market_Signal', 'CIB_Price_USD', 'Hype_Index', 'Google_Trend_Score', 'News_Mentions', 'Mercari_Listings']],
    column_config={
        "CIB_Price_USD": st.column_config.NumberColumn("CIB Price", format="$%.2f"),
        "Hype_Index": st.column_config.ProgressColumn("Hype Index", min_value=0, max_value=100),
    },
    use_container_width=True,
    hide_index=True
)
