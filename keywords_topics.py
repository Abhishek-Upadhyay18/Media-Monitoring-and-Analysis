
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime
from spellchecker import SpellChecker
import os
from collections import Counter, defaultdict
import re
import nltk
import sys
import spacy
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.decomposition import LatentDirichletAllocation
import numpy as np

# Initialize spaCy
try:
    nlp = spacy.load("en_core_web_sm")
except OSError:
    print("Downloading spaCy English language model...")
    import subprocess
    subprocess.run(["python", "-m", "spacy", "download", "en_core_web_sm"])
    nlp = spacy.load("en_core_web_sm")


def load_and_merge_articles(sources, date):
    """
    Load and merge article files from multiple sources for a specific date
    
    Args:
        sources (list): List of news sources (e.g. ['ET', 'Mint', 'Hindu'])
        date (str): Date string in format DD_MM_YYYY (e.g., "11_04_2025")
        
    Returns:
        pd.DataFrame: Merged dataframe containing articles from all sources
    """
    dfs = []
    
    # Convert date format if it contains underscores (DD_MM_YYYY to DDMMYYYY)
    file_date = date.replace('_', '') if '_' in date else date
    
    for source in sources:
        filename = f'articles/{source}_full_articles_{date}.csv'
        try:
            df = pd.read_csv(filename)
            df['source'] = source  # Add source column
            dfs.append(df)
            print(f"Loaded {len(df)} articles from {filename}")
        except FileNotFoundError:
            print(f"Warning: File not found - {filename}")
            # Try alternate filename format
            alt_filename = f'articles/{source}_full_articles_{file_date}.csv'
            try:
                df = pd.read_csv(alt_filename)
                # Map source names to full names
                if source == 'ET':
                    df['source'] = 'Economic Times'
                elif source == 'Hindu':
                    df['source'] = 'The Hindu'
                else:
                    df['source'] = source
                dfs.append(df)
                print(f"Loaded {len(df)} articles from {alt_filename}")
            except FileNotFoundError:
                print(f"Warning: Alternative file not found either - {alt_filename}")
            except Exception as e:
                print(f"Error loading alternative file {alt_filename}: {str(e)}")
        except Exception as e:
            print(f"Error loading {filename}: {str(e)}")
            
    if not dfs:
        raise ValueError("No article files could be loaded")
        
    # Merge all dataframes
    merged_df = pd.concat(dfs, ignore_index=True)
    
    print(f"\nSuccessfully merged {len(merged_df)} total articles from {len(dfs)} sources")
    
    # Save merged file
    output_file = f'articles/{"_".join(sources)}_articles_merged_{date}.csv'
    merged_df.to_csv(output_file, index=False)
    print(f"Saved merged articles to {output_file}")
    
    return merged_df


def find_keywords_in_content(content, keywords):
    """Find which keywords are present in the content."""
    if pd.isna(content):
        return []
    content = str(content).lower()
    return [keyword for keyword in keywords if keyword.lower() in content]


def extract_themes(text):
    """Extract themes from text based on keyword matching."""
    if pd.isna(text):
        return []
    
    text = str(text).lower()
    themes = []
    
    for theme, keywords in theme_keywords.items():
        # Check if any of the theme's keywords appear in the text
        if any(keyword in text for keyword in keywords):
            themes.append(theme)
    
    return themes

def preprocess_text(text):
    """Preprocess text for theme analysis."""
    if pd.isna(text):
        return ""
    
    # Convert to string and lowercase
    text = str(text).lower()
    
    # Remove special characters and numbers
    text = re.sub(r'[^a-zA-Z\s]', '', text)
    
    # Process with spaCy
    doc = nlp(text)
    
    # Extract meaningful words (nouns, verbs, adjectives)
    meaningful_words = []
    for token in doc:
        if (token.pos_ in ['NOUN', 'VERB', 'ADJ'] and 
            not token.is_stop and 
            len(token.text) > 2):
            meaningful_words.append(token.lemma_)
    
    return ' '.join(meaningful_words)

def extract_key_phrases(text):
    """Extract key phrases from text using spaCy."""
    if pd.isna(text):
        return []
    
    doc = nlp(str(text))
    phrases = []
    
    # Extract noun phrases
    for chunk in doc.noun_chunks:
        if len(chunk.text.split()) > 1:  # Only consider multi-word phrases
            phrases.append(chunk.text.lower())
    
    return phrases

