#!/usr/bin/env python3
"""
Script to fetch news article URLs from LiveMint insurance section and save them to a CSV file.
"""
from bs4 import BeautifulSoup
import requests
import pandas as pd
import re
from datetime import datetime


def extract_article_data(div):
    """Extract article data from a headline section div."""
    links = div.find('a')
    if not links:
        return None
    
    onclick_value = links.get('onclick')
    if not onclick_value:
        return None
    
    match = re.search(r"target_url:\s*'(.*?)'", onclick_value)
    if not match:
        return None
    
    target_url = match.group(1)
    text = links.text
    span_time = div.find('span')
    timestamp = span_time.text if span_time else ""
    
    return {
        "timestamp": timestamp.replace('\n', ''),
        "headline": text.replace('\n', ''),
        "target_url": target_url
    }


def fetch_all_urls(urls):
    """Fetch article data from a list of URLs."""
    news_data = []
    
    for url in urls:
        print(f"Fetching data from: {url}")
        try:
            response = requests.get(url)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            target_divs = soup.find_all('div', attrs={'class': 'headlineSec'})
            
            for div in target_divs:
                article_data = extract_article_data(div)
                if article_data:
                    news_data.append(article_data)
                    
        except requests.RequestException as e:
            print(f"Error fetching {url}: {e}")
    
    return pd.DataFrame(news_data)


def save_to_csv(df, prefix="Mint_news_urls"):
    """Save DataFrame to CSV with current date in filename."""
    current_date = datetime.now().strftime("%d_%m_%Y")
    folder_name = "articles"
    filename = f'{folder_name}/{prefix}_{current_date}.csv'
    df.to_csv(filename, index=False)
    print(f"Data saved to {filename}")
    return filename


def main():
    """Main function to execute the script."""
    urls = [
        "https://www.livemint.com/insurance/news",
        "https://www.livemint.com/insurance/page-2",
        "https://www.livemint.com/insurance/page-3",
        "https://www.livemint.com/insurance/page-4",
        "https://www.livemint.com/insurance/page-5"
    ]
    
    news_urls_df = fetch_all_urls(urls)
    print(f"Total articles found: {len(news_urls_df)}")
    
    if not news_urls_df.empty:
        save_to_csv(news_urls_df)
    else:
        print("No articles found.")


if __name__ == "__main__":
    main()
