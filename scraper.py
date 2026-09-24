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

def get_pricecharting_data(game_list):
    """Scrapes CIB (Complete In Box) prices from PriceCharting."""
    print("🏷️ Scraping PriceCharting...")
    prices = {}
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    
    for game in game_list:
        slug = game.lower().replace(" ", "-").replace(":", "").replace("'", "")
        url = f"https://www.pricecharting.com/game/playstation-2/{slug}"
        try:
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                cib_elem = soup.find('td', id='used_price')
                if cib_elem:
                    price_text = cib_elem.text.strip().replace('$', '').replace(',', '')
                    prices[game] = float(price_text)
                else:
                    prices[game] = 0.0
            else:
                prices[game] = 0.0
            time.sleep(1.5)
        except Exception as e:
            print(f"⚠️ PriceCharting error for {game}: {e}")
            prices[game] = 0.0
            
    return prices

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
    prices = get_pricecharting_data(TARGET_GAMES)
    ra_data = get_retroachievements_data(TARGET_GAMES)
    mercari = await get_mercari_listings(TARGET_GAMES)
    hltb = get_hltb_hours(TARGET_GAMES)
    
    today_str = datetime.now().strftime("%Y-%m-%d")
    new_rows = []
    
    for game in TARGET_GAMES:
        t_val = trends.get(game, 0)
        n_val = news.get(game, 0)
        ra_val = ra_data.get(game, 0)
        
        # Calculate composite Hype Index (0 to 100 relative scale)
        hype_index = round(min(100.0, (t_val * 0.5) + (n_val * 15.0) + (ra_val * 0.01)), 2)
        
        new_rows.append({
            "Date": today_str,
            "Game": game,
            "CIB_Price_USD": prices.get(game, 0.0),
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
        # Avoid duplicating entries for today
        existing_df = existing_df[existing_df['Date'] != today_str]
        combined_df = pd.concat([existing_df, new_df], ignore_index=True)
    else:
        combined_df = new_df
        
    combined_df.to_csv(csv_filename, index=False)
    print(f"✅ Scraping completed. Saved {len(new_rows)} entries to {csv_filename}")

if __name__ == "__main__":
    asyncio.run(run_scraper())
