import os
import time
import asyncio
import feedparser
import requests
import pandas as pd
from datetime import datetime
from bs4 import BeautifulSoup
from pytrends.request import TrendReq
from howlongtobeatpy import HowLongToBeat
from mercapi import Mercapi

# ---------------------------------------------------------
# TARGET BENCHMARK PS2 GAMES
# ---------------------------------------------------------
TARGET_GAMES = [
    "Silent Hill 2",
    "Rule of Rose",
    "Kuon",
    "Def Jam Fight for NY",
    "God of War",
    "Metal Gear Solid 3",
    "Grand Theft Auto San Andreas",
    "Persona 4",
    "Shadow of the Colossus",
    "Fatal Frame II"
]

# Top Gaming Outlets RSS Feeds
RSS_FEEDS = [
    "https://www.gamesindustry.biz/feed/news",
    "https://ign.com/rss/articles/feed",
    "https://kotaku.com/rss",
    "https://www.eurogamer.net/feed/news",
    "https://www.gematsu.com/feed"
]

RA_API_KEY = os.environ.get("RA_API_KEY", "")
RA_USER = os.environ.get("RA_USER", "")

# ---------------------------------------------------------
# SCRAPING FUNCTIONS WITH SAFE FALLBACKS
# ---------------------------------------------------------

def get_google_trends(game_list):
    """Fetches 7-day search interest using pytrends."""
    print("📈 Fetching Google Trends...")
    trends_data = {}
    pytrend = TrendReq(hl='en-US', tz=360)
    
    for game in game_list:
        try:
            pytrend.build_payload(kw_list=[f"{game} PS2"], timeframe='now 7-d')
            df = pytrend.interest_over_time()
            if not df.empty and f"{game} PS2" in df.columns:
                trends_data[game] = round(float(df[f"{game} PS2"].mean()), 2)
            else:
                trends_data[game] = 0.0
            time.sleep(1) # Rate limit protection
        except Exception as e:
            print(f"⚠️ Google Trends error for {game}: {e}")
            trends_data[game] = 0.0
            
    return trends_data

def get_news_mentions(game_list):
    """Counts mentions across major gaming RSS feeds."""
    print("📰 Scraping RSS Gaming News...")
    mentions = {game: 0 for game in game_list}
    
    for url in RSS_FEEDS:
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries:
                text = (entry.get('title', '') + " " + entry.get('summary', '')).lower()
                for game in game_list:
                    if game.lower() in text:
                        mentions[game] += 1
        except Exception as e:
            print(f"⚠️ RSS error for {url}: {e}")
            
    return mentions

import re
import urllib.parse
import requests
from bs4 import BeautifulSoup

# Strictly filter for Complete-In-Box items
CIB_POSITIVE_KEYWORDS = ["cib", "complete", "with manual", "box and manual", "black label", "完品", "帯付き"]
CIB_NEGATIVE_KEYWORDS = ["disc only", "case only", "manual only", "loose", "repro", "digital code", "junk", "ジャンク"]

def get_live_exchange_rates():
    """Fetches real-time currency conversion rates relative to USD."""
    try:
        res = requests.get("https://open.er-api.com/v6/latest/USD", timeout=5)
        if res.status_code == 200:
            return res.json().get('rates', {'USD': 1.0, 'GBP': 0.78, 'EUR': 0.92, 'JPY': 155.0})
    except Exception as e:
        print(f"⚠️ FX API error: {e}. Using estimated conversion rates.")
    return {'USD': 1.0, 'GBP': 0.78, 'EUR': 0.92, 'JPY': 155.0}

def is_cib_listing(title):
    """Verifies title contains CIB indicators and excludes loose/partial items."""
    title_lower = title.lower()
    if any(neg in title_lower for neg in CIB_NEGATIVE_KEYWORDS):
        return False
    return True

