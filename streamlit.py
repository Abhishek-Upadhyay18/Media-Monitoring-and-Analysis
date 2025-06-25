#streamlit run streamlit.py --server.headless true

import streamlit as st
import pandas as pd
import ast
from datetime import datetime

# Set page config
st.set_page_config(
    page_title="News Articles Dashboard and Analysis",
    page_icon="📰",
    layout="wide"
)

# Custom CSS to reduce dropdown size and style theme highlights
st.markdown("""
    <style>
    .stSelectbox {
        font-size: 14px;
    }
    .stSelectbox > div > div {
        font-size: 14px;
    }
    .highlight {
        background-color: #ffd700;
        color: #000000;
        padding: 2px 5px;
        border-radius: 3px;
        font-size: 0.9em;
        font-weight: 500;
    }
    .article-theme {
        color: #666666;
        font-style: italic;
        font-size: 0.9em;
        margin-bottom: 1.5em;
    }
    .filter-container {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        margin-bottom: 1rem;
    }
    .filter-title {
        color: #31333F;
        font-size: 1.1rem;
        font-weight: 600;
        margin-bottom: 0.5rem;
    }
    </style>
""", unsafe_allow_html=True)

# Title
st.title("News Articles Dashboard and Analysis")

# Add a simple welcome message and description
st.write("Welcome to the News Articles Analysis Dashboard!")
st.markdown("This dashboard provides analysis of articles from Economic Times, Mint and The Hindu. More features will be added soon.")

# Read the CSV file
@st.cache_data
def load_data():
    df = pd.read_csv('articles/ET_Mint_Hindu_articles_with_advanced_themes_11_04_2025.csv')
    # Convert string representation of list to actual list
    df['topics'] = df['topics'].apply(lambda x: ast.literal_eval(x) if isinstance(x, str) else [])
    df['article_themes'] = df['article_themes'].apply(lambda x: ast.literal_eval(x) if isinstance(x, str) else [])
    df['themes'] = df['themes'].apply(lambda x: ast.literal_eval(x) if isinstance(x, str) else [])
    
    # Convert published_date to datetime and extract year and month
    # First, clean up the date strings for Mint format like "5 min read.17 Jan 2025"
    df['published_date_cleaned'] = df['published_date'].apply(
        lambda x: x.split('.')[-1] if isinstance(x, str) and 'min read.' in x else x
    )
    
    # Try multiple date formats for different sources
    df['published_date'] = pd.to_datetime(
        df['published_date_cleaned'], 
        format='%d %b, %Y, %I:%M %p IST',  # ET format: "27 Mar, 2025, 12:51 AM IST"
        errors='coerce'
    )
    
    # For dates that failed to parse with the first format, try additional formats
    mask = pd.isna(df['published_date'])
    if mask.any():
        # Try Mint format: "17 Jan 2025"
        df.loc[mask, 'published_date'] = pd.to_datetime(
            df.loc[mask, 'published_date_cleaned'],
            format='%d %b %Y',
            errors='coerce'
        )
    
    # Try one more format for any remaining unparsed dates
    mask = pd.isna(df['published_date'])
    if mask.any():
        # Try format like "13-Jun-24" (Hindu format)
        df.loc[mask, 'published_date'] = pd.to_datetime(
            df.loc[mask, 'published_date_cleaned'],
            format='%d-%b-%y',
            errors='coerce'
        )
    
    # Clean up the temporary column
    df = df.drop('published_date_cleaned', axis=1)
    
    # Now extract year and month for rows with valid dates
    df.loc[~pd.isna(df['published_date']), 'year'] = df.loc[~pd.isna(df['published_date']), 'published_date'].dt.year
    df.loc[~pd.isna(df['published_date']), 'month'] = df.loc[~pd.isna(df['published_date']), 'published_date'].dt.month_name()
    
    # Set placeholders for invalid dates - Replacing 'Unknown' with 2025
    df['year'] = df['year'].fillna(2025)
    df['month'] = df['month'].fillna('Unknown')
    
    # Replace any remaining 'Unknown' in year with 2025
    df.loc[df['year'] == 'Unknown', 'year'] = 2025
    
    return df

