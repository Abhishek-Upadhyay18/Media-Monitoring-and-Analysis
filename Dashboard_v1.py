#%%
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime
from spellchecker import SpellChecker
import spacy
import re

#%%
df1 = pd.read_csv('articles/ET_full_articles_merged_24_03_2025.csv')
df2 = pd.read_csv('articles/Mint_article_content_with_keywords_25_03_2025.csv')

#%%
df1['source'] = 'ET'
df2['source'] = 'Mint'

#%%
df = pd.concat([df1, df2])
#%%
df.to_csv('articles/ET_Mint_articles_merged_25_03_2025.csv', index=False)
#%%
# Initialize spell checker and NLP model
spell = SpellChecker()
nlp = spacy.load('en_core_web_sm')

# Add custom words to the spell checker
custom_words = ['metlife', 'healthcare', 'pnb', 'irdai', 'sebi', 'rbi', 'covid']
for word in custom_words:
    spell.word_frequency.add(word)

def extract_entities(text):
    """Extract named entities from text using spaCy"""
    if pd.isna(text):
        return set()
    doc = nlp(str(text))
    # Extract all named entities and multi-word phrases
    entities = set()
    for ent in doc.ents:
        entities.add(ent.text.lower())
    return entities

def clean_text(text):
    """Clean text while preserving named entities"""
    if pd.isna(text):
        return ""
    # Convert to string and remove special characters but keep spaces
    text = str(text)
    text = re.sub(r'[^\w\s]', ' ', text)
    return text

def check_spelling(text):
    """Check spelling while preserving named entities"""
    if pd.isna(text):
        return {}
    
    # Extract named entities first
    entities = extract_entities(text)
    
    # Clean the text
    text = clean_text(text)
    
    # Split into words
    words = text.split()
    
    # Find misspelled words, excluding named entities
    misspelled = set()
    for word in words:
        word_lower = word.lower()
        # Only check spelling if the word is not a named entity
        if word_lower not in entities and not spell.known([word_lower]):
            misspelled.add(word)
    
    # Get corrections for actually misspelled words
    corrections = {}
    for word in misspelled:
        correction = spell.correction(word)
        if correction and correction != word:
            corrections[word] = correction
    
    return corrections

#%%
# Apply spell checking to headline and full_content columns
print("Checking spelling in headlines...")
df['headline_spell_check'] = df['headline'].apply(check_spelling)
df['headline_entities'] = df['headline'].apply(extract_entities)

print("Checking spelling in full_content...")
df['full_context_spell_check'] = df['full_content'].apply(check_spelling)
df['full_context_entities'] = df['full_content'].apply(extract_entities)

#%%
# Save the results
output_filename = f'articles/merged_articles_with_spell_check_and_ner_{datetime.now().strftime("%d_%m_%Y")}.csv'
df.to_csv(output_filename, index=False)
print(f"Saved spell-checked articles with NER to {output_filename}")

#%%
# Print summary of spell checking results
total_headlines = len(df)
headlines_with_errors = df['headline_spell_check'].apply(lambda x: len(x) > 0).sum()
total_contexts = len(df)
contexts_with_errors = df['full_context_spell_check'].apply(lambda x: len(x) > 0).sum()

print("\nSpell Checking Summary:")
print(f"Total headlines checked: {total_headlines}")
print(f"Headlines with spelling errors: {headlines_with_errors}")
print(f"Percentage of headlines with errors: {(headlines_with_errors/total_headlines)*100:.2f}%")
print(f"\nTotal contexts checked: {total_contexts}")
print(f"Contexts with spelling errors: {contexts_with_errors}")
print(f"Percentage of contexts with errors: {(contexts_with_errors/total_contexts)*100:.2f}%")

#%%
# Display some examples of corrections and entities
print("\nExample corrections and entities from headlines:")
for idx, row in df[df['headline_spell_check'].apply(lambda x: len(x) > 0)].head(3).iterrows():
    print(f"\nOriginal: {row['headline']}")
    print("Named Entities:", row['headline_entities'])
    print("Spelling Corrections:", row['headline_spell_check'])

print("\nExample corrections and entities from full_context:")
for idx, row in df[df['full_context_spell_check'].apply(lambda x: len(x) > 0)].head(3).iterrows():
    print(f"\nFirst 100 chars: {row['full_content'][:100]}...")
    print("Sample Named Entities:", list(row['full_context_entities'])[:5])
    print("Sample Spelling Corrections:", dict(list(row['full_context_spell_check'].items())[:5]))

# %%
