import streamlit as st
from newsapi import NewsApiClient
import pandas as pd
from datetime import date, timedelta
from dateutil import parser
import re
from collections import Counter
from fpdf import FPDF

# Improved topic extraction using noun phrase extraction and frequency
from nltk import word_tokenize, pos_tag, ne_chunk
from nltk.chunk import tree2conlltags

import nltk
#nltk.download('punkt')
#nltk.download('averaged_perceptron_tagger')
#nltk.download('maxent_ne_chunker')
#nltk.download('words')
#nltk.download('stopwords')

st.set_page_config(page_title="NewsAPI Media Dashboard", page_icon="📰", layout="wide")
st.title("Live News Fetcher (NewsAPI) - Media Dashboard")

st.write("""
Fetch the latest news articles from NewsAPI.org. Enter your search parameters below and view or download the results instantly.
""")

with st.expander("NewsAPI Parameters", expanded=True):
    # Remove API key input from display
    # api_key = st.text_input("Enter your NewsAPI Key", value="0ebced6d0d454faeaf76b51098b0ad4b", type="password")
    api_key = "0ebced6d0d454faeaf76b51098b0ad4b"  # Use default or set elsewhere
    query = st.text_input("Search Keyword", value="insurance")
    # Restrict date range to last 30 days
    today = date.today()
    min_date = today - timedelta(days=30)
    max_date = today
    col1, col2 = st.columns(2)
    with col1:
        from_date = st.date_input("From Date", value=min_date, min_value=min_date, max_value=max_date)
    with col2:
        to_date = st.date_input("To Date", value=max_date, min_value=min_date, max_value=max_date)
    # Language dropdown with full names
    language_options = [
        ("English", "en"),
        #("Hindi", "hi"),
        ("French", "fr"),
        ("German", "de"),
        ("Spanish", "es")
    ]
    language_display = [name for name, code in language_options]
    language_index = 0  # Default to English
    language_selected = st.selectbox("Language", options=language_display, index=language_index)
    language = dict(language_options)[language_selected]
    # Country selectbox beside sources
    country_options = {
        'All': '',
        'India': 'in',
        'United States': 'us',
        'United Kingdom': 'gb',
        'Australia': 'au',
        'Canada': 'ca',
        'Germany': 'de',
        'France': 'fr',
        'China': 'cn',
        'Japan': 'jp',
        'Singapore': 'sg',
        'South Africa': 'za',
        'New Zealand': 'nz',
        'Russia': 'ru',
        'Brazil': 'br',
        'Italy': 'it',
        'Spain': 'es',
        'UAE': 'ae',
    }
    with col1:
        selected_country_name = st.selectbox("Country", list(country_options.keys()), index=0)
        selected_country = country_options[selected_country_name]
    # Remove the source selection multiselect box
    sources_list = []
    sources_dict = {}
    # Build a mapping from source id to country code for later lookup
    source_id_to_country = {}
    if api_key:
        try:
            newsapi_temp = NewsApiClient(api_key=api_key)
            sources_response = newsapi_temp.get_sources(language=language, country=selected_country if selected_country else None)
            if sources_response and 'sources' in sources_response:
                sources_list = [src['name'] for src in sources_response['sources']]
                sources_dict = {src['name']: src['id'] for src in sources_response['sources']}
                source_id_to_country = {src['id']: src.get('country', None) for src in sources_response['sources']}
        except Exception as e:
            st.warning(f"Could not fetch sources: {e}")
    # selected_sources = st.multiselect("Select News Sources (optional)", options=sources_list)

# Add custom CSS for yellow highlight
st.markdown("""
    <style>
    .highlight-yellow {
        background-color: #ffd700;
        color: #000;
        padding: 2px 8px;
        border-radius: 4px;
        font-weight: 600;
        font-size: 0.95em;
    }
    </style>
""", unsafe_allow_html=True)

def fetch_articles(api_key, query, from_date, to_date, language='en', sources=None):
    newsapi = NewsApiClient(api_key=api_key)
    params = dict(q=query, from_param=from_date, to=to_date, language=language, sort_by='relevancy')
    if sources:
        params['sources'] = sources
    # Do NOT include country in get_everything
    all_articles = newsapi.get_everything(**params)
    return all_articles['articles']

def extract_noun_phrases(text):
    # Tokenize and POS tag
    tokens = word_tokenize(text)
    pos_tags = pos_tag(tokens)
    chunked = ne_chunk(pos_tags, binary=False)
    iob_tagged = tree2conlltags(chunked)
    # Extract contiguous noun phrases
    noun_phrases = []
    current_np = []
    for word, pos, chunk in iob_tagged:
        if chunk.startswith('B') or chunk.startswith('I'):
            current_np.append(word)
        else:
            if current_np:
                noun_phrases.append(' '.join(current_np))
                current_np = []
    if current_np:
        noun_phrases.append(' '.join(current_np))
    return noun_phrases