def analyze_article_themes(text):
    """Analyze article content to extract themes."""
    if pd.isna(text):
        return []
    
    text = str(text)
    doc = nlp(text)
    
    # Define theme categories and their associated keywords
    theme_categories = {
        'Business & Economy': ['business', 'economy', 'market', 'trade', 'industry', 'company', 'financial', 'investment'],
        'Technology & Innovation': ['technology', 'digital', 'innovation', 'tech', 'software', 'hardware', 'internet', 'data'],
        'Politics & Governance': ['government', 'political', 'policy', 'minister', 'parliament', 'democracy', 'election'],
        'Healthcare & Medicine': ['health', 'medical', 'hospital', 'doctor', 'patient', 'disease', 'treatment'],
        'Education & Learning': ['education', 'school', 'university', 'student', 'teacher', 'learning'],
        'Environment & Climate': ['environment', 'climate', 'sustainable', 'green', 'pollution', 'energy'],
        'Science & Research': ['science', 'research', 'study', 'scientist', 'discovery', 'experiment'],
        'Social Issues': ['social', 'community', 'society', 'welfare', 'development', 'poverty'],
        'Culture & Arts': ['culture', 'art', 'music', 'literature', 'heritage', 'tradition'],
        'Sports & Recreation': ['sports', 'game', 'athlete', 'competition', 'tournament', 'championship']
    }
    
    # Extract key phrases
    key_phrases = extract_key_phrases(text)
    
    # Analyze text for themes
    themes = []
    text_lower = text.lower()
    
    # Check for theme matches
    for theme, keywords in theme_categories.items():
        # Check if any keywords appear in the text
        if any(keyword in text_lower for keyword in keywords):
            themes.append(theme)
    
    # Add custom themes based on key phrases
    if len(key_phrases) > 0:
        # Get the most frequent key phrases
        phrase_counts = defaultdict(int)
        for phrase in key_phrases:
            phrase_counts[phrase] += 1
        
        # Add top key phrases as themes if they're significant
        top_phrases = sorted(phrase_counts.items(), key=lambda x: x[1], reverse=True)[:3]
        for phrase, count in top_phrases:
            if count > 1:  # Only add if phrase appears multiple times
                themes.append(f"Topic: {phrase.title()}")
    
    return list(set(themes))  # Remove duplicates

# Define keyword and theme dictionaries
life_insurance_keywords = [
    # Policy & Coverage
    "Term Insurance", "Whole Life Insurance", "Endowment Policy", "Universal Life Insurance",
    "Variable Life Insurance", "Guaranteed Issue", "Cash Value", "Surrender Value", 
    "Paid-Up Policy", "Riders", "Annuity", "Participating Policy", "Non-Participating Policy", 
    "Convertible Policy",

    # Premium & Payments
    "Premium", "Single-Premium Policy", "Level Premium", "Renewable Premium", 
    "Grace Period", "Underwriting", "Actuarial Valuation", "Risk Assessment", 
    "Policy Lapse", "Reinstatement",

    # Claims & Payouts
    "Death Benefit", "Maturity Benefit", "Sum Assured", "Nominee", "Beneficiary", 
    "Claim Settlement", "Contingent Beneficiary", "Exclusions", "Claim Ratio", 
    "Survival Benefit", "Waiting Period", "Free Look Period",

    # Regulatory & Compliance
    "IRDAI", "Solvency Ratio", "Anti-Money Laundering (AML)", "KYC", "Free-look Period", 
    "Tax Benefits", "Section 80C", "Section 10(10D)", "Insurable Interest",

    # Actuarial & Risk
    "Mortality Table", "Morbidity Rate", "Risk Pooling", "Reinsurance", 
    "Underwriting Guidelines", "Persistency Ratio", "Expense Ratio",

    # Marketing & Sales
    "Sum Insured", "Policy Illustration", "Surrender Charges", "Guaranteed Returns", 
    "Bonus", "Reversionary Bonus", "Terminal Bonus", "ULIP (Unit Linked Insurance Plan)"
]

theme_keywords = {
    'Finance': ['finance', 'financial', 'money', 'investment', 'bank', 'stock', 'market', 'economy', 'economic'],
    'Technology': ['tech', 'technology', 'digital', 'innovation', 'software', 'hardware', 'internet', 'data', 'AI', 'artificial intelligence'],
    'Business': ['business', 'company', 'enterprise', 'corporate', 'industry', 'market', 'trade', 'commerce'],
    'Politics': ['politics', 'political', 'government', 'policy', 'election', 'minister', 'parliament', 'democracy'],
    'Healthcare': ['health', 'medical', 'hospital', 'doctor', 'patient', 'disease', 'treatment', 'medicine'],
    'Education': ['education', 'school', 'university', 'student', 'teacher', 'learning', 'academic'],
    'Environment': ['environment', 'climate', 'sustainable', 'green', 'pollution', 'energy', 'renewable'],
    'Sports': ['sports', 'game', 'match', 'player', 'team', 'championship', 'tournament'],
    'Entertainment': ['entertainment', 'movie', 'film', 'music', 'celebrity', 'artist', 'show', 'performance']
}

