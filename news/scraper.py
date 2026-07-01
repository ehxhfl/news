import feedparser
import json
import logging
from bs4 import BeautifulSoup
from datetime import datetime

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def clean_html(raw_html):
    if not raw_html:
        return ""
    soup = BeautifulSoup(raw_html, "html.parser")
    text = soup.get_text(separator=" ", strip=True)
    return text[:200] + "..." if len(text) > 200 else text

import requests

def extract_image(entry):
    # Try to find image in enclosures or media_content
    if 'media_content' in entry and len(entry.media_content) > 0:
        return entry.media_content[0].get('url', '')
    if 'enclosures' in entry and len(entry.enclosures) > 0:
        for enc in entry.enclosures:
            if 'image' in enc.get('type', ''):
                return enc.get('href', '')
    
    # Try to parse from summary HTML
    if 'summary' in entry:
        soup = BeautifulSoup(entry.summary, "html.parser")
        img = soup.find('img')
        if img and img.get('src'):
            return img.get('src')
            
    # Fetch original page and find og:image
    link = entry.get('link', '')
    if link:
        try:
            resp = requests.get(link, timeout=5)
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, "html.parser")
                og_img = soup.find("meta", property="og:image")
                if og_img and og_img.get("content"):
                    return og_img.get("content")
        except Exception as e:
            logging.debug(f"Could not fetch og:image for {link}: {e}")
            
    return None

def scrape_feeds(config_path="config.json", limit_per_feed=5):
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
    except Exception as e:
        logging.error(f"Failed to load config: {e}")
        return []

    articles = []
    for feed in config.get("feeds", []):
        logging.info(f"Fetching feed: {feed['name']} ({feed['url']})")
        parsed = feedparser.parse(feed['url'])
        
        count = 0
        for entry in parsed.entries:
            if count >= limit_per_feed:
                break
            
            title = entry.get('title', '')
            link = entry.get('link', '')
            summary = clean_html(entry.get('summary', entry.get('description', '')))
            published = entry.get('published', entry.get('pubDate', ''))
            image_url = extract_image(entry)
            
            articles.append({
                "category": feed['category'],
                "source": feed['name'],
                "title_ja": title,
                "summary_ja": summary,
                "link": link,
                "published": published,
                "image_url": image_url
            })
            count += 1
            
    return articles

if __name__ == "__main__":
    arts = scrape_feeds()
    for a in arts[:2]:
        print(a)