def assign_topic(title, description, content=None):
    # Combine all available text
    text = f"{title} {description}"
    if content:
        text += f" {content}"
    text = text.strip()
    if not text:
        return "General"
    # Extract noun phrases
    noun_phrases = extract_noun_phrases(text.lower())
    # Remove very short or generic phrases
    noun_phrases = [np for np in noun_phrases if len(np.split()) > 1 and not np.isspace()]
    # Count frequency
    if noun_phrases:
        most_common = Counter(noun_phrases).most_common(1)[0][0]
        return most_common.title()
    # Fallback: use most frequent non-stopword word
    words = re.findall(r'\w+', text.lower())
    stopwords = set(nltk.corpus.stopwords.words('english'))
    words = [w for w in words if w not in stopwords and len(w) > 3]
    if words:
        return Counter(words).most_common(1)[0][0].title()
    return "General"

# --- Fetch and persist articles in session state ---
fetch_triggered = st.button("Fetch News")

if fetch_triggered or (
    'articles' in st.session_state and 'articles_df' in st.session_state and len(st.session_state.articles) > 0
):
    if fetch_triggered:
        if not api_key or not query or not from_date or not to_date:
            st.warning("Please fill all fields.")
            st.stop()
        with st.spinner("Fetching articles from NewsAPI..."):
            sources_param = None
            if sources_dict:
                sources_param = ','.join(sources_dict.values()) if sources_dict else None
            articles = fetch_articles(
                api_key=api_key,
                query=query,
                from_date=from_date.strftime("%Y-%m-%d"),
                to_date=to_date.strftime("%Y-%m-%d"),
                language=language,
                sources=sources_param
            )
            st.session_state.articles = articles
            st.session_state.articles_df = pd.DataFrame(articles)
    articles = st.session_state.articles
    df = st.session_state.articles_df
    if articles:
        st.success(f"Found {len(df)} articles.")
        # Persistent selection: use a dict in session_state
        if 'selected_articles' not in st.session_state or not isinstance(st.session_state.selected_articles, dict):
            st.session_state.selected_articles = {}
        selected_articles = st.session_state.selected_articles
        def article_key(article, idx):
            return article.get('url', f"{article.get('title','')}_{idx}")
        for idx, article in enumerate(articles):
            key = article_key(article, idx)
            checked = selected_articles.get(key, False)
            new_checked = st.checkbox(
                label="Select article",
                key=f"checkbox_{key}",
                value=checked,
                label_visibility="collapsed"
            )
            selected_articles[key] = new_checked
            col1, col2 = st.columns([0.05, 0.95])
            with col2:
                st.subheader(article.get('title', 'No Title'))
                published_at = article.get('publishedAt')
                source = article.get('source', {}).get('name', 'Source not available')
                # --- Country code logic ---
                country_display = 'N/A'
                if selected_country:
                    country_display = selected_country.upper()
                else:
                    source_id = article.get('source', {}).get('id')
                    if source_id and source_id_to_country.get(source_id):
                        country_display = source_id_to_country[source_id].upper()
                if published_at:
                    try:
                        dt = parser.parse(published_at)
                        date_str = dt.strftime('%d %b %Y, %H:%M')
                    except Exception:
                        date_str = published_at
                else:
                    date_str = 'Date not available'
                st.write(f"**Source:** {source} | **Country:** {country_display} | **Published:** {date_str}")
                st.write(article.get('description', 'No Description'))
                st.write(f"[Read more]({article.get('url', '#')})")
                st.markdown("---")
        # Download buttons
        csv = df.to_csv(index=False)
        col_csv, col_pdf = st.columns([1, 1])
        with col_csv:
            st.download_button("Download as CSV", csv, "news_articles.csv", "text/csv")
        with col_pdf:
            def generate_pdf(selected_idxs):
                pdf = FPDF()
                pdf.set_auto_page_break(auto=True, margin=15)
                pdf.add_page()
                pdf.set_font("Arial", size=12)
                def safe_latin1(text):
                    if not text:
                        return ''
                    return str(text).encode('latin-1', 'replace').decode('latin-1')
                for idx in selected_idxs:
                    article = articles[idx]
                    title = safe_latin1(article.get('title', 'No Title'))
                    published_at = safe_latin1(article.get('publishedAt'))
                    source = safe_latin1(article.get('source', {}).get('name', 'Source not available'))
                    url = safe_latin1(article.get('url', '#'))
                    description = safe_latin1(article.get('description', 'No Description'))
                    pdf.set_font("Arial", 'B', 14)
                    pdf.multi_cell(0, 10, title)
                    pdf.set_font("Arial", '', 12)
                    pdf.cell(0, 8, f"Source: {source} | Published: {published_at}", ln=1)
                    pdf.multi_cell(0, 8, description)
                    pdf.set_text_color(0, 0, 255)
                    pdf.cell(0, 8, url, ln=1, link=url)
                    pdf.set_text_color(0, 0, 0)
                    pdf.ln(5)
                return pdf.output(dest='S').encode('latin1')
            selected_idxs = [i for i, article in enumerate(articles) if selected_articles.get(article_key(article, i), False)]
            st.download_button(
                "Download Selected as PDF",
                generate_pdf(selected_idxs) if selected_idxs else b"",
                "selected_articles.pdf",
                "application/pdf",
                disabled=(len(selected_idxs) == 0)
            )
    else:
        st.info("No articles found for your query.")

