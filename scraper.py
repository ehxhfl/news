import calendar
import html
import json
import logging
from urllib.parse import parse_qsl, urlencode, urljoin, urlsplit, urlunsplit

import feedparser
import requests
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

USER_AGENT = "NewsCurator/1.0 (RSS reader)"
FEED_TIMEOUT = (5, 20)
PAGE_TIMEOUT = (5, 10)
RETRYABLE_STATUS_CODES = (429, 500, 502, 503, 504)
TRACKING_QUERY_KEYS = {"fbclid", "gclid", "mc_cid", "mc_eid"}


def clean_html(raw_html, max_length=600):
    if not raw_html or max_length <= 0:
        return ""

    raw_text = str(raw_html)
    if "<" in raw_text and ">" in raw_text:
        soup = BeautifulSoup(raw_text, "html.parser")
        text = soup.get_text(separator=" ", strip=True)
    else:
        text = " ".join(html.unescape(raw_text).split())
    if len(text) <= max_length:
        return text

    return text[: max_length - 1].rstrip() + "…"


def normalize_url(url):
    """Return a stable URL used only as the in-run deduplication key."""
    if not url:
        return ""

    try:
        parts = urlsplit(str(url).strip())
    except (TypeError, ValueError):
        return ""

    scheme = parts.scheme.lower()
    netloc = parts.netloc.lower()
    if scheme not in {"http", "https"} or not netloc:
        return ""

    if scheme == "http" and netloc.endswith(":80"):
        netloc = netloc[:-3]
    elif scheme == "https" and netloc.endswith(":443"):
        netloc = netloc[:-4]

    path = parts.path.rstrip("/") or "/"
    query_items = [
        (key, value)
        for key, value in parse_qsl(parts.query, keep_blank_values=True)
        if not key.lower().startswith("utm_") and key.lower() not in TRACKING_QUERY_KEYS
    ]
    query = urlencode(sorted(query_items))
    return urlunsplit((scheme, netloc, path, query, ""))


def _build_session():
    retry = Retry(
        total=3,
        connect=3,
        read=3,
        status=3,
        backoff_factor=0.5,
        status_forcelist=RETRYABLE_STATUS_CODES,
        allowed_methods=frozenset({"GET"}),
        respect_retry_after_header=True,
    )
    adapter = HTTPAdapter(max_retries=retry)

    session = requests.Session()
    session.headers.update(
        {
            "User-Agent": USER_AGENT,
            "Accept": "application/rss+xml, application/atom+xml, application/xml, text/xml, text/html;q=0.8, */*;q=0.5",
        }
    )
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session


def _feed_image(entry, article_url):
    media_content = entry.get("media_content") or []
    for media in media_content:
        image_url = media.get("url")
        if image_url:
            return urljoin(article_url, image_url)

    media_thumbnails = entry.get("media_thumbnail") or []
    for media in media_thumbnails:
        image_url = media.get("url")
        if image_url:
            return urljoin(article_url, image_url)

    for enclosure in entry.get("enclosures") or []:
        if "image" in enclosure.get("type", "").lower():
            image_url = enclosure.get("href") or enclosure.get("url")
            if image_url:
                return urljoin(article_url, image_url)

    summary_html = entry.get("summary", entry.get("description", ""))
    if summary_html:
        soup = BeautifulSoup(str(summary_html), "html.parser")
        image = soup.find("img", src=True)
        if image:
            return urljoin(article_url, image["src"])

    return None


def extract_image(entry, session, timeout=PAGE_TIMEOUT):
    article_url = str(entry.get("link", "")).strip()
    feed_image = _feed_image(entry, article_url)
    if feed_image:
        return feed_image

    if not article_url:
        return None

    try:
        response = session.get(article_url, timeout=timeout)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")

        image_meta = soup.find("meta", property="og:image")
        if not image_meta:
            image_meta = soup.find("meta", attrs={"name": "twitter:image"})

        if image_meta and image_meta.get("content"):
            return urljoin(article_url, image_meta["content"])
    except requests.RequestException as exc:
        logging.debug("Could not fetch og:image for %s: %s", article_url, exc)
    except Exception as exc:
        logging.debug("Could not parse og:image for %s: %s", article_url, exc)

    return None


def scrape_feeds(config_path="config.json", limit_per_feed=5):
    try:
        with open(config_path, "r", encoding="utf-8") as config_file:
            config = json.load(config_file)
    except (OSError, ValueError) as exc:
        logging.error("Failed to load config: %s", exc)
        return []

    if limit_per_feed <= 0:
        return []

    articles = []
    seen_urls = set()
    session = _build_session()

    try:
        for feed in config.get("feeds", []):
            feed_name = str(feed.get("name", "")).strip()
            feed_url = str(feed.get("url", "")).strip()
            category = str(feed.get("category", "")).strip()
            if not feed_name or not feed_url or not category:
                logging.warning("Skipping feed with missing name, URL, or category: %s", feed)
                continue

            logging.info("Fetching feed: %s (%s)", feed_name, feed_url)
            try:
                response = session.get(feed_url, timeout=FEED_TIMEOUT)
                response.raise_for_status()
                parsed = feedparser.parse(response.content)
            except requests.RequestException as exc:
                logging.error("Failed to fetch feed %s: %s", feed_name, exc)
                continue
            except Exception as exc:
                logging.error("Failed to parse feed %s: %s", feed_name, exc)
                continue

            if getattr(parsed, "bozo", False):
                logging.warning(
                    "Feed parser warning for %s: %s",
                    feed_name,
                    getattr(parsed, "bozo_exception", "unknown parse error"),
                )

            accepted = 0
            for entry in parsed.entries:
                if accepted >= limit_per_feed:
                    break

                title = clean_html(entry.get("title", ""), max_length=300)
                raw_link = str(entry.get("link", "")).strip()
                link = urljoin(feed_url, raw_link)
                normalized_link = normalize_url(link)

                if not title or not raw_link or not normalized_link:
                    logging.debug("Skipping invalid entry from %s", feed_name)
                    continue
                if normalized_link in seen_urls:
                    logging.debug("Skipping duplicate entry URL: %s", link)
                    continue

                summary = clean_html(
                    entry.get("summary", entry.get("description", "")),
                    max_length=600,
                )
                published = entry.get("published", entry.get("updated", entry.get("pubDate", "")))
                published_parsed = entry.get("published_parsed") or entry.get("updated_parsed")
                timestamp = 0
                if published_parsed:
                    try:
                        timestamp = calendar.timegm(published_parsed)
                    except (TypeError, ValueError, OverflowError):
                        logging.debug("Invalid published timestamp for %s", link)

                entry_for_image = dict(entry)
                entry_for_image["link"] = link
                image_url = extract_image(entry_for_image, session)

                articles.append(
                    {
                        "category": category,
                        "source": feed_name,
                        "title_source": title,
                        "summary_source": summary,
                        "title_ja": title,
                        "summary_ja": summary,
                        "link": link,
                        "published": published,
                        "timestamp": timestamp,
                        "image_url": image_url,
                    }
                )
                seen_urls.add(normalized_link)
                accepted += 1
    finally:
        session.close()

    return articles


if __name__ == "__main__":
    scraped_articles = scrape_feeds()
    for article in scraped_articles[:2]:
        print(article)
