#%%
# Import required libraries
import pandas as pd          # For data manipulation and CSV handling
from bs4 import BeautifulSoup  # For HTML parsing
import requests             # For making HTTP requests
import time                # For adding delays between requests
import json               # For JSON file operations
import re                 # For regular expression operations
import os                 # For file and directory operations
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass
from datetime import datetime

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
        paywall_indicators = [
            'articleBlocker',
            'paywall_box',
            'prime_paywall',
            'subscribeBtn',
        ]
        
        for indicator in paywall_indicators:
            if soup.find(class_=indicator):
                return True
        
        article_content = soup.find(class_=['artText', 'article-text', 'article_content']) or soup.find('article')
        return not (article_content and len(article_content.get_text().strip()) > 200)

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
            {'type': 'class', 'name': 'story-details'}
        ]
        
        for selector in content_selectors:
            element = soup.find(class_=selector['name'])
            if element:
                content = self._process_content_element(element)
                if content:
                    return content, f"class: {selector['name']}"
        
        return None, None

    def _process_content_element(self, element: BeautifulSoup) -> Optional[str]:
        """Process a BeautifulSoup element to extract clean content"""
        # Remove unwanted elements
        for unwanted in element.find_all(['script', 'style', 'noscript', 'div']):
            if unwanted.get('class') and any(c in ['flt', 'ads', 'footer', 'disclaimer', 'prime', 'paywall'] 
                                           for c in unwanted.get('class')):
                unwanted.decompose()
        
        content = element.get_text(separator=' ', strip=True)
        
        # Remove boilerplate text
        for text in self.boilerplate_text:
            if text in content:
                content = content.split(text)[0]
        
        content = self.clean_text(content)
        return content if len(content) > 200 else None

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

def main():
    """Main entry point of the script"""
    input_file = f'articles/news_articles_ET_{datetime.now().strftime("%d_%m_%Y")}.csv'
    scraper = ArticleScraper(input_file)
    scraper.process_articles()

if __name__ == "__main__":
    main()

# %%
# TOI