def parse_price_and_convert(price_text, rates):
    """Extracts numerical value and currency symbol, converting to USD."""
    try:
        # Clean price string
        clean_text = price_text.replace(',', '').strip()
        
        # Identify currency
        currency = 'USD'
        if '£' in clean_text or 'GBP' in clean_text:
            currency = 'GBP'
        elif '€' in clean_text or 'EUR' in clean_text:
            currency = 'EUR'
        elif '¥' in clean_text or 'JPY' in clean_text:
            currency = 'JPY'
        elif 'AU$' in clean_text or 'C$' in clean_text:
            currency = 'USD' # Standardize CAD/AUD approx or extend as needed
            
        # Extract float value
        match = re.search(r'([0-9]+\.?[0-9]*)', clean_text)
        if match:
            raw_val = float(match.group(1))
            rate = rates.get(currency, 1.0)
            usd_value = raw_val / rate if currency != 'USD' and rate > 0 else raw_val
            return round(usd_value, 2)
    except Exception:
        pass
    return None

def scrape_ebay_sold_by_region(game_name, region_tag, rates):
    """Scrapes the top 3 most recently sold listings for a specific regional variant on eBay."""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
        'Accept-Language': 'en-US,en;q=0.9'
    }
    
    # Regional search queries
    region_queries = {
        "US": f"{game_name} PS2 CIB complete NTSC-U",
        "PAL": f"{game_name} PS2 CIB complete PAL",
        "JP": f"{game_name} PS2 CIB 完品 NTSC-J Japan"
    }
    
    query = urllib.parse.quote(region_queries.get(region_tag, f"{game_name} PS2 CIB"))
    # _sop=13 sorts specifically by "Ended Recently" (most recent sales first)
    ebay_url = f"https://www.ebay.com/sch/i.html?_nkw={query}&LH_Sold=1&LH_Complete=1&_sop=13"
    
    prices_usd = []
    
    try:
        res = requests.get(ebay_url, headers=headers, timeout=10)
        if res.status_code == 200:
            soup = BeautifulSoup(res.text, 'html.parser')
            items = soup.find_all('div', class_='s-item__info')
            
            for item in items:
                title_elem = item.find('div', class_='s-item__title')
                price_elem = item.find('span', class_='s-item__price')
                
                if title_elem and price_elem:
                    title_text = title_elem.text.strip()
                    price_text = price_elem.text.strip()
                    
                    if is_cib_listing(title_text):
                        usd_price = parse_price_and_convert(price_text, rates)
                        if usd_price and usd_price > 0:
                            prices_usd.append(usd_price)
                            
                # STRICT LIMIT: Stop as soon as we gather the 3 most recently sold valid listings
                if len(prices_usd) >= 3:
                    break
                    
        if prices_usd:
            avg_price = round(sum(prices_usd) / len(prices_usd), 2)
            print(f"  ✅ [{region_tag}] '{game_name}' Recent 3-Sale Avg: ${avg_price} USD (Sample: {prices_usd})")
            return avg_price
    except Exception as e:
        print(f"  ⚠️ eBay [{region_tag}] error for '{game_name}': {e}")
        
    return None  # No baseline! Returns None if no recent sales exist.

def get_multi_region_prices(game_list):
    """Pulls live regional market prices across US, PAL, and JP regions."""
    print("🏷️ Fetching Live Multi-Region Prices from eBay Sold Listings...")
    rates = get_live_exchange_rates()
    regional_data = {}
    
    for game in game_list:
        print(f"\n🎮 Tracking live sales for: {game}")
        us_price = scrape_ebay_sold_by_region(game, "US", rates)
        pal_price = scrape_ebay_sold_by_region(game, "PAL", rates)
        jp_price = scrape_ebay_sold_by_region(game, "JP", rates)
        
        regional_data[game] = {
            "Price_US_USD": us_price,
            "Price_PAL_USD": pal_price,
            "Price_JP_USD": jp_price
        }
        
    return regional_data

