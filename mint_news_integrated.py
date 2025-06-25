#!/usr/bin/env python3
"""
Integrated script to fetch news article URLs from LiveMint insurance section,
extract their content, filter by keywords, and save to CSV files.
"""
from bs4 import BeautifulSoup
import requests
import pandas as pd
import re
import time
from datetime import datetime
import os


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
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    for url in urls:
        print(f"Fetching data from: {url}")
        try:
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            target_divs = soup.find_all('div', attrs={'class': 'headlineSec'})
            
            for div in target_divs:
                article_data = extract_article_data(div)
                if article_data:
                    news_data.append(article_data)
            
            # Add a small delay between requests
            time.sleep(1)
                    
        except requests.RequestException as e:
            print(f"Error fetching {url}: {e}")
    
    return pd.DataFrame(news_data)


def save_to_csv(df, prefix, folder_name="articles"):
    """Save DataFrame to CSV with current date in filename."""
    current_date = datetime.now().strftime("%d_%m_%Y")
    filename = f'{folder_name}/{prefix}_{current_date}.csv'
    df.to_csv(filename, index=False)
    print(f"Data saved to {filename}")
    return filename


def extract_year_month(df):
    """Extract year and month as separate columns from published date."""
    # Create empty columns for year and month
    df['year'] = None
    df['month'] = None
    
    # Month number to name mapping
    month_names = {
        1: "January", 2: "February", 3: "March", 4: "April", 5: "May", 6: "June",
        7: "July", 8: "August", 9: "September", 10: "October", 11: "November", 12: "December"
    }
    
    if 'published_date' in df.columns and not df.empty:
        print("Extracting year and month from published dates...")
        
        for idx, row in df.iterrows():
            date_str = row['published_date']
            if pd.notna(date_str) and date_str.strip():
                try:
                    # Common Mint date formats:
                    # "03 Jun 2023" - most common format
                    # "3 min read · 10 Apr 2023" - with 'min read' prefix
                    # "5 Dec 2023, 09:34 AM IST" - with time
                    
                    # Clean up the string
                    clean_date = date_str.strip()
                    
                    # If it contains 'min read', extract the date part
                    if 'min read' in clean_date:
                        clean_date = clean_date.split('·')[-1].strip()
                    
                    # If it contains comma (like "5 Dec 2023, 09:34 AM IST"), take just the date part
                    if ',' in clean_date:
                        clean_date = clean_date.split(',')[0].strip()
                    
                    # Try different regex patterns for date extraction
                    # Pattern for "DD MMM YYYY" (e.g., "03 Jun 2023" or "3 Jun 2023")
                    pattern1 = r'(\d{1,2})\s+([A-Za-z]{3,})\s+(\d{4})'
                    # Pattern for "MMM DD YYYY" (e.g., "Jun 03 2023" or "Jun 3 2023")
                    pattern2 = r'([A-Za-z]{3,})\s+(\d{1,2})\s+(\d{4})'
                    
                    match = re.search(pattern1, clean_date)
                    if match:
                        # Format: "DD MMM YYYY"
                        day = int(match.group(1))
                        month_str = match.group(2).lower()[:3]  # First 3 chars of month name
                        year = int(match.group(3))
                    else:
                        match = re.search(pattern2, clean_date)
                        if match:
                            # Format: "MMM DD YYYY"
                            month_str = match.group(1).lower()[:3]  # First 3 chars of month name
                            day = int(match.group(2))
                            year = int(match.group(3))
                        else:
                            # Try parsing with datetime as a last resort
                            for fmt in ['%d %b %Y', '%d %B %Y', '%b %d %Y', '%B %d %Y', '%d %b, %Y', '%d %B, %Y']:
                                try:
                                    dt_obj = datetime.strptime(clean_date, fmt)
                                    year = dt_obj.year
                                    month_str = dt_obj.strftime('%b').lower()
                                    break
                                except ValueError:
                                    continue
                            else:  # If all formats fail
                                print(f"Could not parse date: {date_str}")
                                continue
                    
                    # Map month abbreviation to month number
                    month_map = {
                        'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4, 'may': 5, 'jun': 6,
                        'jul': 7, 'aug': 8, 'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12
                    }
                    
                    # Get month number
                    month_num = month_map.get(month_str.lower())
                    
                    if month_num and 1 <= month_num <= 12 and 1900 <= year <= 2100:  # Basic validation
                        df.at[idx, 'year'] = year
                        df.at[idx, 'month'] = month_names[month_num]
                        
                except Exception as e:
                    print(f"Error processing date '{date_str}': {str(e)}")
    
    # Print summary statistics
    valid_year_count = df['year'].notna().sum()
    print(f"Successfully extracted year and month for {valid_year_count}/{len(df)} articles")
    
    return df


def extract_article_content(urls_df, key_words):
    """Extract content from article URLs and filter by keywords."""
    collated_data = []
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    df_sub = urls_df[urls_df['headline'] != 'MintGenie']
    
    for idx, row in enumerate(df_sub.itertuples()):
        try:
            url = row.target_url
            published_date = row.timestamp
            print(f"Processing URL {idx + 1}/{len(df_sub)}: {url}")
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            
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
                    # Store as dictionary
                    article_data = {
                        'url': url,
                        'published_date': published_date,
                        'headline': h1,
                        'sub_headline': h2_combined,
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
    
    return pd.DataFrame(collated_data) if collated_data else pd.DataFrame()


def main():
    """Main function to execute the script."""
    # Define insurance-related keywords
    key_words = [
        'metlife', 'group life insurance', 'health insurance', 'healthcare',
        'life insurance', 'health', 'insurance policy', 'insurance plan',
        'insurance coverage', 'insurance claim', 'insurance claim process',
        'insurance claim settlement', 'insurance claim approval',
        'insurance claim rejection'
    ]
    
    # Create articles directory if it doesn't exist
    os.makedirs("articles", exist_ok=True)
    
    # 1. Fetch article URLs
    urls = [
        "https://www.livemint.com/insurance/news",
        "https://www.livemint.com/insurance/page-2",
        "https://www.livemint.com/insurance/page-3",
        "https://www.livemint.com/insurance/page-4",
        "https://www.livemint.com/insurance/page-5",
        "https://www.livemint.com/insurance/page-6",
        "https://www.livemint.com/insurance/page-7",
        "https://www.livemint.com/insurance/page-8",
        "https://www.livemint.com/insurance/page-9",
        "https://www.livemint.com/insurance/page-10"
    ]
    
    print("Step 1: Fetching article URLs...")
    news_urls_df = fetch_all_urls(urls)
    print(f"Total articles found: {len(news_urls_df)}")
    
    if not news_urls_df.empty:
        urls_file = save_to_csv(news_urls_df, "Mint_news_urls")
        
        # 2. Extract and filter article content
        print("\nStep 2: Extracting article content...")
        articles_df = extract_article_content(news_urls_df, key_words)
        
        if not articles_df.empty:
            # 3. Extract year and month from published dates
            print("\nStep 3: Extracting year and month from published dates...")
            articles_df = extract_year_month(articles_df)
            
            # 4. Save the processed articles
            save_to_csv(articles_df, "Mint_full_articles")
            print(f"\nProcess complete. Found and saved {len(articles_df)} articles.")
        else:
            print("\nNo articles found.")
    else:
        print("No article URLs found.")


if __name__ == "__main__":
    main() 