# Load the data
df = load_data()

# Create filter container
st.markdown('<div class="filter-container">', unsafe_allow_html=True)
st.markdown('<div class="filter-title">Filter Articles</div>', unsafe_allow_html=True)

# Create four columns for filters
col1, col2, col3, col4 = st.columns(4)

with col1:
    # Create a dropdown for source selection
    sources = ['All'] + sorted(df['source'].unique().tolist())
    selected_source = st.selectbox('Select Source', sources, key='source_select')

with col2:
    # Create a dropdown for year selection with numeric years only (no 'Unknown')
    unique_years = sorted(df['year'].unique(), reverse=True)  # Most recent years first
    years = ['All'] + [str(int(y)) for y in unique_years]  # Convert to int then string to remove decimals
    selected_year = st.selectbox('Select Year', years, key='year_select')

with col3:
    # Create a dropdown for month selection in a fixed order
    month_order = ['All', 'January', 'February', 'March', 'April', 'May', 'June', 
                  'July', 'August', 'September', 'October', 'November', 'December', 'Unknown']
    
    # Get unique months that exist in the data
    available_months = ['All'] + [m for m in month_order[1:] if m in df['month'].unique()]
    
    selected_month = st.selectbox('Select Month', available_months, key='month_select')

with col4:
    # Get all unique themes from the themes column (TEST)
    all_themes = set()
    for theme_list in df['themes']:
        all_themes.update(theme_list)
    all_themes = sorted(list(all_themes))
    
    # Create a multi-select for themes
    selected_themes = st.multiselect(
        'Select Themes from keywords',
        options=all_themes,
        default=[],
        key='theme_select'
    )

st.markdown('</div>', unsafe_allow_html=True)

# Filter the dataframe based on selected source, year, month and themes
filtered_df = df.copy()

if selected_source != 'All':
    filtered_df = filtered_df[filtered_df['source'] == selected_source]

if selected_year != 'All':
    # Convert the selected year to numeric for comparison with numeric values in dataframe
    selected_year_numeric = int(selected_year)
    # Cast the dataframe year values to integers to match
    filtered_df = filtered_df[filtered_df['year'].astype(int) == selected_year_numeric]

if selected_month != 'All':
    filtered_df = filtered_df[filtered_df['month'] == selected_month]

if selected_themes:
    # Filter articles that contain any of the selected themes in the themes column (TEST)
    filtered_df = filtered_df[filtered_df['themes'].apply(lambda x: any(theme in x for theme in selected_themes))]

# Display articles or message if none found
if len(filtered_df) == 0:
    st.markdown("### No articles found.")
else:
    for _, article in filtered_df.iterrows():
        st.markdown(f"### {article['headline']}")
        
        # Display source and published date (handling NaN dates)
        date_display = "Date not captured"
        if not pd.isna(article['published_date']):
            date_display = article['published_date'].strftime('%d %B, %Y, %I:%M %p')
        
        source_date = f"**Source:** {article['source']} | **Published Date:** {date_display}"
        
        # Add matching themes if selected
        if selected_themes:
            # Check if any selected themes match in the themes list
            matching_themes = [theme for theme in selected_themes if theme in article['themes']]
            if matching_themes:
                themes_str = " | ".join([f'<span class="highlight">{theme}</span>' for theme in matching_themes])
                source_date += f" | **Themes:** {themes_str}"
        
        st.markdown(source_date, unsafe_allow_html=True)
        
        # Display topics if available
        #if article['topics']:
        #    topics_str = " | ".join(article['topics'])
        #    st.markdown(f'<div class="article-theme">**Topics:** {topics_str}</div>', unsafe_allow_html=True)
        
        # Display article themes from LLM analysis
        if article['article_themes']:
            themes_str = " | ".join(article['article_themes'])
            st.markdown(f'<div class="article-theme">**Theme after analysing the article using LLM:** {themes_str}</div>', unsafe_allow_html=True)
        
        st.write("")  # Add an empty line for spacing
        st.write("**Content:**")
        st.write(article['full_content'])
        st.markdown("---")
