import requests
from bs4 import BeautifulSoup
import json
import time

def scrape_steam_games():
    """
    Scrapes Steam's top 150 sellers for the 'tags=19' category and returns the results as a JSON string.
    """
    
    def get_data(url):
        r = requests.get(url)
        data = r.json()  # Directly parse JSON response
        return data['results_html']

    def parse(data):
        gameslist = []
        soup = BeautifulSoup(data, 'html.parser')
        games = soup.find_all('a')
        
        for game in games:
            # Extract title
            title_tag = game.find('span', {'class': 'title'})
            title = title_tag.text if title_tag else 'No Title'
    
            # Look for the price container
            price_div = game.find('div', {'class': 'search_price_discount_combined'})
            if price_div:
                # Try to get the raw price in cents
                price_raw = price_div.get('data-price-final')
    
                # Extract the visible final price text
                final_price_div = price_div.find('div', {'class': 'discount_final_price'})
                if final_price_div:
                    price = final_price_div.text.strip()
                elif price_raw:
                    price = f"${int(price_raw) / 100:.2f}"
                else:
                    price = 'N/A'
    
                # Extract the original price if a discount is available
                discount_price_div = price_div.find('div', {'class': 'discount_original_price'})
                discprice = discount_price_div.text.strip() if discount_price_div else price
    
                # Extract discount percentage if available
                discount_pct_div = price_div.find('div', {'class': 'discount_pct'})
                discount_pct = discount_pct_div.text.strip() if discount_pct_div else '0%'
    
                # Handle free games explicitly
                if price.lower() == 'free':
                    price = 'Free'
                    discprice = 'Free'
                    discount_pct = '0%'
            else:
                price = 'N/A'
                discprice = 'N/A'
                discount_pct = 'N/A'
    
            # Extract review summary
            review_div = game.find('span', {'class': 'search_review_summary'})
            if review_div and review_div.has_attr('data-tooltip-html'):
                review_summary = review_div['data-tooltip-html'].replace("<br>", " ")
            else:
                review_summary = 'No reviews'
    
            # Save game details into a dictionary
            game_info = {
                'title': title,
                'price': price,
                'no_disc_price': discprice,
                'discount_pct': discount_pct,
                #'review_summary': review_summary
            }
            gameslist.append(game_info)
        
        return gameslist

    # List to hold results from all pages
    results = []
    for x in range(0, 50, 50):
        url = f'https://store.steampowered.com/search/results/?query&start={x}&count=50&dynamic_data=&sort_by=_ASC&snr=1_7_7_7000_7&filter=topsellers&tags=19&infinite=1'
        data = get_data(url)
        results.extend(parse(data))
        print(f'Results Scraped: 50')
        time.sleep(1.5)  # Pause to avoid rapid requests
    
    return results
    # Convert the results list to a JSON string and return it
    #print(json.dumps(results, indent=2))