import requests
from bs4 import BeautifulSoup
import json
import pandas as pd
import time

url = 'https://store.steampowered.com/search/results/?query&start=0&count=50&dynamic_data=&sort_by=_ASC&snr=1_7_7_7000_7&filter=topsellers&tags=19&infinite=1'

def totalresults(url):
    r = requests.get(url)
    data = dict(r.json())
    totalresults = data['total_count']
    return int(totalresults)

def get_data(url):
    r = requests.get(url)
    data = dict(r.json())
    return data['results_html']

def parse(data):
    gameslist = []
    soup = BeautifulSoup(data, 'html.parser')
    games = soup.find_all('a')
    
    for game in games:
        title = game.find('span', {'class': 'title'}).text

        # Look for the price container
        price_div = game.find('div', {'class': 'search_price_discount_combined'})
        if price_div:
            # Check if there's a "data-price-final" attribute (raw price in cents)
            price_raw = price_div.get('data-price-final')

            # Look for final price text
            final_price_div = price_div.find('div', {'class': 'discount_final_price'})
            if final_price_div:
                price = final_price_div.text.strip()
            elif price_raw:  # If no visible price, fallback to data-price-final
                price = f"${int(price_raw) / 100:.2f}"
            else:
                price = 'N/A'

            # Handle discount cases
            discount_price_div = price_div.find('div', {'class': 'discount_original_price'})
            if discount_price_div:
                discprice = discount_price_div.text.strip()
            else:
                discprice = price  # No discount, set discount price as the normal price

            # Handle discount percentage
            discount_pct_div = price_div.find('div', {'class': 'discount_pct'})
            discount_pct = discount_pct_div.text.strip() if discount_pct_div else '0%'

            # Handle "Free" games
            if price.lower() == 'free':
                price = 'Free'
                discprice = 'Free'
                discount_pct = '0%'  # No discount for free games
        else:
            price = 'N/A'
            discprice = 'N/A'
            discount_pct = 'N/A'

        # Extract review summary from "data-tooltip-html"
        review_div = game.find('span', {'class': 'search_review_summary'})
        if review_div and review_div.has_attr('data-tooltip-html'):
            review_summary = review_div['data-tooltip-html'].replace("<br>", " ")  # Remove HTML line breaks
        else:
            review_summary = 'No reviews'

        # Save game details
        mygame = {
            'title': title,
            'price': price,
            'no_disc_price': discprice,
            'discount_pct': discount_pct,
            'review_summary': review_summary
        }
        gameslist.append(mygame)
    
    return gameslist

def output(results):
    gamesdf = pd.concat([pd.DataFrame(g) for g in results])
    gamesdf.to_csv('gamesprices.csv', index=False)
    print('Fin. Saved to CSV')
    print(gamesdf.head())
    return

results = []
for x in range(0, totalresults, 50):
    data = get_data(f'https://store.steampowered.com/search/results/?query&start={x}&count=50&dynamic_data=&sort_by=_ASC&snr=1_7_7_7000_7&filter=topsellers&tags=19&infinite=1')
    results.append(parse(data))
    print('Results Scraped: ', x)
    time.sleep(1.5)

output(results)