def get_retroachievements_data(game_list):
    """Pulls achievement activity count from RetroAchievements if credentials exist."""
    print("🏆 Fetching RetroAchievements stats...")
    ra_scores = {game: 0 for game in game_list}
    if not RA_API_KEY or not RA_USER:
        print("ℹ️ Skipping RetroAchievements (API Key / User not provided).")
        return ra_scores
    
    # Example RA Game ID Mapping (In production, dynamic lookup can be added)
    ra_ids = {"Silent Hill 2": 2182, "God of War": 2240, "Persona 4": 3042}
    
    for game, game_id in ra_ids.items():
        if game in game_list:
            url = f"https://retroachievements.org/API/API_GetGameExtended.php?i={game_id}&y={RA_API_KEY}&u={RA_USER}"
            try:
                res = requests.get(url, timeout=10).json()
                ra_scores[game] = int(res.get('NumEarned', 0))
            except Exception as e:
                print(f"⚠️ RetroAchievements error for {game}: {e}")
                
    return ra_scores

async def get_mercari_listings(game_list):
    """Searches active listings on Mercari Japan."""
    print("🛍️ Fetching Mercari Japan listings...")
    mercari_counts = {}
    m = Mercapi()
    
    for game in game_list:
        try:
            results = await m.search(f"{game} PS2")
            mercari_counts[game] = results.meta.num_found if results.meta else 0
        except Exception as e:
            print(f"⚠️ Mercari error for {game}: {e}")
            mercari_counts[game] = 0
            
    return mercari_counts

def get_hltb_hours(game_list):
    """Pulls average completion time from HowLongToBeat."""
    print("⏱️ Scraping HowLongToBeat...")
    hltb_data = {}
    hltb = HowLongToBeat()
    
    for game in game_list:
        try:
            results = hltb.search(game)
            if results and len(results) > 0:
                hltb_data[game] = float(results[0].gameplay_main)
            else:
                hltb_data[game] = 0.0
        except Exception as e:
            print(f"⚠️ HLTB error for {game}: {e}")
            hltb_data[game] = 0.0
            
    return hltb_data

# ---------------------------------------------------------
# COMPOSITE SCORE CALCULATOR & MAIN PIPELINE
# ---------------------------------------------------------

async def run_scraper():
    trends = get_google_trends(TARGET_GAMES)
    news = get_news_mentions(TARGET_GAMES)
    ra_data = get_retroachievements_data(TARGET_GAMES)
    mercari = await get_mercari_listings(TARGET_GAMES)
    hltb = get_hltb_hours(TARGET_GAMES)
    
    # Multi-Region Scraper (US, PAL, JP)
    region_prices = get_multi_region_prices(TARGET_GAMES)
    
    today_str = datetime.now().strftime("%Y-%m-%d")
    new_rows = []
    
    for game in TARGET_GAMES:
        t_val = trends.get(game, 0)
        n_val = news.get(game, 0)
        ra_val = ra_data.get(game, 0)
        
        # Primary reference price uses US price if available, else PAL, else JP, else None
        p_dict = region_prices.get(game, {})
        us_p = p_dict.get("Price_US_USD")
        pal_p = p_dict.get("Price_PAL_USD")
        jp_p = p_dict.get("Price_JP_USD")
        
        primary_price = us_p if us_p is not None else (pal_p if pal_p is not None else jp_p)
        
        hype_index = round(min(100.0, (t_val * 0.5) + (n_val * 15.0) + (ra_val * 0.01)), 2)
        
        new_rows.append({
            "Date": today_str,
            "Game": game,
            "CIB_Price_USD": primary_price,  # Primary benchmark for scatter chart
            "Price_US_USD": us_p,
            "Price_PAL_USD": pal_p,
            "Price_JP_USD": jp_p,
            "Hype_Index": hype_index,
            "Google_Trend_Score": t_val,
            "News_Mentions": n_val,
            "Mercari_Listings": mercari.get(game, 0),
            "RA_Active_Achievements": ra_val,
            "HLTB_Main_Hours": hltb.get(game, 0.0)
        })
        
    new_df = pd.DataFrame(new_rows)
    
    csv_filename = "ps2_sentiment_history.csv"
    if os.path.exists(csv_filename):
        existing_df = pd.read_csv(csv_filename)
        existing_df = existing_df[existing_df['Date'] != today_str]
        combined_df = pd.concat([existing_df, new_df], ignore_index=True)
    else:
        combined_df = new_df
        
    combined_df.to_csv(csv_filename, index=False)
    print(f"✅ Live regional price scraping completed. Updated {csv_filename}")
