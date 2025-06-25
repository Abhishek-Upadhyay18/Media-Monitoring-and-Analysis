#%%
import pandas as pd
import json
from bs4 import BeautifulSoup
import requests
import time
import re
import os

def clean_text(text):
    if not text:
        return ""
    # Remove extra whitespace
    text = re.sub(r'\s+', ' ', text.strip())
    # Remove special characters that might cause issues
    text = text.replace('\n', ' ').replace('\r', ' ').replace('\t', ' ')
    return text

def extract_article_content(soup):
    # First try to get the main article content
    article_tag = soup.find('article')
    if article_tag:
        # Remove unwanted elements
        for unwanted in article_tag.find_all(['script', 'style', 'noscript', 'div']):
            if unwanted.get('class') and any(c in ['flt', 'ads', 'footer', 'disclaimer', 'prime', 'paywall'] for c in unwanted.get('class')):
                unwanted.decompose()
        
        # Get the main content
        content = article_tag.get_text(separator=' ', strip=True)
        
        # Remove common boilerplate text
        boilerplate = [
            "Catch all the US News",
            "Download The Economic Times News App",
            "You can now subscribe to our Economic Times WhatsApp channel",
            "Disclaimer Statement:",
            "Read More News on",
            "Prime Exclusives",
            "Investment Ideas",
            "View all Stories",
            "(You can now subscribe to our",
            "Read More News on"
        ]
        
        for text in boilerplate:
            if text in content:
                content = content.split(text)[0]
        
        content = clean_text(content)
        if len(content) > 200:  # Only return if we have substantial content
            return content

    return None

def recheck_paywall_articles():
    # Headers to mimic browser request
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }

    # Load the paywall URLs
    try:
        with open('articles/paywall_urls_24_03_2025.json', 'r') as f:
            paywall_urls = json.load(f)
    except FileNotFoundError:
        print("Paywall URLs file not found!")
        return
    
    successfully_extracted = []
    still_paywall = []
    failed_urls = []

    print(f"\nRechecking {len(paywall_urls)} articles previously marked as paywall protected...")

    for idx, article in enumerate(paywall_urls, 1):
        url = article['url']
        try:
            print(f"\nProcessing URL {idx}/{len(paywall_urls)}: {url}")
            
            response = requests.get(url, headers=headers, timeout=15)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            content = extract_article_content(soup)
            
            if content:
                print(f"Successfully extracted article ({len(content)} chars)")
                article['full_content'] = content
                successfully_extracted.append(article)
            else:
                print("Still appears to be behind paywall or no content found")
                still_paywall.append(article)
            
            time.sleep(2)  # Be nice to the server
            
        except Exception as e:
            print(f"Error processing URL: {str(e)}")
            article['error'] = str(e)
            failed_urls.append(article)

    # Save results
    if successfully_extracted:
        print(f"\nSuccessfully extracted {len(successfully_extracted)} articles!")
        
        # Convert to DataFrame and save
        df = pd.DataFrame(successfully_extracted)
        output_file = 'articles/recovered_paywall_articles_24_03_2025.csv'
        df.to_csv(output_file, index=False)
        print(f"Saved recovered articles to: {output_file}")

    if still_paywall:
        output_file = 'articles/still_paywall_24_03_2025.json'
        with open(output_file, 'w') as f:
            json.dump(still_paywall, f, indent=2)
        print(f"\n{len(still_paywall)} articles still appear to be behind paywall")
        print(f"Saved to: {output_file}")

    if failed_urls:
        output_file = 'articles/paywall_check_failed_24_03_2025.json'
        with open(output_file, 'w') as f:
            json.dump(failed_urls, f, indent=2)
        print(f"\nFailed to process {len(failed_urls)} URLs")
        print(f"Saved to: {output_file}")

if __name__ == "__main__":
    recheck_paywall_articles() 