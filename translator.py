"""Free, best-effort translation with a small persistent cache."""

from __future__ import annotations

import atexit
import hashlib
import html
import json
import logging
import os
import re
import threading
import time
from pathlib import Path
from typing import Any, Iterable, Mapping

from deep_translator import GoogleTranslator


_CACHE_PATH = Path(__file__).resolve().with_name(".translation-cache.json")
_CACHE_LOCK = threading.RLock()
_TRANSLATOR_LOCK = threading.Lock()
_TRANSLATORS: dict[tuple[str, str], GoogleTranslator] = {}
_CACHE: dict[str, str] = {}
_CACHE_DIRTY = False

_KANA_RE = re.compile(r"[\u3040-\u30ff\u31f0-\u31ff\uff66-\uff9f]")
_CJK_RE = re.compile(r"[\u3400-\u9fff\uf900-\ufaff]")
_HANGUL_RE = re.compile(
    r"[\u1100-\u11ff\u3130-\u318f\ua960-\ua97f\uac00-\ud7a3\ud7b0-\ud7ff]"
)
_LATIN_RE = re.compile(r"[A-Za-z]")


def _load_cache() -> None:
    global _CACHE

    if not _CACHE_PATH.exists():
        return
    try:
        with _CACHE_PATH.open("r", encoding="utf-8") as cache_file:
            payload = json.load(cache_file)
        if not isinstance(payload, dict):
            raise ValueError("cache root must be an object")
        translations = payload.get("translations", payload)
        if not isinstance(translations, dict):
            raise ValueError("cache must contain an object")
        _CACHE = {
            str(key): value
            for key, value in translations.items()
            if isinstance(value, str) and value.strip()
        }
    except (OSError, ValueError, TypeError, json.JSONDecodeError) as exc:
        logging.warning("Ignoring unreadable translation cache %s: %s", _CACHE_PATH, exc)


