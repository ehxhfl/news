"""Repair incomplete or visibly mixed-language translations in saved issues."""

import json
import logging
import re

from main import _dated_data_files, _load_articles, _write_json_atomic, generate_all_pages
from translator import (
    flush_translation_cache,
    translate_text,
    validate_translation,
)


KOREAN_DISALLOWED_RE = re.compile(
    r"[\u3040-\u30ff\u31f0-\u31ff\u3400-\u9fff"
    r"\u0e00-\u0e7f\u0400-\u04ff\u0900-\u097f]"
)


def _source_text(article, kind):
    for field_name in (
        f"{kind}_source",
        f"{kind}_ja",
        f"{kind}_en",
        f"{kind}_ko",
        kind,
    ):
        value = article.get(field_name)
        if value is not None and str(value).strip():
            return str(value).strip()
    return ""


def _field_needs_repair(value, language):
    if not validate_translation(value, language):
        return True
    return language == "ko" and KOREAN_DISALLOWED_RE.search(str(value)) is not None


def _repair_article(article):
    updated = dict(article)
    changed = False

    for kind in ("title", "summary"):
        source_text = _source_text(article, kind)
        source_field = f"{kind}_source"
        if updated.get(source_field) != source_text:
            updated[source_field] = source_text
            changed = True

        for language in ("en", "ja", "ko"):
            field_name = f"{kind}_{language}"
            if _field_needs_repair(updated.get(field_name), language):
                updated[field_name] = translate_text(
                    source_text,
                    source="auto",
                    target=language,
                )
                changed = True

    return updated, changed


def repair_history():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
    repaired_articles = 0

    for date_str, file_path in _dated_data_files():
        try:
            articles = _load_articles(file_path)
        except (OSError, ValueError, json.JSONDecodeError) as error:
            logging.error("Skipping %s: %s", file_path, error)
            continue

        updated_articles = []
        repaired_for_day = 0
        for article in articles:
            updated_article, changed = _repair_article(article)
            updated_articles.append(updated_article)
            if changed:
                repaired_for_day += 1

        if repaired_for_day:
            if len(updated_articles) != len(articles):
                raise RuntimeError(f"Article count changed while repairing {file_path}")
            _write_json_atomic(file_path, updated_articles)
            logging.info("Repaired %d articles in %s", repaired_for_day, date_str)
            repaired_articles += repaired_for_day

    flush_translation_cache()
    generate_all_pages()
    logging.info("Translation repair complete: %d articles updated", repaired_articles)


if __name__ == "__main__":
    repair_history()
