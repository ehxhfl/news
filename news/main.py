import logging
import json
import os
import shutil
from datetime import datetime
from scraper import scrape_feeds
from ai_curator import curate_articles
from generator import generate_html

def main():
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
    logging.info("=== AI Curated Japan News Started ===")
    
    # 1. Scrape
    logging.info("Step 1: Scraping feeds...")
    articles = scrape_feeds()
    logging.info(f"Scraped {len(articles)} articles.")
    
    if not articles:
        logging.warning("No articles scraped. Exiting.")
        return
        
    # 2. AI Curation
    logging.info("Step 2: AI Curation (this will take a while)...")
    curated_articles = curate_articles(articles)
    
    # 3. Save raw data just in case
    with open("data.json", "w", encoding="utf-8") as f:
        json.dump(curated_articles, f, ensure_ascii=False, indent=2)
        
    # 4. Generate HTML and Archive
    logging.info("Step 3: Generating HTML...")
    generate_html(curated_articles, "index.html")
    
    # Archive the daily run
    today_str = datetime.now().strftime("%Y-%m-%d")
    archive_path = f"archive-{today_str}.html"
    shutil.copy("index.html", archive_path)
    # Regenerate index.html to include the new archive in the sidebar
    generate_html(curated_articles, "index.html")
    # Regenerate the archive file so it also has the updated sidebar
    generate_html(curated_articles, archive_path)
    
    logging.info(f"=== Done! Saved to index.html and {archive_path} ===")

if __name__ == "__main__":
    main()
