import glob
import json
import logging
import os
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

from ai_curator import curate_articles
from generator import generate_html
from scraper import normalize_url, scrape_feeds


JST = timezone(timedelta(hours=9), name="JST")
DATED_DATA_RE = re.compile(r"^data-(\d{4}-\d{2}-\d{2})\.json$")


def _load_articles(path):
    with open(path, "r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, list):
        raise ValueError(f"{path} must contain a JSON array")
    return data


def _write_json_atomic(path, data):
    path = Path(path)
    temp_path = path.with_name(f".{path.name}.tmp")
    with open(temp_path, "w", encoding="utf-8", newline="\n") as handle:
        json.dump(data, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    os.replace(temp_path, path)


def _merge_by_link(*article_groups):
    merged = []
    seen = set()
    for group in article_groups:
        for article in group:
            link = (article.get("link") or "").strip()
            key = normalize_url(link) or link or f"{article.get('source', '')}\0{article.get('title_source', article.get('title_ja', ''))}"
            if key in seen:
                continue
            seen.add(key)
            merged.append(article)
    return merged


def _dated_data_files():
    dated_files = []
    for path in glob.glob("data-*.json"):
        match = DATED_DATA_RE.match(os.path.basename(path))
        if match:
            dated_files.append((match.group(1), path))
    return sorted(dated_files)


def _seen_links(exclude_path=None):
    seen = set()
    excluded = os.path.abspath(exclude_path) if exclude_path else None
    for _, path in _dated_data_files():
        if excluded and os.path.abspath(path) == excluded:
            continue
        try:
            seen.update(
                normalize_url(article.get("link")) or article.get("link")
                for article in _load_articles(path)
                if article.get("link")
            )
        except (OSError, ValueError, json.JSONDecodeError) as error:
            logging.warning("Skipping unreadable history file %s: %s", path, error)
    return seen


def generate_all_pages():
    valid_days = []
    for date_str, data_path in _dated_data_files():
        try:
            articles = _load_articles(data_path)
        except (OSError, ValueError, json.JSONDecodeError) as error:
            logging.error("Cannot generate %s: %s", data_path, error)
            continue

        archive_path = f"archive-{date_str}.html"
        generate_html(articles, archive_path, display_date=date_str)
        valid_days.append((date_str, data_path, articles))

    if not valid_days:
        raise RuntimeError("No valid dated news files are available to publish")

    latest_date, _, latest_articles = valid_days[-1]
    _write_json_atomic("data.json", latest_articles)
    generate_html(latest_articles, "index.html", display_date=latest_date)

    archive_index = [
        {
            "date": date_str,
            "page": "index.html" if date_str == latest_date else f"archive-{date_str}.html",
            "archive_page": f"archive-{date_str}.html",
            "data": os.path.basename(data_path),
            "count": len(articles),
        }
        for date_str, data_path, articles in reversed(valid_days)
    ]
    _write_json_atomic("archive-index.json", archive_index)
    logging.info("Published %d dated issues; latest is %s", len(valid_days), latest_date)


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
    logging.info("=== Global Tech News update started ===")

    today_str = datetime.now(JST).strftime("%Y-%m-%d")
    data_file = f"data-{today_str}.json"
    raw_file = f"raw-data-{today_str}.json"

    logging.info("Step 1: Fetching public news feeds...")
    crawled_articles = scrape_feeds()

    existing_raw = []
    if os.path.exists(raw_file):
        try:
            existing_raw = _load_articles(raw_file)
        except (OSError, ValueError, json.JSONDecodeError) as error:
            logging.warning("Replacing unreadable raw file %s: %s", raw_file, error)

    merged_raw = _merge_by_link(crawled_articles, existing_raw)
    _write_json_atomic(raw_file, merged_raw)
    _write_json_atomic("raw-data.json", merged_raw)
    logging.info("Saved %d crawled records to %s", len(merged_raw), raw_file)

    if not crawled_articles:
        if _dated_data_files():
            generate_all_pages()
        raise RuntimeError("No articles could be fetched from any configured feed")

    existing_today = []
    if os.path.exists(data_file):
        try:
            existing_today = _load_articles(data_file)
        except (OSError, ValueError, json.JSONDecodeError) as error:
            logging.warning("Ignoring unreadable current data file %s: %s", data_file, error)

    seen_links = _seen_links(exclude_path=data_file)
    seen_links.update(
        normalize_url(article.get("link")) or article.get("link")
        for article in existing_today
        if article.get("link")
    )
    new_articles = [
        article
        for article in crawled_articles
        if article.get("link")
        and (normalize_url(article.get("link")) or article.get("link")) not in seen_links
    ]
    logging.info("Found %d new articles after historical deduplication", len(new_articles))

    curated_new = []
    if new_articles:
        logging.info("Step 2: Translating and curating new articles...")
        curated_new = curate_articles(new_articles)
        if not curated_new:
            logging.warning("No new articles passed curation; preserving existing daily data")

    daily_articles = _merge_by_link(curated_new, existing_today)
    if daily_articles:
        _write_json_atomic(data_file, daily_articles)
        logging.info("Saved %d translated articles to %s", len(daily_articles), data_file)
    elif not _dated_data_files():
        raise RuntimeError("No translated news is available to publish")

    logging.info("Step 3: Rebuilding the latest page and all dated archives...")
    generate_all_pages()
    logging.info("=== Update complete ===")


if __name__ == "__main__":
    main()
