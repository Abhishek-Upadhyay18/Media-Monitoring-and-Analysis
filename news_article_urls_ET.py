#%%
url = "https://economictimes.indiatimes.com/topic/metlife"
# %%
import re
import requests
import pandas as pd
from bs4 import BeautifulSoup
from datetime import datetime
import time
import json

# %%
def fetchAllURLs(urls):
    # Headers to mimic a browser request
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Connection': 'keep-alive',
    }

    news_data = []
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')

        # Find all news article containers
        target_divs = soup.find_all('div', attrs={'class':'clr flt topicstry story_list'})
        
        for div in target_divs:
            try:
                article_data = {}
                
                # Get the link and headline
                link_elem = div.find('a')
                if link_elem:
                    # Get headline
                    article_data['headline'] = link_elem.text.strip()
                    
                    # Extract URL from data attributes or onclick
                    article_url = None
                    # Try getting URL from data-url attribute
                    if 'data-url' in link_elem.attrs:
                        article_url = link_elem['data-url']
                    # Try getting URL from href attribute
                    elif 'href' in link_elem.attrs:
                        article_url = link_elem['href']
                    # Try getting URL from onclick attribute as fallback
                    else:
                        onclick_value = link_elem.get('onclick', '')
                        url_match = re.search(r"target_url:\s*'(.*?)'", onclick_value)
                        if url_match:
                            article_url = url_match.group(1)
                    
                    if article_url:
                        # Add base URL if it's a relative URL
                        if article_url.startswith('/'):
                            article_url = 'https://economictimes.indiatimes.com' + article_url
                        article_data['article_url'] = article_url
                
                # Get published date
                date_span = div.find('span', {'class': 'date-format'})
                if date_span:
                    article_data['published_date'] = date_span.text.strip()
                else:
                    # Try alternative date format
                    date_span = div.find('time')
                    if date_span:
                        article_data['published_date'] = date_span.text.strip()
                
                # Get content summary
                content_div = div.find('p')
                if content_div:
                    article_data['content'] = content_div.text.strip()
                
                # Only append if we have the minimum required fields
                required_fields = ['headline', 'published_date']
                if all(key in article_data for key in required_fields):
                    # Add placeholder for missing fields
                    if 'content' not in article_data:
                        article_data['content'] = 'Content not available'
                    if 'article_url' not in article_data:
                        article_data['article_url'] = 'URL not available'
                    news_data.append(article_data)
            
            except Exception as e:
                print(f"Error processing article: {str(e)}")
                continue

    except requests.RequestException as e:
        print(f"Error fetching data: {str(e)}")
        return pd.DataFrame()

    # Create DataFrame and clean up the data
    df = pd.DataFrame(news_data)
    if not df.empty:
        # Clean up any newlines and extra whitespace
        for col in df.columns:
            if df[col].dtype == 'object':
                df[col] = df[col].str.replace('\n', ' ').str.strip()
        
        # Reorder columns for better display
        column_order = ['headline', 'content', 'published_date', 'article_url']
        df = df[column_order]
    
    return df

# Example usage
if __name__ == "__main__":
    df = fetchAllURLs(url)
    print(f"Found {len(df)} articles")
    if not df.empty:
        print("\nSample of scraped data:")
        pd.set_option('display.max_columns', None)  # Show all columns
        pd.set_option('display.width', None)        # Don't wrap wide columns
        pd.set_option('display.max_colwidth', None) # Don't truncate column content
        print(df.head())
  
# %%
df.to_csv('news_articles_ET_24_03_2025.csv', index=False)

# %%
