import requests
from bs4 import BeautifulSoup
import urllib.parse
import re

def get_cexdb_price(game_title):
    """
    Scrapes live pricing data directly from CeXDB (cexdb.com).
    """
    # Append PS2 to narrow down search results specifically to PS2 titles
    query = f"{game_title} PS2"
    encoded_query = urllib.parse.quote(query)
    url = f"https://cexdb.com/search?q={encoded_query}"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Accept-Language": "en-GB,en;q=0.9"
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code != 200:
            print(f"[CeXDB Error] Status code {response.status_code} for query: {game_title}")
            return None

        soup = BeautifulSoup(response.text, "html.parser")
        
        # CeXDB displays search items in product links/cards containing '/product/'
        product_cards = soup.find_all("a", href=re.compile(r"/product/"))
        
        for card in product_cards:
            card_text = card.get_text(separator=" ", strip=True)
            
            # Match PlayStation 2 products
            if "ps2" in card_text.lower() or "playstation 2" in card_text.lower():
                # Extract monetary values (£XX.XX) using Regex
                prices = re.findall(r"£(\d+\.\d{2}|\d+)", card_text)
                
                if prices:
                    # CeXDB typical pricing structure: [Sell Price, Voucher Price, Cash Price]
                    sell_price = float(prices[0]) if len(prices) > 0 else None
                    voucher_price = float(prices[1]) if len(prices) > 1 else None
                    cash_price = float(prices[2]) if len(prices) > 2 else None
                    
                    return {
                        "title": game_title,
                        "sell_price": sell_price,
                        "cash_price": cash_price,
                        "voucher_price": voucher_price,
                        "url": f"https://cexdb.com{card['href']}"
                    }
                    
    except Exception as e:
        print(f"[CeXDB Exception] Failed to parse {game_title}: {e}")
        
    return None
