#%%
# Saving articles from Mint website date 21_03_2025 

from bs4 import BeautifulSoup
import requests
import pandas as pd
import re
import time
from datetime import datetime
#%%
df = pd.read_csv('articles/Mint_news_urls_21_03_2025.csv')
df_sub = df[df['headline'] != 'MintGenie']
collated_data  = []  # This will now store dictionaries instead of DataFrames
key_words = ['metlife', 'group life insurance', 'health insurance', 'healthcare', 'life insurance', 'health',  'insurance policy', 'insurance plan', 'insurance coverage', 'insurance claim', 'insurance claim process', 'insurance claim settlement', 'insurance claim approval', 'insurance claim rejection', 'insurance claim settlement', 'insurance claim approval', 'insurance claim rejection']

# Add headers to mimic a browser request
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

#%%
for idx, row in enumerate(df_sub['target_url']):
    try:
        url = row
        published_date = df_sub.iloc[idx]['timestamp']  # Get the timestamp for this URL
        print(f"Processing URL {idx + 1}/{len(df_sub)}: {url}")
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()  # This will raise an exception for bad status codes
        
        soup = BeautifulSoup(response.content, 'html.parser')
        article_div = soup.find('div', attrs={'class':'storyPage_storyBox__zPlkE'})

        if article_div is not None:
            # Extract h1, h2, and content
            h1 = article_div.find('h1').text.strip() if article_div.find('h1') else ''
            h2_tags = article_div.find_all('h2')
            h2_texts = [h2.text.strip() for h2 in h2_tags]
            h2_combined = ' | '.join(h2_texts)

            # Get all paragraphs for content
            paragraphs = article_div.find_all('p')
            content = ' '.join([p.text.strip() for p in paragraphs])

            # Convert content to lowercase for keyword checking
            content_lower = content.lower()
            
            # Check if any key word is in the content
            if any(keyword in content_lower for keyword in key_words):
                # Store as dictionary instead of DataFrame
                article_data = {
                    'url': url,
                    'published_date': published_date,
                    'headline': h1,
                    'h2': h2_combined,
                    'full_content': content
                }
                collated_data.append(article_data)
                print(f"Successfully extracted article with title: {h1[:100]}...")
        else:
            print(f"No article div found for URL: {url}")
            
        # Add a small delay between requests to avoid overwhelming the server
        time.sleep(2)
            
    except requests.exceptions.RequestException as e:
        print(f"Request error for URL {url}: {str(e)}")
        continue
    except Exception as e:
        print(f"Unexpected error processing URL {url}: {str(e)}")
        continue

#%%
if collated_data:  # Check if we have any data before creating DataFrame
    # Create DataFrame from list of dictionaries
    final_df = pd.DataFrame(collated_data)
    final_df.to_csv(f'articles/Mint_article_content_with_keywords_{datetime.now().strftime("%d_%m_%Y")}.csv', index=False)
    print(f"Saved {len(final_df)} articles to CSV")
else:
    print("No articles with keywords found")


# %%

