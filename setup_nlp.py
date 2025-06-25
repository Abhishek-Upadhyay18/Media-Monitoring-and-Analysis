import nltk
import spacy

def download_nlp_resources():
    # Download popular NLTK datasets
    nltk_packages = [
        'punkt',
        'averaged_perceptron_tagger',
        'wordnet',
        'stopwords',
        'vader_lexicon'
    ]
    
    print("Downloading NLTK resources...")
    for package in nltk_packages:
        try:
            nltk.download(package)
            print(f"Successfully downloaded {package}")
        except Exception as e:
            print(f"Error downloading {package}: {str(e)}")

    # Download spaCy English model
    print("\nDownloading spaCy English model...")
    try:
        spacy.cli.download("en_core_web_sm")
        print("Successfully downloaded spaCy English model")
    except Exception as e:
        print(f"Error downloading spaCy model: {str(e)}")

if __name__ == "__main__":
    download_nlp_resources() 