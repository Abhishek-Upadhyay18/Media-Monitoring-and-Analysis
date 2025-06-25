#%%
import requests
from bs4 import BeautifulSoup
import json
import os

from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass
from datetime import datetime
import pandas as pd
import time
import re

@dataclass
class ArticleData:
    """Data class to store article information"""
    url: str
    headline: str
    published_date: str
    full_content: Optional[str] = None
    extraction_method: Optional[str] = None
    error: Optional[str] = None

class NewsArticleScraper:
    """Generic news article scraper that can handle multiple sources"""
    
    def __init__(self, input_file: str, output_dir: str = 'articles'):
        self.input_file = input_file
        self.output_dir = output_dir
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        # Common boilerplate text patterns to remove
        self.boilerplate_text = [
            "Download The News App",
            "Subscribe to our WhatsApp channel",
            "Disclaimer Statement:",
            "Read More News on",
            "Prime Exclusives",
            "View all Stories",
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

    def is_paywall_page(self, soup: BeautifulSoup, source: str) -> bool:
        """Check if article is behind paywall based on source-specific indicators"""
        paywall_indicators = {
            'economictimes': ['articleBlocker', 'paywall_box', 'prime_paywall', 'subscribeBtn'],
            'livemint': ['paywall', 'subscription-content', 'paywall-container'],
            # Add indicators for other sources here
        }
        
        # Get source-specific indicators or use default ones
        indicators = paywall_indicators.get(source.lower(), ['paywall', 'subscription'])
        
        for indicator in indicators:
            if soup.find(class_=indicator):
                return True
                
        article_content = soup.find(class_=['artText', 'article-text']) or soup.find('article')
        return not (article_content and len(article_content.get_text().strip()) > 200)

    def extract_article_content(self, soup: BeautifulSoup, source: str) -> Tuple[Optional[str], Optional[str]]:
        """Extract article content using source-specific selectors"""
        # Common content selectors for different sources
        content_selectors = {
            'economictimes': [
                {'type': 'tag', 'name': 'article'},
                {'type': 'class', 'name': 'artText'},
                {'type': 'class', 'name': 'article_wrap'}
            ],
            'livemint': [
                {'type': 'class', 'name': 'mainArea'},
                {'type': 'class', 'name': 'articleBody'},
                {'type': 'tag', 'name': 'article'}
            ]
            # Add selectors for other sources here
        }
        
        # Get source-specific selectors or use default ones
        selectors = content_selectors.get(source.lower(), [
            {'type': 'tag', 'name': 'article'},
            {'type': 'class', 'name': 'article-content'},
            {'type': 'class', 'name': 'story-content'}
        ])
        
        for selector in selectors:
            element = None
            if selector['type'] == 'class':
                element = soup.find(class_=selector['name'])
            elif selector['type'] == 'tag':
                element = soup.find(selector['name'])
                
            if element:
                # Remove unwanted elements
                for unwanted in element.find_all(['script', 'style', 'noscript', 'div']):
                    if unwanted.get('class') and any(c in ['ads', 'footer', 'paywall'] for c in unwanted.get('class')):
                        unwanted.decompose()
                
                content = element.get_text(separator=' ', strip=True)
                
                # Remove boilerplate text
                for text in self.boilerplate_text:
                    if text in content:
                        content = content.split(text)[0]
                
                content = self.clean_text(content)
                if len(content) > 200:
                    return content, f"{selector['type']}: {selector['name']}"
        
        return None, None

    def process_single_article(self, url: str, headline: str, published_date: str, source: str) -> ArticleData:
        """Process a single article URL"""
        try:
            response = requests.get(url, headers=self.headers, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            if self.is_paywall_page(soup, source):
                return ArticleData(url, headline, published_date, error="Paywall detected")
            
            content, method = self.extract_article_content(soup, source)
            
            if content:
                return ArticleData(url, headline, published_date, content, method)
            else:
                return ArticleData(url, headline, published_date, error="No content found")
                
        except requests.exceptions.RequestException as e:
            return ArticleData(url, headline, published_date, error=f"Request error: {str(e)}")
        except Exception as e:
            return ArticleData(url, headline, published_date, error=f"Unexpected error: {str(e)}")

    def process_articles(self, source: str) -> None:
        """Process all articles from the input file"""
        df = pd.read_csv(self.input_file)
        
        print(f"Processing {len(df)} articles from {source}...")
        
        for idx, row in df.iterrows():
            print(f"\nProcessing article {idx + 1}/{len(df)}")
            
            result = self.process_single_article(
                row['article_url'],
                row['headline'],
                row['published_date'],
                source
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
        
        self.save_results(source)

    def save_results(self, source: str) -> None:
        """Save results to files with source prefix"""
        try:
            if self.article_data:
                df = pd.DataFrame([vars(article) for article in self.article_data])
                df.to_csv(f'{self.output_dir}/{source}_articles_{self._get_date_string()}.csv',
                         index=False, encoding='utf-8')

            if self.failed_urls:
                self._save_json(self.failed_urls, f'{source}_failed_urls')

            if self.paywall_urls:
                self._save_json(self.paywall_urls, f'{source}_paywall_urls')

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

def main():
    """Example usage"""
    # Process Economic Times articles
    et_input = f'articles/news_articles_ET_{datetime.now().strftime("%d_%m_%Y")}.csv'
    et_scraper = NewsArticleScraper(et_input)
    et_scraper.process_articles('economictimes')
    
    # Process Mint articles
    mint_input = f'articles/news_articles_Mint_{datetime.now().strftime("%d_%m_%Y")}.csv'
    mint_scraper = NewsArticleScraper(mint_input)
    mint_scraper.process_articles('livemint')

if __name__ == "__main__":
    main()
