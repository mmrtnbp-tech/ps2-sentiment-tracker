import streamlit as st
import json
import os
import pandas as pd
from scraper import run_scraper

st.set_page_config(page_title="PS2 Market Intelligence & Sentiment Engine", layout="wide")

@st.cache_data
def load_master_catalog():
    if os.path.exists("master_ps2_catalog.json"):
        with open("master_ps2_catalog.json", "r", encoding="utf-8") as f:
            return json.load(f)
    return []

# Sidebar Controls
with st.sidebar:
    st.title("⚙️ Controls")
    if st.button("🔄 Refresh Market Data", use_container_width=True):
        with st.spinner("Executing market query cycle..."):
            run_scraper()
            st.cache_data.clear()
        st.success("Market metrics updated!")
        st.rerun()

st.title("🎮 PS2 Market Intelligence & Sentiment Engine")

csv_file = "ps2_sentiment_history.csv"

# First-time setup fallback
if not os.path.exists(csv_file):
    st.warning("⚠️ No historical market data detected.")
    if st.button("🚀 Initialize Market Scraper"):
        with st.spinner("Generating initial dataset..."):
            run_scraper()
            st.cache_data.clear()
        st.success("Dataset generated!")
        st.rerun()
    st.stop()

# Load Data
df = pd.read_csv(csv_file)
latest_date = df['Date'].max()
latest_df = df[df['Date'] == latest_date].copy()

# ==============================================================================
# 1. MASTER DATABASE DROPDOWN & INDIVIDUAL METRICS
# ==============================================================================
catalog = load_master_catalog()
all_titles = [g["title"] for g in catalog] if catalog else df['Game'].unique().tolist()

st.subheader("🔎 Master Catalog Deep Dive")
selected_game = st.selectbox("Search Master Database:", all_titles)

game_history = df[df["Game"] == selected_game]

if not game_history.empty:
    latest_row = game_history.iloc[-1]
    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("CIB Price (USD)", f"${latest_row['CIB_Price_USD']:.2f}")
    m2.metric("CeX PAL Price (£)", f"£{latest_row['Price_PAL_GBP']:.2f}")
    m3.metric("Est. Market Cap", f"${latest_row['Market_Cap_USD']:,.2f}")
    m4.metric("Hype Score", f"{latest_row['Hype_Index']}/100")
    m5.metric("Market Signal", latest_row['Market_Signal'])
else:
    st.info(f"'{selected_game}' is stored in the master catalog but is currently on hold.")

st.divider()

# ==============================================================================
# 2. TRENDING DASHBOARD & HYPE ANALYTICS
# ==============================================================================
st.subheader("🔥 Trending Games & Social Hype Analytics")
col_left, col_right = st.columns(2)

with col_left:
    st.markdown("##### 🚀 Top Trending by Hype Index")
    trending_df = latest_df.sort_values(by="Hype_Index", ascending=False).head(5)
    st.dataframe(
        trending_df[['Game', 'Hype_Index', 'CIB_Price_USD', 'Market_Signal']],
        column_config={
            "Hype_Index": st.column_config.ProgressColumn("Hype Score", min_value=0, max_value=100),
            "CIB_Price_USD": st.column_config.NumberColumn("Price ($)", format="$%.2f")
        },
        use_container_width=True,
        hide_index=True
    )

with col_right:
    st.markdown("##### 📈 Top Valuation Gainers (Market Cap)")
    val_df = latest_df.sort_values(by="Market_Cap_USD", ascending=False).head(5)
    st.dataframe(
        val_df[['Game', 'Market_Cap_USD', 'Price_PAL_GBP', 'Market_Signal']],
        column_config={
            "Market_Cap_USD": st.column_config.NumberColumn("Market Cap ($)", format="$%.2f"),
            "Price_PAL_GBP": st.column_config.NumberColumn("PAL Price (£)", format="£%.2f")
        },
        use_container_width=True,
        hide_index=True
    )

st.divider()

# ==============================================================================
# 3. REGIONAL METRICS & MARKET SIGNALS OVERVIEW
# ==============================================================================
st.subheader("🌐 Regional Variance & Market Signals")

sig_col1, sig_col2, sig_col3 = st.columns(3)
buys = len(latest_df[latest_df['Market_Signal'] == 'BUY'])
holds = len(latest_df[latest_df['Market_Signal'] == 'HOLD'])
sells = len(latest_df[latest_df['Market_Signal'] == 'SELL'])

sig_col1.metric("BUY Signals", buys)
sig_col2.metric("HOLD Signals", holds)
sig_col3.metric("SELL Signals", sells)

st.divider()

# ==============================================================================
# 4. COINGECKO-STYLE TOP 50 MARKET CAP LEADERBOARD
# ==============================================================================
st.subheader("🦎 Top 50 PS2 Collectibles by Market Valuation (CoinGecko Style)")
st.caption(f"Showing active top 50 rankings as of {latest_date}")

top_50_df = latest_df.sort_values("Rank").head(50)

st.dataframe(
    top_50_df[[
        'Rank', 'Game', 'CIB_Price_USD', 'Market_Cap_USD', 
        'Price_PAL_GBP', 'Price_US_USD', 'Price_JP_USD', 
        'Hype_Index', 'Market_Signal'
    ]],
    column_config={
        "Rank": st.column_config.NumberColumn("# Rank", format="#%d", width="small"),
        "Game": st.column_config.TextColumn("Title / Game Name", width="medium"),
        "CIB_Price_USD": st.column_config.NumberColumn("CIB Price (USD)", format="$%.2f"),
        "Market_Cap_USD": st.column_config.NumberColumn("Market Cap ($)", format="$%.2f"),
        "Price_PAL_GBP": st.column_config.NumberColumn("CeX PAL (£)", format="£%.2f"),
        "Price_US_USD": st.column_config.NumberColumn("NTSC-U ($)", format="$%.2f"),
        "Price_JP_USD": st.column_config.NumberColumn("NTSC-J ($)", format="$%.2f"),
        "Hype_Index": st.column_config.ProgressColumn("Hype Score", min_value=0, max_value=100),
        "Market_Signal": st.column_config.TextColumn("Signal", width="small")
    },
    use_container_width=True,
    hide_index=True,
    height=600
)