# Main execution function
def main():
    try:
        # Get current date in DD_MM_YYYY format
        current_date = datetime.now().strftime("%d_%m_%Y")
        
        # Download required NLTK data with better error handling
        required_nltk_data = ['punkt', 'stopwords']
        for package in required_nltk_data:
            try:
                nltk.data.find(f'tokenizers/{package}' if package == 'punkt' else f'corpora/{package}')
                print(f"NLTK {package} package already downloaded")
            except LookupError:
                try:
                    print(f"Downloading NLTK {package} package...")
                    nltk.download(package)
                    print(f"Successfully downloaded NLTK {package} package")
                except Exception as e:
                    print(f"Error downloading NLTK {package} package: {str(e)}")
                    print("Continuing with basic text analysis...")
                    break
        
        # Load and merge articles using the function
        sources = ['ET', 'Mint', 'Hindu']  # Define your sources
        date = '11_04_2025'  # Date format with underscores DD_MM_YYYY
        
        print(f"Loading and merging articles from {sources} for date {date}...")
        df = load_and_merge_articles(sources, date)
        
        print("\nAvailable columns in the DataFrame:")
        print(df.columns.tolist())
        print(df.head())
        
        # Keyword Analysis
        print("\nStarting Keyword Analysis...")
        df['topics'] = df['full_content'].apply(lambda x: find_keywords_in_content(x, life_insurance_keywords))
        df['keyword_count'] = df['topics'].apply(len)
        
        # Display the results
        print("\nArticles with life insurance keywords:")
        display_columns = [col for col in ['headline', 'title', 'url', 'full_content'] if col in df.columns]
        display_columns.extend(['topics', 'keyword_count'])
        print(df[display_columns].head())
        
        # Save the results to a new CSV file with current date
        output_file = f'articles/{"_".join(sources)}_articles_with_keywords_{current_date}.csv'
        df.to_csv(output_file, index=False)
        print(f"\nResults saved to {output_file}")
        
        # Print some statistics
        total_articles = len(df)
        articles_with_keywords = len(df[df['keyword_count'] > 0])
        print(f"\nStatistics:")
        print(f"Total articles analyzed: {total_articles}")
        print(f"Articles containing life insurance keywords: {articles_with_keywords}")
        print(f"Percentage of articles with keywords: {(articles_with_keywords/total_articles)*100:.2f}%")
        
        # Theme Analysis
        print("\nStarting Theme Analysis...")
        df['themes'] = df['full_content'].apply(extract_themes)
        df['theme_count'] = df['themes'].apply(len)
        
        # Print some statistics about themes
        print("\nTheme Analysis Results:")
        print(f"Total articles analyzed: {len(df)}")
        print("\nTheme distribution:")
        
        # Calculate theme distribution
        theme_distribution = {}
        for themes in df['themes']:
            for theme in themes:
                theme_distribution[theme] = theme_distribution.get(theme, 0) + 1
        
        # Sort themes by count
        sorted_themes = sorted(theme_distribution.items(), key=lambda x: x[1], reverse=True)
        for theme, count in sorted_themes:
            print(f"{theme}: {count} articles ({(count/len(df))*100:.1f}%)")
        
        # Save the results with current date
        output_file = f'articles/{"_".join(sources)}_articles_with_themes_{current_date}.csv'
        df.to_csv(output_file, index=False)
        print(f"\nResults saved to {output_file}")
        
        # Advanced Theme Analysis
        print("\nStarting Advanced Theme Analysis...")
        df['processed_content'] = df['full_content'].apply(preprocess_text)
        df['article_themes'] = df['full_content'].apply(analyze_article_themes)
        df['theme_count'] = df['article_themes'].apply(len)
        
        # Calculate theme distribution
        theme_distribution = defaultdict(int)
        for themes in df['article_themes']:
            for theme in themes:
                theme_distribution[theme] += 1
        
        # Sort and display theme distribution
        print("\nTheme distribution:")
        sorted_themes = sorted(theme_distribution.items(), key=lambda x: x[1], reverse=True)
        for theme, count in sorted_themes:
            print(f"{theme}: {count} articles ({(count/len(df))*100:.1f}%)")
        
        # Save results with current date
        output_file = f'articles/{"_".join(sources)}_articles_with_advanced_themes_{current_date}.csv'
        df.to_csv(output_file, index=False)
        print(f"\nResults saved to {output_file}")
        
    except Exception as e:
        print(f"Error in main execution: {str(e)}")
        raise

# Execute main function when run as script
if __name__ == "__main__":
    main()
