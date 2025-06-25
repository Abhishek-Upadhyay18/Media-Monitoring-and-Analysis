#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Hindu News Article Scraper
This script scrapes article URLs from The Hindu's search results,
extracts metadata, and saves the data to a CSV file.
"""

import os
import re
import time
import traceback
import pandas as pd
from datetime import datetime
from selenium import webdriver
from bs4 import BeautifulSoup
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.firefox.service import Service as FirefoxService
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.firefox import GeckoDriverManager


def setup_webdriver():
    """Initialize and set up a headless web browser instance."""
    driver = None
    try:
        # Try Chrome first
        print("Setting up Chrome driver...")
        chrome_options = ChromeOptions()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")
        
        service = ChromeService(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        print("Chrome driver setup successful")
    except Exception as e:
        print(f"Chrome setup failed: {str(e)}")
        try:
            # Try Firefox as fallback
            print("Setting up Firefox driver...")
            firefox_options = FirefoxOptions()
            firefox_options.add_argument("--headless")
            
            service = FirefoxService(GeckoDriverManager().install())
            driver = webdriver.Firefox(service=service, options=firefox_options)
            print("Firefox driver setup successful")
        except Exception as e2:
            print(f"Firefox setup failed: {str(e2)}")
            raise Exception("Failed to initialize any webdriver")

    # Test the driver
    try:
        print("Testing driver with a simple page...")
        driver.get("https://www.google.com")
        print(f"Page title: {driver.title}")
        print("Driver test successful")
    except Exception as e:
        print(f"Driver test failed: {str(e)}")
    
    return driver


def extract_date(date_text):
    """Extract a standardized date from various text formats."""
    if not date_text:
        return None
        
    # Clean up quotes if present
    if date_text.startswith('"') or date_text.endswith('"'):
        date_text = date_text.strip('"')
    
    # Try several date extraction patterns
    patterns = [
        r'(\d{1,2})\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)[a-z]*\s+(\d{4})',  # DD Month YYYY
        r'(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)[a-z]*\s+\d{1,2}(?:,)?\s+\d{4}',  # Month DD, YYYY
        r'"(\d{1,2}\s+\w+\s+\d{4})"',  # Quoted dates
        r'(\d{1,2}\s+\w+\s+\d{4})'  # Simple pattern
    ]
    
    for pattern in patterns:
        match = re.search(pattern, date_text, re.IGNORECASE)
        if match:
            return match.group(0).strip('"')
            
    # Special case for the format seen in screenshot
    if "Sept" in date_text:
        match = re.search(r'(\d{1,2})\s+Sept\s+(\d{4})', date_text)
        if match:
            return match.group(0)
    
    return None


def process_article(article):
    """Extract data from a single article element."""
    article_data = {
        'headline': None,
        'url': None,
        'published_date': None
    }
    
    try:
        # Extract title and URL
        try:
            title_element = article.find_element(By.CSS_SELECTOR, "a.gs-title")
            article_data['headline'] = title_element.text.strip()
            article_data['url'] = title_element.get_attribute("href")
        except Exception as e:
            print(f"Error extracting title: {str(e)}")
            return None
        
        # Extract published date
        try:
            # Try different CSS selectors to find the date element
            date_element = None
            selectors = [
                "div.gs-bidi-start-align.gs-snippet",
                "div.gs-bidi-start-align",
                "div.gs-snippet",
                "div[dir='ltr']"
            ]
            
            for selector in selectors:
                try:
                    elements = article.find_elements(By.CSS_SELECTOR, selector)
                    for elem in elements:
                        text = elem.text.strip()
                        # Check if text looks like a date
                        if re.search(r'\b\d{1,2}\s+\w+\s+\d{4}\b', text) or re.search(r'\b\w+\s+\d{1,2},?\s+\d{4}\b', text):
                            date_element = elem
                            date_text = text
                            break
                    if date_element:
                        break
                except Exception as e:
                    continue
                    
            if not date_element:  # Fallback - take any element with date-like text
                for elem in article.find_elements(By.XPATH, ".//*"):
                    try:
                        text = elem.text.strip()
                        if text and (re.search(r'\b\d{1,2}\s+\w+\s+\d{4}\b', text) or re.search(r'\b\w+\s+\d{1,2},?\s+\d{4}\b', text)):
                            date_element = elem
                            date_text = text
                            break
                    except:
                        continue
            
            if date_element:
                article_data['published_date'] = extract_date(date_text)
                
        except Exception as e:
            print(f"Error extracting date: {str(e)}")

        # Return article data if we at least have title and URL
        if article_data['headline'] and article_data['url']:
            return article_data
        return None
        
    except Exception as e:
        print(f"Error processing article: {str(e)}")
        return None


def scrape_search_results(urls, driver):
    """Scrape article data from search result pages."""
    all_articles = []
    
    try:
        for url in urls:
            print(f"Processing: {url}")
            driver.get(url)
            
            # Wait for search results to load
            wait = WebDriverWait(driver, 20)
            wait.until(EC.presence_of_element_located((By.CLASS_NAME, "gsc-webResult")))
            
            # Allow time for JavaScript to render content
            time.sleep(5)
            
            # Get article elements
            articles = driver.find_elements(By.CLASS_NAME, "gsc-webResult")
            print(f"Found {len(articles)} articles on this page")
            
            # If no articles found, try alternative selectors
            if len(articles) == 0:
                print("No articles found with class 'gsc-webResult', trying alternative selectors")
                for selector in [".gs-title", ".gsc-thumbnail-inside", ".gsc-url-top"]:
                    elements = driver.find_elements(By.CSS_SELECTOR, selector)
                    if elements:
                        print(f"Found {len(elements)} elements with selector '{selector}'")
            
            # Process each article
            for article in articles:
                article_data = process_article(article)
                if article_data:
                    all_articles.append(article_data)
                    print(f"Added article: {article_data['headline'][:30]}... Date: {article_data['published_date']}")
                    
            # Small delay between pages
            time.sleep(2)
            
    except Exception as e:
        print(f"Error during scraping: {str(e)}")
        traceback.print_exc()
        
    return all_articles


def extract_year_month(df):
    """Extract year and month from published dates."""
    # Month number to name mapping
    month_names = {
        1: "January", 2: "February", 3: "March", 4: "April", 5: "May", 6: "June",
        7: "July", 8: "August", 9: "September", 10: "October", 11: "November", 12: "December"
    }
    
    # Create empty columns for year and month
    df['year'] = None
    df['month'] = None
    
    # Only process if we have dates
    if 'published_date' in df.columns:
        # Extract year and month from published_date for non-null values
        for idx, row in df.iterrows():
            if pd.notna(row['published_date']):
                try:
                    date_str = row['published_date'].strip()
                    
                    # Format: "DD Month YYYY" like "26 Sept 2019"
                    day_month_year_match = re.match(r'^(\d{1,2})\s+([A-Za-z]+)\s+(\d{4})$', date_str)
                    if day_month_year_match:
                        day = int(day_month_year_match.group(1))
                        month_str = day_month_year_match.group(2).lower()
                        year = int(day_month_year_match.group(3))
                        
                        # Map month name to number
                        month_map = {
                            'jan': 1, 'january': 1,
                            'feb': 2, 'february': 2,
                            'mar': 3, 'march': 3,
                            'apr': 4, 'april': 4,
                            'may': 5,
                            'jun': 6, 'june': 6,
                            'jul': 7, 'july': 7,
                            'aug': 8, 'august': 8,
                            'sep': 9, 'sept': 9, 'september': 9,
                            'oct': 10, 'october': 10,
                            'nov': 11, 'november': 11,
                            'dec': 12, 'december': 12
                        }
                        
                        # Get month number - check for prefix match
                        month_num = None
                        for key, value in month_map.items():
                            if month_str.startswith(key):
                                month_num = value
                                break
                        
                        # Set year and month
                        if month_num:
                            df.at[idx, 'year'] = year
                            df.at[idx, 'month'] = month_names[month_num]
                        else:
                            print(f"Could not map month: {month_str}")
                    else:
                        # Try standard datetime formats
                        try:
                            # Try multiple date formats
                            for fmt in ['%b %d, %Y', '%B %d, %Y', '%d %b %Y', '%d %B %Y']:
                                try:
                                    date_obj = datetime.strptime(date_str, fmt)
                                    df.at[idx, 'year'] = date_obj.year
                                    df.at[idx, 'month'] = month_names[date_obj.month]
                                    break
                                except ValueError:
                                    continue
                        except Exception as format_err:
                            print(f"Failed to parse with standard formats: {format_err}")
                except Exception as e:
                    print(f"Error parsing date '{row['published_date']}': {str(e)}")
    else:
        print("No 'published_date' column found in DataFrame")
    
    return df


def filter_and_deduplicate(df):
    """Filter out articles with no year and remove duplicates."""
    # Filter out articles with no year
    df_with_years = df[df['year'].notna()]
    articles_removed = len(df) - len(df_with_years)
    print(f"Removed {articles_removed} articles with no published year")
    print(f"Articles with valid published years: {len(df_with_years)}")
    
    # Use the filtered dataframe for deduplication
    df = df_with_years
    
    # Remove duplicates based on URL (keeping the first occurrence)
    df_no_dupes = df.drop_duplicates(subset=['url'], keep='first')
    print(f"After removing URL duplicates: {len(df_no_dupes)} articles")
    
    # Check if there are articles with same headline but different URLs
    headline_counts = df_no_dupes['headline'].value_counts()
    duplicate_headlines = headline_counts[headline_counts > 1].index.tolist()
    if duplicate_headlines:
        print(f"Found {len(duplicate_headlines)} headlines with multiple URLs")
        
        # Further remove duplicates based on headline
        df_final = df_no_dupes.drop_duplicates(subset=['headline'], keep='first')
        print(f"After removing headline duplicates: {len(df_final)} articles")
    else:
        df_final = df_no_dupes
    
    print(f"Total distinct articles: {len(df_final)}")
    return df_final


def save_to_csv(df, output_dir='articles'):
    """Save DataFrame to CSV with dynamic date in filename."""
    # Create output directory if it doesn't exist
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        print(f"Created directory: {output_dir}")
    
    # Get current date for filename
    current_date = datetime.now().strftime('%Y%m%d')
    
    # Create filename with date
    csv_filename = f'Hindu_news_URLs_{current_date}.csv'
    csv_path = os.path.join(output_dir, csv_filename)
    
    # Save to CSV
    df.to_csv(csv_path, index=False)
    print(f"Data saved to {csv_path}")
    
    return csv_path


def main():
    """Main function to execute the scraping process."""
    # Define search URLs
    search_urls = [
        'https://www.thehindu.com/search/#gsc.tab=0&gsc.q=metlife&gsc.sort=',
        'https://www.thehindu.com/search/#gsc.tab=0&gsc.q=metlife&gsc.sort=&gsc.page=2',
        'https://www.thehindu.com/search/#gsc.tab=0&gsc.q=metlife&gsc.sort=&gsc.page=3',
        'https://www.thehindu.com/search/#gsc.tab=0&gsc.q=metlife&gsc.sort=&gsc.page=4',
        'https://www.thehindu.com/search/#gsc.tab=0&gsc.q=metlife&gsc.sort=&gsc.page=5',
        'https://www.thehindu.com/search/#gsc.tab=0&gsc.q=metlife&gsc.sort=&gsc.page=6',
        'https://www.thehindu.com/search/#gsc.tab=0&gsc.q=metlife&gsc.sort=&gsc.page=7',
        'https://www.thehindu.com/search/#gsc.tab=0&gsc.q=metlife&gsc.sort=&gsc.page=8'
    ]
    
    driver = None
    try:
        # Setup webdriver
        driver = setup_webdriver()
        
        # Scrape articles from search results
        articles = scrape_search_results(search_urls, driver)
        
        # Create DataFrame
        print(f"Total articles collected: {len(articles)}")
        df = pd.DataFrame(articles)
        
        # Display sample data
        print("\nDataFrame columns:", df.columns.tolist())
        print("\nSample data:")
        print(df.head())
        
        # Extract year and month from dates
        df = extract_year_month(df)
        
        # Filter and deduplicate
        df_final = filter_and_deduplicate(df)
        
        # Save to CSV
        csv_path = save_to_csv(df_final)
        
        print(f"Scraping complete. Data saved to {csv_path}")
        
    except Exception as e:
        print(f"Error in main function: {str(e)}")
        traceback.print_exc()
        
    finally:
        # Close the browser
        if driver:
            driver.quit()


if __name__ == "__main__":
    main()
