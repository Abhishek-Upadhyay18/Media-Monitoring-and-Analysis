#%%
import pandas as pd
import os
import requests
from bs4 import BeautifulSoup
import time
import json
from datetime import datetime
import re

# Create articles directory if it doesn't exist
os.makedirs('articles', exist_ok=True)

# Load the URLs from the CSV file
df = pd.read_csv('articles/news_urls_hindu.csv')

# Display the first few rows of the dataframe
print(df.head())

# Function to extract article content
def extract_article_content(url):
    try:
        # Add headers to mimic a browser request
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        # Send a GET request to the URL
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()  # Raise an exception for HTTP errors
        
        # Parse the HTML content
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Extract the headline (multiple possible selectors based on site structure)
        headline = None
        headline_selectors = [
            'h1.title', '.article-title', '.story-headline h1', '.title-holder h1'
        ]
        
        for selector in headline_selectors:
            headline_element = soup.select_one(selector)
            if headline_element:
                headline = headline_element.get_text().strip()
                break
        
        # IMPROVED CONTENT EXTRACTION
        content = ""
        
        # First try to find the main article body with articlebodycontent class
        article_body = soup.find('div', class_='articlebodycontent')
        
        # If not found, try finding div with id containing 'content-body-'
        if not article_body:
            article_body = soup.find('div', id=lambda x: x and 'content-body-' in x)
        
        # If still not found, try other common selectors
        if not article_body:
            for selector in ['.article-content', '#article-content', '.story-content', '.story-details', '.content-area']:
                article_body = soup.select_one(selector)
                if article_body:
                    break
        
        # Extract all paragraphs from the article body, including those separated by ads
        if article_body:
            # Get all <p> tags, even if they're not direct children
            paragraphs = article_body.find_all('p')
            if paragraphs:
                # Join all paragraph texts
                content = "\n\n".join([p.get_text().strip() for p in paragraphs])
        
        # If content is still empty, try a simple approach with content-body
        if not content:
            article_body = soup.select_one('#content-body')
            if article_body:
                paragraphs = article_body.find_all('p')
                content = "\n\n".join([p.get_text().strip() for p in paragraphs])
        
        # Verify if we have meaningful content (more than just a few characters)
        if content and len(content.strip()) < 50:
            print(f"Warning: Very short content detected ({len(content.strip())} chars) for {url}")
        
        success = bool(headline and content and len(content.strip()) > 0)
            
        return {
            'headline': headline,
            'content': content,
            'success': success
        }
        
    except Exception as e:
        print(f"Error extracting content from {url}: {str(e)}")
        return {
            'headline': None,
            'content': None,
            'success': False,
            'error': str(e)
        }

# List to store URLs that failed
failed_urls = []

# Create a list to store the successful article data
articles_data = []

# Process each URL in the CSV
for index, row in df.iterrows():
    url = row['url']
    print(f"Processing URL {index+1}/{len(df)}: {url}")
    
    # Extract article content
    result = extract_article_content(url)
    
    if result['success']:
        # Prepare data for saving
        article_data = {
            'headline': result['headline'] if result['headline'] else row['headline'],
            'content': result['content'],
            'published_date': row['published_date'],
            'year': row['year'],
            'month': row['month']
        }
        
        # Add to our articles data list
        articles_data.append(article_data)
        
        print(f"Successfully extracted article: {article_data['headline']}")
    else:
        failed_urls.append({
            'url': url,
            'headline': row['headline'],
            'error': result.get('error', 'Unknown error')
        })
        print(f"Failed to extract content from URL: {url}")
    
    # Add delay to avoid overwhelming the server
    time.sleep(2)

# Create DataFrame from the articles data
articles_df = pd.DataFrame(articles_data)

# Save to CSV
csv_path = 'articles/hindu_articles.csv'
articles_df.to_csv(csv_path, index=False)

# Print summary
print(f"\n\nCompleted scraping {len(articles_data)}/{len(df)} articles successfully.")
print(f"Articles saved to {csv_path}")

if failed_urls:
    print(f"Failed to scrape {len(failed_urls)} articles:")
    for failed_url in failed_urls:
        print(f"  - {failed_url['headline']}: {failed_url['url']} (Error: {failed_url['error']})")
    
    # Save failed URLs to a file
    with open('articles/failed_urls.json', 'w') as f:
        json.dump(failed_urls, f, indent=4)
else:
    print("All articles were scraped successfully!")




# %%
