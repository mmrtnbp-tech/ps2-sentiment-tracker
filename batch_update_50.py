import json
import time
import pandas as pd
from datetime import datetime
from cexdb_scraper import get_cexdb_price

def run_50_game_batch():
    # Load entire catalog database from local JSON
    with open("master_ps2_catalog.json", "r", encoding="utf-8") as f:
        catalog = json.load(f)
        
    # Restrict batch query execution to 50 games
    batch_50 = catalog[:50]
    
    results = []
    print(f"Starting CeXDB update cycle for {len(batch_50)} games...\n")
    
    for idx, item in enumerate(batch_50, 1):
        title = item["title"]
        print(f"[{idx}/50] Querying CeXDB for: {title}")
        
        price_data = get_cexdb_price(title)
        
        results.append({
            "Timestamp": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
            "Game_ID": item["id"],
            "Title": title,
            "Genre": item["genre"],
            "CeXDB_Sell_Price": price_data["sell_price"] if price_data else None,
            "CeXDB_Cash_Price": price_data["cash_price"] if price_data else None,
            "CeXDB_Voucher_Price": price_data["voucher_price"] if price_data else None,
        })
        
        time.sleep(1)  # Respectful scraping delay
        
    # Append or create historical tracking CSV
    df = pd.DataFrame(results)
    file_exists = pd.io.common.file_exists("ps2_sentiment_history.csv")
    df.to_csv("ps2_sentiment_history.csv", mode='a', header=not file_exists, index=False)
    print("\nBatch update complete. Saved to ps2_sentiment_history.csv")

if __name__ == "__main__":
    run_50_game_batch()
