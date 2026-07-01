from deep_translator import GoogleTranslator
import logging
import time

def translate_text(text, source='ja', target='ko'):
    if not text:
        return ""
    try:
        translator = GoogleTranslator(source=source, target=target)
        # Handle long texts if needed, but summary is already truncated
        translated = translator.translate(text)
        return translated
    except Exception as e:
        logging.error(f"Translation failed for '{text[:20]}...': {e}")
        return text # fallback to original

def translate_articles(articles):
    logging.info("Starting translation of articles...")
    for idx, article in enumerate(articles):
        logging.info(f"Translating article {idx+1}/{len(articles)}")
        article['title_ko'] = translate_text(article['title_ja'])
        article['summary_ko'] = translate_text(article['summary_ja'])
        time.sleep(0.5) # Basic rate limiting to prevent getting blocked
    return articles