def _cache_key(text: str, source: str, target: str) -> str:
    material = json.dumps(
        {"source": source, "target": target, "text": text},
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


def _cache_get(key: str) -> str | None:
    with _CACHE_LOCK:
        return _CACHE.get(key)


def _cache_set(key: str, value: str) -> None:
    global _CACHE_DIRTY

    with _CACHE_LOCK:
        if _CACHE.get(key) == value:
            return
        _CACHE[key] = value
        _CACHE_DIRTY = True


def flush_translation_cache() -> None:
    """Atomically persist translations collected during this process."""

    global _CACHE_DIRTY

    with _CACHE_LOCK:
        if not _CACHE_DIRTY:
            return

        temporary_path = _CACHE_PATH.with_name(
            f"{_CACHE_PATH.name}.{os.getpid()}.tmp"
        )
        try:
            with temporary_path.open("w", encoding="utf-8", newline="\n") as cache_file:
                json.dump(
                    {"version": 1, "translations": _CACHE},
                    cache_file,
                    ensure_ascii=False,
                    indent=2,
                    sort_keys=True,
                )
                cache_file.write("\n")
                cache_file.flush()
                os.fsync(cache_file.fileno())
            os.replace(temporary_path, _CACHE_PATH)
            _CACHE_DIRTY = False
        except OSError as exc:
            logging.warning("Could not save translation cache %s: %s", _CACHE_PATH, exc)
            try:
                temporary_path.unlink(missing_ok=True)
            except OSError:
                pass


def validate_translation(text: Any, target: str) -> bool:
    """Apply inexpensive script checks to translated output."""

    if not isinstance(text, str) or not text.strip():
        return False

    normalized_target = target.lower()
    if normalized_target == "en":
        return not (
            _HANGUL_RE.search(text) or _KANA_RE.search(text) or _CJK_RE.search(text)
        )
    if normalized_target == "ko":
        # Latin brand and product names are valid in Korean copy.
        return _KANA_RE.search(text) is None and _CJK_RE.search(text) is None
    return True


def _already_in_target_language(text: str, target: str) -> bool:
    if not validate_translation(text, target):
        return False
    if target == "ko":
        return _HANGUL_RE.search(text) is not None
    if target == "ja":
        return _KANA_RE.search(text) is not None
    if target == "en":
        return _LATIN_RE.search(text) is not None
    return False


def _get_translator(source: str, target: str) -> GoogleTranslator:
    key = (source, target)
    with _TRANSLATOR_LOCK:
        translator = _TRANSLATORS.get(key)
        if translator is None:
            translator = GoogleTranslator(source=source, target=target)
            _TRANSLATORS[key] = translator
        return translator


def translate_text(
    text: Any,
    source: str = "auto",
    target: str = "ko",
    max_retries: int = 3,
    initial_backoff: float = 1.0,
) -> str:
    """Translate text without an API key, returning the source on final failure."""

    if text is None:
        return ""
    source_text = str(text).strip()
    if not source_text:
        return ""

    source = (source or "auto").lower()
    target = target.lower()
    key = _cache_key(source_text, source, target)
    cached = _cache_get(key)
    if cached and validate_translation(cached, target):
        return cached

    if _already_in_target_language(source_text, target):
        _cache_set(key, source_text)
        return source_text

    attempts = max(1, int(max_retries))
    for attempt in range(attempts):
        try:
            translator = _get_translator(source, target)
            translated = translator.translate(source_text)
            if isinstance(translated, str):
                translated = html.unescape(translated).strip()
            if validate_translation(translated, target):
                _cache_set(key, translated)
                return translated
            logging.warning(
                "Translation to %s failed quality validation (attempt %s/%s)",
                target,
                attempt + 1,
                attempts,
            )
        except Exception as exc:  # deep-translator exposes several provider errors
            logging.warning(
                "Translation to %s failed (attempt %s/%s): %s",
                target,
                attempt + 1,
                attempts,
                exc,
            )

        if attempt < attempts - 1:
            time.sleep(max(0.0, initial_backoff) * (2**attempt))

    # Google occasionally leaves an entire Japanese headline untouched when
    # translating directly to Korean. An English pivot is slower, but gives
    # the free path one independent recovery route before preserving source.
    if target == "ko":
        try:
            pivot_text = _get_translator(source, "en").translate(source_text)
            translated = _get_translator("en", target).translate(pivot_text)
            if isinstance(translated, str):
                translated = html.unescape(translated).strip()
            if validate_translation(translated, target):
                _cache_set(key, translated)
                return translated
        except Exception as exc:
            logging.warning("English-pivot translation to %s failed: %s", target, exc)

    logging.error("Using source text after translation to %s failed", target)
    return source_text


def _first_text(article: Mapping[str, Any], names: Iterable[str]) -> str:
    for name in names:
        value = article.get(name)
        if value is not None and str(value).strip():
            return str(value).strip()
    return ""


def translate_article(
    article: Mapping[str, Any], force: bool = False
) -> dict[str, Any]:
    """Return an article with source text preserved and all language fields set."""

    translated_article = dict(article)
    title_source = _first_text(
        article,
        ("title_source", "title_ja", "title_en", "title_ko", "title"),
    )
    summary_source = _first_text(
        article,
        ("summary_source", "summary_ja", "summary_en", "summary_ko", "summary"),
    )

    translated_article["title_source"] = title_source
    translated_article["summary_source"] = summary_source

    title_translations_complete = all(
        validate_translation(article.get(f"title_{language}"), language)
        for language in ("en", "ja", "ko")
    )
    summary_translations_complete = all(
        validate_translation(article.get(f"summary_{language}"), language)
        for language in ("en", "ja", "ko")
    )

    for language in ("en", "ja", "ko"):
        title_field = f"title_{language}"
        summary_field = f"summary_{language}"

        if force or not title_translations_complete:
            translated_article[title_field] = translate_text(
                title_source, source="auto", target=language
            )
        if force or not summary_translations_complete:
            translated_article[summary_field] = translate_text(
                summary_source, source="auto", target=language
            )

    return translated_article


def _untranslated_fallback(article: Mapping[str, Any]) -> dict[str, Any]:
    """Preserve one malformed/failed item instead of shortening the article list."""

    fallback = dict(article)
    title_source = _first_text(
        article,
        ("title_source", "title_ja", "title_en", "title_ko", "title"),
    )
    summary_source = _first_text(
        article,
        ("summary_source", "summary_ja", "summary_en", "summary_ko", "summary"),
    )
    fallback["title_source"] = title_source
    fallback["summary_source"] = summary_source
    for language in ("en", "ja", "ko"):
        title_field = f"title_{language}"
        summary_field = f"summary_{language}"
        if not isinstance(fallback.get(title_field), str) or not fallback[title_field].strip():
            fallback[title_field] = title_source
        if (
            not isinstance(fallback.get(summary_field), str)
            or not fallback[summary_field].strip()
        ):
            fallback[summary_field] = summary_source
    return fallback


def translate_articles(
    articles: Iterable[Mapping[str, Any]], force: bool = False
) -> list[dict[str, Any]]:
    logging.info("Starting free translation of articles...")
    translated_articles: list[dict[str, Any]] = []
    try:
        for index, article in enumerate(articles, start=1):
            logging.info("Translating article %s", index)
            try:
                translated_articles.append(translate_article(article, force=force))
            except Exception:
                logging.exception(
                    "Unexpected translation failure for article %s; preserving source",
                    index,
                )
                translated_articles.append(_untranslated_fallback(article))
    finally:
        flush_translation_cache()
    return translated_articles


_load_cache()
atexit.register(flush_translation_cache)
