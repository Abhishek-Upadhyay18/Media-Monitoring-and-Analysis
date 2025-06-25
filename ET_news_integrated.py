#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
ET News Integrated Scraper
This script combines URL scraping and article content extraction for Economic Times news.
"""

import re
import requests
import pandas as pd
from bs4 import BeautifulSoup
from datetime import datetime
import time
import json
import os
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass

def extract_year_month(df):
    """
    Extract year and month as separate columns from published date
    
    Args:
        df (pd.DataFrame): DataFrame containing published_date column
        
    Returns:
        pd.DataFrame: DataFrame with added year and month columns
    """
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
                    # Common Economic Times date formats:
                    # "Jan 15, 2024, 08:15 AM IST"
                    # "15 Jan, 2024, 08:15 AM IST"
                    # "15 Jan 2024"
                    # "Jan 15 2024"
                    
                    # Clean up the string
                    clean_date = date_str.strip()
                    
                    # If it contains IST, remove the time part
                    if 'IST' in clean_date:
                        parts = clean_date.split(',')
                        if len(parts) >= 2:  # Keep only the date part
                            clean_date = ','.join(parts[0:2]).strip()
                    
                    # Remove any commas
                    clean_date = clean_date.replace(',', ' ')
                    
                    # Try different regex patterns for date extraction
                    # Pattern for "DD MMM YYYY" (e.g., "15 Jan 2024")
                    pattern1 = r'(\d{1,2})\s+([A-Za-z]{3,})\s+(\d{4})'
                    # Pattern for "MMM DD YYYY" (e.g., "Jan 15 2024")
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

# ===== URL Scraping Functions =====

def fetch_all_urls(url):
    """
    Scrape article URLs, headlines, and basic info from Economic Times topic page
    
    Args:
        url (str): The URL of the Economic Times topic page
        
    Returns:
        pd.DataFrame: DataFrame containing article URLs, headlines, and basic info
    """
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

def save_urls_to_csv(df, folder_name="articles"):
    """
    Save the scraped URLs to a CSV file
    
    Args:
        df (pd.DataFrame): DataFrame containing article URLs and info
        folder_name (str): Name of the folder to save the CSV file
        
    Returns:
        str: Path to the saved CSV file
    """
    # Ensure folder exists
    os.makedirs(folder_name, exist_ok=True)
    
    # Get current date for filename
    current_date = datetime.now().strftime("%d_%m_%Y")
    filename = f'{folder_name}/ET_news_urls_{current_date}.csv'
    
    # Save to CSV
    df.to_csv(filename, index=False)
    print(f"URLs saved to {filename}")
    
    return filename

# ===== Article Content Extraction Classes =====

@dataclass
class ArticleData:
    """Data class to store article information"""
    url: str
    headline: str
    published_date: str
    full_content: Optional[str] = None
    extraction_method: Optional[str] = None
    error: Optional[str] = None

class ArticleScraper:
    """Class to handle article scraping operations"""
    
    def __init__(self, input_file: str, output_dir: str = 'articles'):
        """
        Initialize the scraper with input file and output directory
        
        Args:
            input_file (str): Path to input CSV file with article URLs
            output_dir (str): Directory to store output files
        """
        self.input_file = input_file
        self.output_dir = output_dir
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        self.boilerplate_text = [
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
        
        # Ensure output directory exists
        os.makedirs(output_dir, exist_ok=True)
        
        # Initialize data containers
        self.article_data: List[ArticleData] = []
        self.failed_urls: List[ArticleData] = []
        self.paywall_urls: List[ArticleData] = []

    @staticmethod
    def clean_text(text: str) -> str:
        """Clean and normalize text content"""
        if not text:
            return ""
        text = re.sub(r'\s+', ' ', text.strip())
        text = text.replace('\n', ' ').replace('\r', ' ').replace('\t', ' ')
        return text

    def is_paywall_page(self, soup: BeautifulSoup) -> bool:
        """Check if the article page is behind a paywall"""
        # Check for explicit paywall indicators
        paywall_indicators = [
            'articleBlocker',
            'paywall_box',
            'prime_paywall',
            'subscribeBtn',
            'paywall',
            'subscription-required',
            'premium-content'
        ]
        
        # Check for paywall indicators in class names
        for indicator in paywall_indicators:
            if soup.find(class_=lambda c: c and indicator in c):
                return True
        
        # Check for paywall indicators in text
        paywall_texts = [
            "Subscribe to read",
            "Subscribe to continue reading",
            "This article is exclusively for subscribers",
            "To read the full article, subscribe",
            "Subscribe to ET Prime",
            "This article is locked"
        ]
        
        for text in paywall_texts:
            if soup.find(string=lambda s: s and text in s):
                return True
        
        # Check for paywall-related elements
        if soup.find(id=lambda i: i and 'paywall' in i.lower()):
            return True
            
        # Check for subscription buttons
        if soup.find('button', string=lambda s: s and ('subscribe' in s.lower() or 'sign in' in s.lower())):
            return True
            
        # If we've made it this far, it's likely not a paywall
        return False

    def extract_article_content(self, soup: BeautifulSoup) -> Tuple[Optional[str], Optional[str]]:
        """Extract the main article content from the HTML"""
        # Try main article tag first
        article_tag = soup.find('article')
        if article_tag:
            content = self._process_content_element(article_tag)
            if content:
                return content, "article tag"

        # Try alternative selectors
        content_selectors = [
            {'type': 'class', 'name': 'artText'},
            {'type': 'class', 'name': 'article_wrap'},
            {'type': 'class', 'name': 'article-content'},
            {'type': 'class', 'name': 'story-details'},
            {'type': 'class', 'name': 'article_content'},
            {'type': 'class', 'name': 'article-text'},
            {'type': 'class', 'name': 'story-content'},
            {'type': 'class', 'name': 'story-body'},
            {'type': 'class', 'name': 'articleBody'},
            {'type': 'class', 'name': 'article-body'}
        ]
        
        for selector in content_selectors:
            element = soup.find(class_=selector['name'])
            if element:
                content = self._process_content_element(element)
                if content:
                    return content, f"class: {selector['name']}"
        
        # Try finding by ID
        id_selectors = ['articleBody', 'article-body', 'story-content', 'story-body']
        for id_name in id_selectors:
            element = soup.find(id=id_name)
            if element:
                content = self._process_content_element(element)
                if content:
                    return content, f"id: {id_name}"
        
        # Try finding paragraphs within the main content area
        main_content = soup.find('div', class_=lambda c: c and ('article' in c or 'story' in c or 'content' in c))
        if main_content:
            paragraphs = main_content.find_all('p')
            if paragraphs:
                content = ' '.join([p.get_text().strip() for p in paragraphs if p.get_text().strip()])
                if content and len(content) > 200:
                    return content, "paragraphs in main content"
        
        return None, None

    def _process_content_element(self, element: BeautifulSoup) -> Optional[str]:
        """Process a BeautifulSoup element to extract clean content"""
        # Create a copy of the element to avoid modifying the original
        element_copy = BeautifulSoup(str(element), 'html.parser')
        
        # Remove unwanted elements
        unwanted_classes = [
            'flt', 'ads', 'footer', 'disclaimer', 'prime', 'paywall', 
            'social-share', 'related-articles', 'recommended', 'sidebar',
            'advertisement', 'ad-container', 'ad-wrapper', 'advertisement-container',
            'social-media', 'share-buttons', 'comments', 'comment-section',
            'newsletter', 'subscription', 'subscribe', 'sign-up', 'signup',
            'cookie-notice', 'cookie-banner', 'cookie-policy', 'cookie-consent',
            'newsletter-signup', 'newsletter-form', 'newsletter-container',
            'newsletter-wrapper', 'newsletter-box', 'newsletter-banner',
            'newsletter-popup', 'newsletter-modal', 'newsletter-dialog',
            'newsletter-overlay', 'newsletter-backdrop', 'newsletter-close',
            'newsletter-close-button', 'newsletter-close-btn', 'newsletter-dismiss',
            'newsletter-dismiss-button', 'newsletter-dismiss-btn', 'newsletter-hide',
            'newsletter-hide-button', 'newsletter-hide-btn', 'newsletter-remove',
            'newsletter-remove-button', 'newsletter-remove-btn', 'newsletter-exit',
            'newsletter-exit-button', 'newsletter-exit-btn', 'newsletter-close-icon',
            'newsletter-close-x', 'newsletter-close-times', 'newsletter-close-times-icon',
            'newsletter-close-times-x', 'newsletter-close-times-button', 'newsletter-close-times-btn',
            'newsletter-close-times-icon-button', 'newsletter-close-times-icon-btn',
            'newsletter-close-times-icon-x', 'newsletter-close-times-icon-times',
            'newsletter-close-times-icon-close', 'newsletter-close-times-icon-dismiss',
            'newsletter-close-times-icon-hide', 'newsletter-close-times-icon-remove',
            'newsletter-close-times-icon-exit', 'newsletter-close-times-icon-close-button',
            'newsletter-close-times-icon-close-btn', 'newsletter-close-times-icon-dismiss-button',
            'newsletter-close-times-icon-dismiss-btn', 'newsletter-close-times-icon-hide-button',
            'newsletter-close-times-icon-hide-btn', 'newsletter-close-times-icon-remove-button',
            'newsletter-close-times-icon-remove-btn', 'newsletter-close-times-icon-exit-button',
            'newsletter-close-times-icon-exit-btn'
        ]
        
        # Remove elements with unwanted classes
        for unwanted_class in unwanted_classes:
            for elem in element_copy.find_all(class_=lambda c: c and unwanted_class in c):
                elem.decompose()
        
        # Remove script, style, and noscript tags
        for tag in element_copy.find_all(['script', 'style', 'noscript', 'iframe', 'form']):
            tag.decompose()
        
        # Remove elements with specific IDs
        unwanted_ids = ['comments', 'related-articles', 'recommended', 'sidebar', 'advertisement']
        for unwanted_id in unwanted_ids:
            elem = element_copy.find(id=unwanted_id)
            if elem:
                elem.decompose()
        
        # Extract text content
        content = element_copy.get_text(separator=' ', strip=True)
        
        # Remove boilerplate text
        for text in self.boilerplate_text:
            if text in content:
                content = content.split(text)[0]
        
        # Clean up the text
        content = self.clean_text(content)
        
        # Check if content is substantial enough
        if len(content) > 200:
            return content
        else:
            return None

    def process_single_article(self, url: str, headline: str, published_date: str) -> ArticleData:
        """Process a single article URL"""
        try:
            if pd.isna(url) or url == 'URL not available':
                return ArticleData(url, headline, published_date, error="Invalid URL")
            
            response = requests.get(url, headers=self.headers, timeout=15)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            if self.is_paywall_page(soup):
                return ArticleData(url, headline, published_date, error="Paywall detected")
            
            content, method = self.extract_article_content(soup)
            
            if content:
                return ArticleData(url, headline, published_date, content, method)
            else:
                return ArticleData(url, headline, published_date, error="No content found")
                
        except requests.exceptions.RequestException as e:
            return ArticleData(url, headline, published_date, error=f"Request error: {str(e)}")
        except Exception as e:
            return ArticleData(url, headline, published_date, error=f"Unexpected error: {str(e)}")

    def recheck_paywall_articles(self) -> Tuple[List[ArticleData], List[ArticleData], List[ArticleData]]:
        """Recheck articles previously marked as behind paywall"""
        successfully_extracted = []
        still_paywall = []
        failed_urls = []

        for article in self.paywall_urls:
            time.sleep(2)  # Respectful delay
            result = self.process_single_article(article.url, article.headline, article.published_date)
            
            if result.full_content:
                successfully_extracted.append(result)
            elif "Paywall" in str(result.error):
                still_paywall.append(result)
            else:
                failed_urls.append(result)

        return successfully_extracted, still_paywall, failed_urls

    def save_results(self) -> None:
        """Save all results to files"""
        try:
            # Save main articles
            if self.article_data:
                df = pd.DataFrame([vars(article) for article in self.article_data])
                
                # Extract year and month from published dates
                df = extract_year_month(df)
                
                df.to_csv(f'{self.output_dir}/ET_full_articles_{self._get_date_string()}.csv', 
                         index=False, encoding='utf-8')

            # Save failed URLs
            if self.failed_urls:
                self._save_json(self.failed_urls, 'failed_urls')

            # Save paywall URLs
            if self.paywall_urls:
                self._save_json(self.paywall_urls, 'paywall_urls')

        except Exception as e:
            print(f"Error saving results: {str(e)}")

    def _save_json(self, data: List[ArticleData], prefix: str) -> None:
        """Helper method to save data to JSON file"""
        filename = f'{self.output_dir}/{prefix}_{self._get_date_string()}.json'
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump([vars(article) for article in data], f, indent=2)

    @staticmethod
    def _get_date_string() -> str:
        """Get formatted date string for filenames"""
        return datetime.now().strftime("%d_%m_%Y")

    def process_articles(self) -> None:
        """Main method to process all articles"""
        # Read input CSV
        df = pd.read_csv(self.input_file)
        
        print(f"Processing {len(df)} articles...")
        
        # Process each article
        for idx, row in df.iterrows():
            print(f"\nProcessing article {idx + 1}/{len(df)}")
            
            result = self.process_single_article(
                row['article_url'], 
                row['headline'], 
                row['published_date']
            )
            
            if result.full_content:
                self.article_data.append(result)
                print(f"Successfully extracted article ({len(result.full_content)} chars)")
            elif "Paywall" in str(result.error):
                self.paywall_urls.append(result)
                print("Article is behind paywall")
            else:
                self.failed_urls.append(result)
                print(f"Failed to extract article: {result.error}")
            
            time.sleep(2)  # Respectful delay
        
        # Save initial results
        self.save_results()
        
        # Recheck paywall articles
        if self.paywall_urls:
            print("\nRechecking paywall articles...")
            recovered, still_paywall, new_failed = self.recheck_paywall_articles()
            
            # Update lists with recheck results
            if recovered:
                self.article_data.extend(recovered)
            if still_paywall:
                self.paywall_urls = still_paywall
            if new_failed:
                self.failed_urls.extend(new_failed)
            
            # Save final results
            self.save_results()

# ===== Main Function =====

def recheck_paywall_articles_from_json(json_file, output_folder="articles"):
    """
    Recheck articles previously marked as paywalled from a JSON file
    
    Args:
        json_file (str): Path to the JSON file containing paywalled articles
        output_folder (str): Folder to save the results
        
    Returns:
        None
    """
    try:
        # Load the paywalled articles
        with open(json_file, 'r', encoding='utf-8') as f:
            paywalled_articles = json.load(f)
        
        if not paywalled_articles:
            print(f"No paywalled articles found in {json_file}")
            return
        
        print(f"Rechecking {len(paywalled_articles)} previously paywalled articles...")
        
        # Create a scraper instance
        scraper = ArticleScraper(None, output_folder)
        
        # Process each article
        successfully_extracted = []
        still_paywall = []
        failed_urls = []
        
        for idx, article in enumerate(paywalled_articles):
            print(f"\nRechecking article {idx + 1}/{len(paywalled_articles)}: {article['headline']}")
            
            result = scraper.process_single_article(
                article['url'], 
                article['headline'], 
                article['published_date']
            )
            
            if result.full_content:
                successfully_extracted.append(result)
                print(f"Successfully extracted article ({len(result.full_content)} chars)")
            elif "Paywall" in str(result.error):
                still_paywall.append(result)
                print("Article is still behind paywall")
            else:
                failed_urls.append(result)
                print(f"Failed to extract article: {result.error}")
            
            time.sleep(2)  # Respectful delay
        
        # Save the results
        if successfully_extracted:
            df = pd.DataFrame([vars(article) for article in successfully_extracted])
            
            # Extract year and month from published dates
            df = extract_year_month(df)
            
            current_date = datetime.now().strftime("%d_%m_%Y")
            df.to_csv(f'{output_folder}/recovered_articles_{current_date}.csv', index=False, encoding='utf-8')
            print(f"\nSaved {len(successfully_extracted)} recovered articles to CSV")
        
        if still_paywall:
            current_date = datetime.now().strftime("%d_%m_%Y")
            with open(f'{output_folder}/still_paywalled_{current_date}.json', 'w', encoding='utf-8') as f:
                json.dump([vars(article) for article in still_paywall], f, indent=2)
            print(f"Saved {len(still_paywall)} still paywalled articles to JSON")
        
        if failed_urls:
            current_date = datetime.now().strftime("%d_%m_%Y")
            with open(f'{output_folder}/recheck_failed_{current_date}.json', 'w', encoding='utf-8') as f:
                json.dump([vars(article) for article in failed_urls], f, indent=2)
            print(f"Saved {len(failed_urls)} failed articles to JSON")
        
        print("\nRecheck completed!")
        
    except Exception as e:
        print(f"Error rechecking paywalled articles: {str(e)}")

def main():
    """Main entry point of the script"""
    # Configuration
    topic_url = "https://economictimes.indiatimes.com/topic/metlife"  # Change this to your desired topic
    output_folder = "articles"
    
    # Step 1: Scrape URLs
    print("Step 1: Scraping article URLs...")
    df = fetch_all_urls(topic_url)
    print(f"Found {len(df)} articles")
    
    if df.empty:
        print("No articles found. Exiting.")
        return
    
    # Display sample of scraped data
    print("\nSample of scraped data:")
    pd.set_option('display.max_columns', None)
    pd.set_option('display.width', None)
    pd.set_option('display.max_colwidth', None)
    print(df.head())
    
    # Step 2: Save URLs to CSV
    print("\nStep 2: Saving URLs to CSV...")
    csv_file = save_urls_to_csv(df, output_folder)
    
    # Step 3: Extract full article content
    print("\nStep 3: Extracting full article content...")
    scraper = ArticleScraper(csv_file, output_folder)
    scraper.process_articles()
    
    # Step 4: Recheck previously paywalled articles if they exist
    current_date = datetime.now().strftime("%d_%m_%Y")
    paywall_json = f"{output_folder}/paywall_urls_{current_date}.json"
    
    if os.path.exists(paywall_json):
        print("\nStep 4: Rechecking previously paywalled articles...")
        recheck_paywall_articles_from_json(paywall_json, output_folder)
    
    print("\nProcess completed successfully!")

if __name__ == "__main__":
    main() 