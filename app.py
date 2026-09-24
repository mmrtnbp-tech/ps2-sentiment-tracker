import streamlit as st
import json
import os
import pandas as pd
from scraper import run_scraper  # Imports your scraper function directly

st.set_page_config(page_title="PS2 Market Cap & Price Tracker", layout="wide")

@st.cache_data
def load_master_catalog():
    if os.path.exists("master_ps2_catalog.json"):
        with open("master_ps2_catalog.json", "r", encoding="utf-8") as f:
            return json.load(f)
    return []

st.title("🎮 PS2 Market Intelligence Dashboard")

# --- DATA GENERATION / REFRESH BUTTON (NO TERMINAL REQUIRED) ---
csv_file = "ps2_sentiment_history.csv"

with st.sidebar:
    st.header("Admin Controls")
    if st.button("🔄 Run / Refresh Market Data"):
        with st.spinner("Scraping Top 50 PS2 titles... Please wait (~15s)"):
            run_scraper()
            st.cache_data.clear()
        st.success("Data updated successfully!")
        st.rerun()

if not os.path.exists(csv_file):
    st.warning("⚠️ No price data found yet.")
    if st.button("🚀 Run Initial Scrape Now"):
        with st.spinner("Generating initial dataset..."):
            run_scraper()
            st.cache_data.clear()
        st.success("Dataset created!")
        st.rerun()
    st.stop()

# --- DASHBOARD CONTENT ---
df = pd.read_csv(csv_file)
latest_date = df['Date'].max()
latest_df = df[df['Date'] == latest_date].copy()

# Master Catalog Dropdown Search
catalog = load_master_catalog()
all_titles = [g["title"] for g in catalog] if catalog else df['Game'].unique().tolist()

selected_game = st.selectbox("Search Master PS2 Database:", all_titles)

game_history = df[df["Game"] == selected_game]

if not game_history.empty:
    latest_row = game_history.iloc[-1]
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Current Price (USD)", f"${latest_row['CIB_Price_USD']:.2f}")
    col2.metric("CeX PAL Price (£)", f"£{latest_row['Price_PAL_GBP']:.2f}")
    col3.metric("Est. Market Cap", f"${latest_row['Market_Cap_USD']:,.2f}")
    col4.metric("Market Signal", latest_row['Market_Signal'])
else:
    st.info(f"'{selected_game}' is stored in the master catalog but is not in the active Top 50 tracked list.")

# CoinGecko Style Table
st.divider()
st.subheader("🦎 Top 50 PS2 Collectibles by Market Valuation (CoinGecko Style)")
st.caption(f"Live Market Cap rankings as of {latest_date}")

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
