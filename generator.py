import os
import glob
import hashlib
import re
from datetime import datetime
from jinja2 import Environment


DATA_FILE_RE = re.compile(r"^data-(\d{4}-\d{2}-\d{2})\.json$")
ARCHIVE_FILE_RE = re.compile(r"^archive-(\d{4}-\d{2}-\d{2})\.html$")

ENGINE_CATEGORY = "Game Engine"
VTUBER_CATEGORY = "VTuber"
COSPLAY_CATEGORY = "Cosplay/Event"

ENGINE_PATTERN = re.compile(
    r"\bunreal\s+engine\b|\bue(?:4|5|6)\b|\buefn\b|"
    r"\bunity(?:\s+(?:engine|editor|hub|release|roadmap|graphics|runtime|[0-9][0-9.]*))\b|"
    r"\bgodot(?:\s+(?:engine|[0-9][0-9.]*))?\b|\bcryengine\b|\bo3de\b|"
    r"\bopen\s+3d\s+engine\b|\bgame\s+engine\b|"
    r"게임\s*엔진|언리얼(?:\s*엔진)?|유니티(?:\s*[0-9][0-9.]*)?|"
    r"ゲームエンジン|アンリアルエンジン|ゴドーエンジン",
    re.IGNORECASE,
)
VTUBER_PATTERN = re.compile(
    r"\bvtubers?\b|\bvirtual\s+youtubers?\b|버튜버|브이튜버|"
    r"バーチャル\s*youtuber|ホロライブ|にじさんじ|\bhololive\b|\bnijisanji\b|\bvshojo\b",
    re.IGNORECASE,
)
COSPLAY_PATTERN = re.compile(
    r"\bcosplay(?:er|ers)?\b|코스프레|コスプレ|"
    r"world\s+cosplay\s+summit|世界コスプレサミット|\bacosta!?\b",
    re.IGNORECASE,
)


def discover_archives():
    """Return valid dated data files as newest-first static archive links."""
    archives = []
    for data_path in glob.glob("data-????-??-??.json"):
        filename = os.path.basename(data_path)
        match = DATA_FILE_RE.fullmatch(filename)
        if not match:
            continue

        date_str = match.group(1)
        try:
            datetime.strptime(date_str, "%Y-%m-%d")
        except ValueError:
            continue

        archives.append({
            "path": f"archive-{date_str}.html",
            "date": date_str,
        })

    return sorted(archives, key=lambda archive: archive["date"], reverse=True)


def _article_filter_text(article):
    if not isinstance(article, dict):
        return ""
    fields = (
        "source",
        "link",
        "title_source",
        "title_en",
        "title_ja",
        "title_ko",
    )
    return " ".join(str(article.get(field) or "") for field in fields)


def canonical_category(category, article=None):
    """Map current, legacy, and clearly identified article labels to filter keys."""
    value = str(category or "").strip()
    folded = value.casefold()
    article_text = _article_filter_text(article)

    legacy_engine_category = folded == "game engines"
    if folded == "game engine" or "게임 엔진" in value or (legacy_engine_category and not article_text):
        return ENGINE_CATEGORY
    if any(
        marker in article_text.casefold()
        for marker in (
            "unreal engine blog",
            "unity blog",
            "godot engine",
            "unrealengine.com",
            "unity.com/blog",
            "godotengine.org",
        )
    ) or ENGINE_PATTERN.search(article_text):
        return ENGINE_CATEGORY
    if legacy_engine_category:
        return "Game"

    if folded == "vtuber" or "버튜버" in value:
        return VTUBER_CATEGORY
    if "panora vtuber" in article_text.casefold() or VTUBER_PATTERN.search(article_text):
        return VTUBER_CATEGORY

    if folded in {"cosplay/event", "cosplay", "cosplay event"} or "코스프레" in value:
        return COSPLAY_CATEGORY
    if "japan cosplay committee" in article_text.casefold() or COSPLAY_PATTERN.search(article_text):
        return COSPLAY_CATEGORY

    if value == "AI":
        return "AI"
    if "it/tech" in folded or "it/테크" in folded:
        return "IT/Tech"
    if "cg/" in folded or "blender" in folded or "블렌더" in value:
        return "CG/Blender"
    if "anime" in folded or "애니" in value:
        return "Anime"
    if "game" in folded or "게임" in value:
        return "Game"

    return value


def display_category(article):
    original = str(article.get("category") or "").strip() if isinstance(article, dict) else ""
    canonical = canonical_category(original, article)
    if canonical in {ENGINE_CATEGORY, VTUBER_CATEGORY, COSPLAY_CATEGORY}:
        return canonical
    return original or canonical


def article_key(article):
    link = str(article.get("link") or "") if isinstance(article, dict) else ""
    return hashlib.sha256(link.encode("utf-8")).hexdigest()[:20]


def article_search_text(article):
    if not isinstance(article, dict):
        return ""
    fields = (
        canonical_category(article.get("category"), article),
        display_category(article),
        article.get("source"),
        article.get("title_en"),
        article.get("title_ja"),
        article.get("title_ko"),
        article.get("summary_en"),
        article.get("summary_ja"),
        article.get("summary_ko"),
    )
    return " ".join(" ".join(str(value or "").split()) for value in fields).casefold()


def is_cosplay_article(article):
    if not isinstance(article, dict):
        return False
    return canonical_category(article.get("category"), article) == COSPLAY_CATEGORY


HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="ko" data-theme="system">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Chunhyo Brief — Tech, Games & Culture</title>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@500;600&family=Noto+Sans+JP:wght@400;600;700&display=swap');
        @import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/static/pretendard.css');
        
        :root {
            /* Light Theme */
            --bg-color: #e9edf2;
            --text-main: #141a21;
            --text-muted: #66707b;
            --border-color: #c6ccd2;
            --nav-bg: rgba(255, 253, 247, 0.98);
            --accent: #2448ff;
            --accent-ink: #1831b5;
            --orange: #ff5a36;
            --highlight: #dfe6ff;
            --hover-bg: #f0f2f4;
            --surface-color: #fffdf7;
        }

        html {
            scrollbar-gutter: stable;
        }

        @media (prefers-color-scheme: dark) {
            :root {
                /* Premium Muted Dark Mode */
                --bg-color: #12161d;
                --text-main: #f5f0e6;
                --text-muted: #a9b0ba;
                --border-color: #454c57;
                --nav-bg: rgba(27, 32, 40, 0.98);
                --accent: #7390ff;
                --accent-ink: #a8b9ff;
                --orange: #ff7757;
                --highlight: #29345c;
                --hover-bg: #252b34;
                --surface-color: #1b2028;
            }
        }

        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }

        body {
            font-family: 'Pretendard', 'Noto Sans JP', system-ui, sans-serif;
            background-color: var(--bg-color);
            color: var(--text-main);
            line-height: 1.6;
            -webkit-font-smoothing: antialiased;
        }
        
        a {
            color: inherit;
            text-decoration: none;
        }

        .skip-link {
            position: fixed;
            left: 1rem;
            top: 1rem;
            z-index: 2000;
            padding: 0.7rem 1rem;
            background: var(--text-main);
            color: var(--bg-color);
            transform: translateY(-180%);
        }

        .skip-link:focus { transform: translateY(0); }

        /* Top Navigation */
        .navbar {
            position: sticky;
            top: 0;
            z-index: 1000;
            background: var(--nav-bg);
            backdrop-filter: blur(10px);
            -webkit-backdrop-filter: blur(10px);
            border-bottom: 1px solid var(--border-color);
            padding: 0 2rem;
            display: grid;
            gap: 0;
        }

        .nav-topline {
            min-height: 4.75rem;
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 1rem;
            border-bottom: 1px solid var(--border-color);
        }

        .brand {
            display: inline-flex;
            align-items: baseline;
            gap: 0.65rem;
            font-weight: 800;
            font-size: 1.45rem;
            letter-spacing: -0.02em;
        }

        .brand-domain,
        .nav-issue-meta {
            color: var(--text-muted);
            font-size: 0.62rem;
            font-weight: 600;
            letter-spacing: 0.2em;
            text-transform: uppercase;
        }

        .issue-number { color: var(--accent); }

        .nav-controls {
            display: flex;
            gap: 1.25rem;
            align-items: center;
            justify-content: space-between;
            flex-wrap: nowrap;
            min-width: 0;
            width: 100%;
            padding: 0.55rem 0;
        }
        
        /* Category Filter */
        .category-toggle {
            display: flex;
            gap: 0.35rem;
            font-size: 0.78rem;
            font-weight: 500;
            justify-content: flex-start;
            flex: 1 1 auto;
            flex-wrap: nowrap;
            min-width: 0;
            overflow-x: auto;
            scrollbar-width: none;
        }
        .category-toggle::-webkit-scrollbar { display: none; }
        .cat-btn {
            flex: 0 0 auto;
            cursor: pointer;
            color: var(--text-muted);
            transition: color 0.2s, border-color 0.2s, background-color 0.2s;
            border: 1px solid transparent;
            border-radius: 0;
            background: none;
            font-family: inherit;
            font-weight: 600;
            min-height: 2.75rem;
            padding: 0.45rem 0.55rem;
            white-space: nowrap;
        }
        .cat-btn.active, .cat-btn:hover {
            color: var(--text-main);
            border-bottom-color: var(--accent);
            background: transparent;
        }

        .lang-toggle {
            display: flex;
            flex: 0 0 auto;
            gap: 0.25rem;
            font-size: 0.85rem;
            font-weight: 500;
        }

        .lang-btn {
            cursor: pointer;
            color: var(--text-muted);
            transition: color 0.2s;
            border: none;
            background: none;
            font-family: inherit;
            font-weight: inherit;
            font-size: inherit;
            min-width: 2.75rem;
            min-height: 2.75rem;
        }
        .lang-btn:hover { color: var(--text-main); }
        .lang-btn.active { color: var(--text-main); font-weight: 700; }

        .archive-dropdown {
            display: flex;
            align-items: center;
            gap: 0.5rem;
            font-size: 0.85rem;
            font-weight: 500;
            color: var(--text-main);
        }
        
        .archive-dropdown select {
            background: var(--bg-color);
            border: 1px solid var(--border-color);
            border-radius: 0;
            color: var(--text-main);
            font-family: inherit;
            font-size: inherit;
            font-weight: inherit;
            cursor: pointer;
            outline: none;
            padding: 0.4rem 1.8rem 0.4rem 0.6rem;
        }

        .archive-dropdown select:focus-visible,
        .issue-link:focus-visible,
        .cat-btn:focus-visible,
        .lang-btn:focus-visible,
        .search-field input:focus-visible,
        .saved-filter:focus-visible,
        .interaction-btn:focus-visible,
        .reset-filter:focus-visible {
            outline: 2px solid var(--accent);
            outline-offset: 2px;
        }

        .issue-navigation {
            display: flex;
            flex: 0 0 auto;
            align-items: center;
            justify-content: center;
            flex-wrap: nowrap;
            gap: 0.75rem;
        }

        .issue-link {
            display: inline-flex;
            align-items: center;
            gap: 0.3rem;
            border: 1px solid var(--border-color);
            border-radius: 0;
            padding: 0.35rem 0.7rem;
            color: var(--text-muted);
            font-size: 0.78rem;
            white-space: nowrap;
            transition: color 0.2s, border-color 0.2s, background-color 0.2s;
        }

        .issue-link:hover,
        .issue-link[aria-current="page"] {
            color: var(--text-main);
            border-color: var(--text-muted);
            background: var(--hover-bg);
        }

        /* Container */
        .container {
            max-width: 1400px;
            margin: 0 auto;
            padding: 2rem;
        }

        /* Editorial issue masthead */
        .editorial-masthead {
            margin-bottom: 2rem;
            border-bottom: 1px solid var(--text-main);
        }

        .masthead-kicker {
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 1rem;
            padding: 2.25rem 0 1.25rem;
            color: var(--text-muted);
            font-size: 0.72rem;
            font-weight: 600;
            letter-spacing: 0.16em;
            text-transform: uppercase;
        }

        .masthead-kicker::before {
            content: '';
            width: 0.45rem;
            height: 0.45rem;
            flex: 0 0 auto;
            background: var(--accent);
        }

        .masthead-kicker time { margin-left: auto; font-variant-numeric: tabular-nums; }

        .masthead-row {
            display: grid;
            grid-template-columns: minmax(0, 1fr) auto;
            gap: 2rem;
            align-items: end;
            padding: 1rem 0 1.75rem;
            border-bottom: 1px solid var(--text-main);
        }

        .masthead-title {
            max-width: 13ch;
            font-size: clamp(3rem, 8vw, 7.5rem);
            font-weight: 800;
            line-height: 0.88;
            letter-spacing: -0.075em;
            text-wrap: balance;
        }

        .guide-link {
            display: inline-flex;
            align-items: center;
            gap: 0.8rem;
            min-height: 3rem;
            padding: 0.7rem 0.9rem;
            border: 1px solid var(--text-main);
            font-size: 0.78rem;
            font-weight: 700;
            letter-spacing: 0.06em;
            text-transform: uppercase;
            transition: background-color 0.2s, color 0.2s;
        }

        .guide-link:hover { background: var(--text-main); color: var(--bg-color); }

        .masthead-summary {
            display: grid;
            grid-template-columns: minmax(16rem, 0.8fr) minmax(0, 1.2fr);
            gap: 2rem;
            align-items: start;
            padding: 1.75rem 0;
        }

        .masthead-copy {
            max-width: 42rem;
            color: var(--text-muted);
            font-size: 0.94rem;
        }

        .masthead-copy strong { color: var(--accent); font-family: 'Newsreader', serif; font-size: 1.35rem; font-style: italic; font-weight: 500; }

        .masthead-metrics {
            display: grid;
            grid-template-columns: minmax(0, 3fr) minmax(12rem, 2fr);
            gap: 1.25rem;
        }

        .digest-stats,
        .daily-traffic {
            display: grid;
            gap: 0.75rem;
            margin: 0;
        }

        .digest-stats { grid-template-columns: repeat(3, minmax(0, 1fr)); }

        .daily-traffic {
            grid-template-columns: repeat(2, minmax(0, 1fr));
        }

        .digest-stats > div,
        .daily-traffic > div {
            min-inline-size: 0;
            padding-left: 0.75rem;
            border-left: 1px solid var(--border-color);
        }

        .digest-stats dt,
        .daily-traffic dt {
            color: var(--text-muted);
            font-size: 0.68rem;
            line-height: 1.2;
            white-space: nowrap;
        }

        .digest-stats dd,
        .daily-traffic dd {
            min-block-size: 1.3em;
            color: var(--text-main);
            font-size: 1.4rem;
            font-weight: 800;
            line-height: 1.3;
            font-variant-numeric: tabular-nums;
        }

        .discovery-panel {
            display: grid;
            grid-template-columns: minmax(18rem, 1fr) auto;
            gap: 0.75rem 1rem;
            align-items: center;
            margin: 0 0 1rem;
            padding: 0.85rem;
            border: 1px solid var(--border-color);
            border-radius: 0;
            background: var(--surface-color);
        }

        .search-field {
            position: relative;
            display: block;
            min-width: 0;
        }

        .search-field svg {
            position: absolute;
            left: 0.9rem;
            top: 50%;
            width: 1.1rem;
            height: 1.1rem;
            color: var(--text-muted);
            transform: translateY(-50%);
            pointer-events: none;
        }

        .search-field input {
            width: 100%;
            min-height: 3rem;
            padding: 0.7rem 1rem 0.7rem 2.75rem;
            border: 1px solid var(--border-color);
            border-radius: 0;
            background: var(--surface-color);
            color: var(--text-main);
            font: inherit;
            font-size: 0.92rem;
        }

        .search-field input::placeholder { color: var(--text-muted); }

        .saved-filter {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            gap: 0.5rem;
            min-height: 3rem;
            padding: 0.65rem 0.9rem;
            border: 1px solid var(--border-color);
            border-radius: 0;
            background: var(--surface-color);
            color: var(--text-main);
            cursor: pointer;
            font: inherit;
            font-size: 0.82rem;
            font-weight: 700;
        }

        .saved-filter svg { width: 1rem; height: 1rem; fill: none; stroke: currentColor; stroke-width: 1.8; }
        .saved-filter[aria-pressed="true"] { border-color: var(--text-main); background: var(--text-main); color: var(--bg-color); }
        .saved-filter-count { min-width: 1.5rem; border-radius: 999px; padding: 0.05rem 0.4rem; background: var(--hover-bg); color: var(--text-main); font-variant-numeric: tabular-nums; }
        .saved-filter[aria-pressed="true"] .saved-filter-count { background: var(--bg-color); }

        .results-status {
            grid-column: 1 / -1;
            display: flex;
            align-items: center;
            justify-content: space-between;
            min-height: 1.25rem;
            color: var(--text-muted);
            font-size: 0.75rem;
        }

        .reset-filter {
            border: 0;
            background: none;
            color: var(--text-main);
            cursor: pointer;
            font: inherit;
            font-weight: 700;
            text-decoration: underline;
            text-underline-offset: 0.18rem;
        }

        .field-note {
            display: grid;
            grid-template-columns: auto minmax(0, 1fr) auto;
            gap: 1.25rem;
            align-items: center;
            margin: 0 0 2.5rem;
            padding: 1rem 1.1rem;
            border: 1px solid var(--border-color);
            border-left: 0.35rem solid var(--accent);
            background: var(--surface-color);
        }

        .field-note-label {
            color: var(--accent);
            font-size: 0.67rem;
            font-weight: 800;
            letter-spacing: 0.14em;
            text-transform: uppercase;
        }

        .field-note h2 { margin-bottom: 0.1rem; font-size: 1rem; }
        .field-note p { color: var(--text-muted); font-size: 0.82rem; }
        .field-note a { min-height: 2.75rem; display: inline-flex; align-items: center; font-size: 0.78rem; font-weight: 700; text-decoration: underline; text-underline-offset: 0.2rem; }

        /* Featured Article */
        .featured {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 3rem;
            margin-bottom: 4rem;
            padding-bottom: 4rem;
            border-bottom: 1px solid var(--border-color);
        }

        .featured-img {
            width: 100%;
            height: 100%;
            min-height: 400px;
            object-fit: cover;
            background: var(--hover-bg);
        }

        .featured-content {
            display: flex;
            flex-direction: column;
            justify-content: center;
        }

        .meta {
            font-size: 0.8rem;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            color: var(--text-muted);
            margin-bottom: 1rem;
            display: flex;
            gap: 1rem;
        }

        .featured-title {
            font-size: 3rem;
            font-weight: 700;
            line-height: 1.1;
            letter-spacing: -0.03em;
            margin-bottom: 1.5rem;
        }
        
        .featured-title a:hover {
            text-decoration: underline;
        }

        .featured-summary {
            font-size: 1.1rem;
            color: var(--text-muted);
            line-height: 1.6;
        }

        /* Masonry Grid Layout */
        .masonry-grid {
            column-count: 3;
            column-gap: 2rem;
            width: 100%;
        }

        .article-card {
            break-inside: avoid;
            margin-bottom: 3rem;
            padding-bottom: 2rem;
            border-bottom: 1px solid var(--border-color);
        }

        .article-card[hidden], .no-results[hidden] { display: none !important; }

        .article-img {
            width: 100%;
            height: auto;
            margin-bottom: 1rem;
            background: var(--hover-bg);
        }

        .article-placeholder {
            aspect-ratio: 16 / 9;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            overflow: hidden;
            color: #ffffff;
            text-align: center;
            letter-spacing: 0.08em;
        }

        .article-placeholder[hidden] { display: none; }

        .cosplay-placeholder {
            background: var(--accent);
        }

        .placeholder-kicker {
            font-size: 0.72rem;
            font-weight: 600;
        }

        .placeholder-title {
            font-size: clamp(1.35rem, 4vw, 2.5rem);
            font-weight: 700;
            line-height: 1;
        }

        .article-title {
            font-size: 1.4rem;
            font-weight: 600;
            line-height: 1.25;
            letter-spacing: -0.02em;
            margin-bottom: 0.75rem;
        }
        
        .article-title a:hover {
            text-decoration: underline;
        }

        .article-summary {
            font-size: 0.95rem;
            color: var(--text-muted);
            line-height: 1.5;
            display: -webkit-box;
            overflow: hidden;
            -webkit-box-orient: vertical;
            -webkit-line-clamp: 5;
        }

        .article-actions {
            display: flex;
            align-items: center;
            flex-wrap: wrap;
            gap: 0.5rem;
            margin-top: 1rem;
        }

        .interaction-btn {
            min-height: 2.1rem;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            gap: 0.35rem;
            border: 1px solid var(--border-color);
            border-radius: 999px;
            background: var(--bg-color);
            color: var(--text-muted);
            cursor: pointer;
            font-family: inherit;
            font-size: 0.78rem;
            font-weight: 600;
            padding: 0.35rem 0.7rem;
            transition: color 0.2s, border-color 0.2s, background-color 0.2s;
        }

        .interaction-btn:hover {
            color: var(--text-main);
            border-color: var(--text-muted);
            background: var(--hover-bg);
        }

        .like-btn[aria-pressed="true"] {
            color: #d13b66;
            border-color: rgba(209, 59, 102, 0.45);
            background: rgba(209, 59, 102, 0.08);
        }

        .save-btn svg { width: 0.95rem; height: 0.95rem; fill: none; stroke: currentColor; stroke-width: 1.8; }
        .save-btn[aria-pressed="true"] { color: var(--text-main); border-color: var(--text-main); background: var(--hover-bg); }
        .save-btn[aria-pressed="true"] svg { fill: currentColor; }
        .save-btn[aria-pressed="false"] .save-active.lang-content { display: none; }
        .save-btn[aria-pressed="true"] .save-default.lang-content { display: none; }

        .interaction-btn:disabled {
            cursor: wait;
            opacity: 0.65;
        }

        .like-count {
            min-width: 1.4ch;
            text-align: right;
            font-variant-numeric: tabular-nums;
        }

        .empty-state {
            border: 1px solid var(--border-color);
            background: var(--hover-bg);
            padding: 4rem 2rem;
            text-align: center;
        }

        .empty-state h1 {
            font-size: 1.75rem;
            margin-bottom: 0.75rem;
        }

        .empty-state p {
            color: var(--text-muted);
        }

        .no-results { margin: 1rem 0 4rem; border: 1px solid var(--border-color); border-radius: 1rem; background: var(--hover-bg); padding: 4rem 2rem; text-align: center; }
        .no-results svg { width: 2rem; height: 2rem; margin-bottom: 1rem; color: var(--text-muted); fill: none; stroke: currentColor; stroke-width: 1.5; }
        .no-results h2 { margin-bottom: 0.5rem; font-size: 1.35rem; }
        .no-results p { margin-bottom: 1rem; color: var(--text-muted); }

        @media (max-width: 1024px) {
            .masonry-grid { column-count: 2; }
            .featured { grid-template-columns: 1fr; gap: 2rem; }
            .featured-img { min-height: 300px; }
            .featured-title { font-size: 2.5rem; }
            .masthead-summary { grid-template-columns: 1fr; }
        }

        @media (max-width: 640px) {
            .masonry-grid { column-count: 1; }
            .navbar { padding: 0 1rem; }
            .nav-topline { min-height: 4rem; flex-wrap: wrap; gap: 0.5rem; padding: 0.75rem 0; }
            .brand { width: 100%; font-size: 1.2rem; white-space: nowrap; }
            .brand-domain { display: none; }
            .nav-issue-meta { display: none; }
            .nav-topline .issue-navigation { width: 100%; justify-content: flex-start; }
            .nav-topline .issue-link:not([aria-current="page"]) { display: none; }
            .nav-controls { width: 100%; justify-content: center; gap: 0.75rem; flex-direction: column; flex-wrap: nowrap; }
            .category-toggle {
                width: 100%;
                gap: 0.5rem;
                justify-content: flex-start;
                flex-wrap: nowrap;
                overflow-x: auto;
                overscroll-behavior-x: contain;
                scrollbar-width: none;
                -webkit-overflow-scrolling: touch;
            }
            .category-toggle::-webkit-scrollbar { display: none; }
            .issue-navigation { width: 100%; }
            .masthead-kicker { align-items: flex-start; padding-top: 1.5rem; letter-spacing: 0.1em; }
            .masthead-row { grid-template-columns: 1fr; gap: 1.25rem; }
            .masthead-title { font-size: clamp(3rem, 16vw, 5rem); }
            .guide-link { width: 100%; justify-content: space-between; }
            .masthead-summary { grid-template-columns: 1fr; }
            .masthead-metrics { grid-template-columns: 1fr; }
            .field-note { grid-template-columns: 1fr; gap: 0.4rem; }
            .featured-img { min-height: 200px; }
            .featured-title { font-size: 2rem; }
            .container { padding: 1rem; }
            .discovery-panel { grid-template-columns: 1fr; margin-top: 0; }
            .saved-filter { width: 100%; }
        }

        @media (prefers-reduced-motion: reduce) {
            *, *::before, *::after {
                scroll-behavior: auto !important;
                transition-duration: 0.01ms !important;
                animation-duration: 0.01ms !important;
                animation-iteration-count: 1 !important;
            }
        }

        /* Chunhyo Feed — two-colour personal newsboard */
        body {
            border-top: 5px solid var(--accent);
            word-break: keep-all;
        }

        .navbar {
            padding: 0 clamp(1rem, 3vw, 2.5rem);
            background: var(--nav-bg);
            backdrop-filter: none;
            -webkit-backdrop-filter: none;
            border-bottom: 2px solid var(--text-main);
        }

        .nav-topline,
        .nav-controls {
            width: min(100%, 1320px);
            margin-inline: auto;
        }

        .nav-topline {
            min-height: 4.5rem;
            border-bottom: 1px solid var(--border-color);
        }

        .brand {
            gap: 0.75rem;
            font-size: 1rem;
            letter-spacing: 0;
        }

        .brand > span:first-child {
            display: inline-grid;
            place-items: center;
            min-height: 2.6rem;
            padding: 0.2rem 0.65rem;
            background: var(--accent);
            color: #fff;
            font-family: 'IBM Plex Mono', monospace;
            font-size: 1rem;
            font-weight: 600;
            letter-spacing: 0.02em;
        }

        .brand-domain,
        .nav-issue-meta {
            font-family: 'IBM Plex Mono', monospace;
            letter-spacing: 0.08em;
        }

        .brand-domain {
            max-width: 10rem;
            line-height: 1.25;
        }

        .issue-number { color: var(--orange); }

        .nav-controls {
            min-height: 3.4rem;
            padding: 0;
        }

        .category-toggle {
            align-self: stretch;
            gap: 0;
            border-left: 1px solid var(--border-color);
        }

        .cat-btn {
            min-height: 3.35rem;
            padding: 0.45rem 0.7rem;
            border: 0;
            border-right: 1px solid var(--border-color);
            font-family: 'IBM Plex Mono', monospace;
            font-size: 0.7rem;
            letter-spacing: -0.02em;
        }

        .cat-btn.active,
        .cat-btn:hover {
            border-bottom-color: transparent;
            background: var(--accent);
            color: #fff;
        }

        .lang-toggle {
            gap: 0;
            border: 1px solid var(--text-main);
        }

        .lang-btn {
            min-width: 2.6rem;
            min-height: 2.35rem;
            font-family: 'IBM Plex Mono', monospace;
            font-size: 0.72rem;
        }

        .lang-btn + .lang-btn { border-left: 1px solid var(--text-main); }
        .lang-btn.active { background: var(--text-main); color: var(--surface-color); }

        .archive-dropdown select,
        .issue-link {
            border-color: var(--text-main);
            background: var(--surface-color);
            font-family: 'IBM Plex Mono', monospace;
            font-size: 0.7rem;
        }

        .issue-link[aria-current="page"] {
            background: var(--orange);
            border-color: var(--orange);
            color: #fff;
        }

        .container {
            max-width: 1320px;
            padding: 2rem clamp(1rem, 3vw, 2.5rem) 5rem;
        }

        .editorial-masthead {
            margin: 0 0 1.5rem;
            border: 2px solid var(--text-main);
            background: var(--surface-color);
        }

        .masthead-kicker {
            min-height: 2.7rem;
            justify-content: flex-start;
            padding: 0.55rem 0.9rem;
            background: var(--accent);
            color: #fff;
            font-family: 'IBM Plex Mono', monospace;
            font-size: 0.68rem;
            letter-spacing: 0.08em;
        }

        .masthead-kicker::before {
            width: 0.55rem;
            height: 0.55rem;
            background: var(--orange);
        }

        .masthead-kicker time { margin-left: auto; }

        .masthead-row {
            grid-template-columns: minmax(0, 1fr) auto;
            align-items: center;
            gap: 1.5rem;
            padding: 1.4rem;
            border-bottom: 1px solid var(--text-main);
        }

        .masthead-title {
            max-width: 16ch;
            font-family: 'Pretendard', 'Noto Sans JP', sans-serif;
            font-size: clamp(2.8rem, 6.5vw, 5.8rem);
            font-weight: 800;
            line-height: 0.93;
            letter-spacing: -0.07em;
        }

        .guide-link {
            min-height: 3rem;
            padding: 0.7rem 0.9rem;
            border: 2px solid var(--text-main);
            background: var(--highlight);
            color: var(--text-main);
            font-family: 'IBM Plex Mono', monospace;
            font-size: 0.68rem;
            letter-spacing: 0.02em;
        }

        .guide-link:hover { background: var(--orange); color: #fff; }

        .masthead-summary {
            grid-template-columns: minmax(15rem, 0.75fr) minmax(0, 1.25fr);
            gap: 1.5rem;
            padding: 1.4rem;
        }

        .masthead-copy { font-size: 0.9rem; }

        .masthead-copy strong {
            display: block;
            margin-bottom: 0.35rem;
            color: var(--orange);
            font-family: 'IBM Plex Mono', monospace;
            font-size: 0.7rem;
            font-style: normal;
            font-weight: 600;
            letter-spacing: 0.06em;
            text-transform: uppercase;
        }

        .masthead-metrics { gap: 0.5rem; }
        .digest-stats, .daily-traffic { gap: 0; }

        .digest-stats > div,
        .daily-traffic > div {
            padding: 0.65rem 0.75rem;
            border: 1px solid var(--border-color);
            border-left: 0;
            background: var(--bg-color);
        }

        .digest-stats > div:first-child,
        .daily-traffic > div:first-child { border-left: 1px solid var(--border-color); }

        .digest-stats dt,
        .daily-traffic dt {
            font-family: 'IBM Plex Mono', monospace;
            font-size: 0.62rem;
            letter-spacing: 0.02em;
        }

        .digest-stats dd,
        .daily-traffic dd {
            font-family: 'IBM Plex Mono', monospace;
            font-size: 1.3rem;
        }

        .discovery-panel {
            margin: 0 0 1.5rem;
            padding: 0.7rem 0;
            border: 0;
            border-top: 2px solid var(--text-main);
            border-bottom: 2px solid var(--text-main);
            background: transparent;
        }

        .search-field input,
        .saved-filter {
            border: 1px solid var(--text-main);
            background: var(--surface-color);
            border-radius: 0;
        }

        .saved-filter {
            font-family: 'IBM Plex Mono', monospace;
            font-size: 0.72rem;
        }

        .saved-filter[aria-pressed="true"] {
            border-color: var(--accent);
            background: var(--accent);
            color: #fff;
        }

        .saved-filter-count,
        .saved-filter[aria-pressed="true"] .saved-filter-count {
            border-radius: 0;
            background: var(--highlight);
            color: var(--text-main);
        }

        .results-status { font-family: 'IBM Plex Mono', monospace; }

        .field-note {
            margin-bottom: 2rem;
            padding: 0.9rem 1rem;
            border: 1px solid var(--text-main);
            border-left: 6px solid var(--orange);
            background: var(--surface-color);
        }

        .field-note-label {
            color: var(--orange);
            font-family: 'IBM Plex Mono', monospace;
        }

        .featured {
            position: relative;
            grid-template-columns: minmax(0, 7fr) minmax(20rem, 5fr);
            gap: 0;
            margin: 0 0 2.5rem;
            padding: 0;
            border: 2px solid var(--text-main);
            background: var(--surface-color);
        }

        .featured::before {
            content: 'LEAD / 01';
            position: absolute;
            top: 0;
            left: 0;
            z-index: 2;
            padding: 0.35rem 0.55rem;
            background: var(--orange);
            color: #fff;
            font-family: 'IBM Plex Mono', monospace;
            font-size: 0.65rem;
            font-weight: 600;
            letter-spacing: 0.06em;
        }

        .featured-img {
            min-height: 430px;
            aspect-ratio: 5 / 3;
            border-right: 2px solid var(--text-main);
            background: var(--highlight);
        }

        .featured-content {
            align-items: flex-start;
            padding: clamp(1.5rem, 3vw, 2.6rem);
        }

        .meta {
            align-items: center;
            gap: 0.55rem;
            margin-bottom: 0.8rem;
            font-family: 'IBM Plex Mono', monospace;
            font-size: 0.66rem;
            letter-spacing: 0.02em;
        }

        .meta > span:first-child {
            padding: 0.18rem 0.35rem;
            background: var(--accent);
            color: #fff;
        }

        .featured-title {
            font-size: clamp(2rem, 3.3vw, 3.4rem);
            font-weight: 800;
            line-height: 1.06;
            letter-spacing: -0.045em;
        }

        .featured-title a:hover,
        .article-title a:hover {
            text-decoration-color: var(--orange);
            text-decoration-thickness: 0.15em;
            text-underline-offset: 0.12em;
        }

        .featured-summary { font-size: 1rem; }

        .masonry-grid {
            display: grid;
            grid-template-columns: repeat(3, minmax(0, 1fr));
            gap: 0;
            width: 100%;
            border-top: 2px solid var(--text-main);
            border-left: 2px solid var(--text-main);
            counter-reset: story 1;
            column-count: initial;
        }

        .masonry-grid .article-card {
            position: relative;
            display: flex;
            min-width: 0;
            min-height: 100%;
            flex-direction: column;
            margin: 0;
            padding: 1.15rem;
            border: 0;
            border-right: 2px solid var(--text-main);
            border-bottom: 2px solid var(--text-main);
            background: var(--surface-color);
            counter-increment: story;
        }

        .masonry-grid .article-card::before {
            content: counter(story, decimal-leading-zero);
            align-self: flex-start;
            margin-bottom: 0.65rem;
            padding-bottom: 0.2rem;
            border-bottom: 3px solid var(--orange);
            color: var(--text-main);
            font-family: 'IBM Plex Mono', monospace;
            font-size: 0.7rem;
            font-weight: 600;
        }

        .masonry-grid .article-card:hover { background: var(--highlight); }

        .article-img {
            aspect-ratio: 5 / 3;
            margin-bottom: 0.9rem;
            border: 1px solid var(--text-main);
            object-fit: cover;
        }

        .cosplay-placeholder {
            background: var(--accent);
            color: #fff;
        }

        .placeholder-kicker { font-family: 'IBM Plex Mono', monospace; }

        .placeholder-title {
            max-width: 8ch;
            font-size: clamp(1.2rem, 3vw, 2rem);
            letter-spacing: -0.04em;
        }

        .article-title {
            font-size: 1.25rem;
            font-weight: 700;
            line-height: 1.3;
            letter-spacing: -0.025em;
        }

        .article-summary {
            -webkit-line-clamp: 4;
            font-size: 0.88rem;
        }

        .article-actions { margin-top: auto; padding-top: 1rem; }

        .interaction-btn {
            min-height: 2rem;
            padding: 0.25rem 0;
            border: 0;
            border-bottom: 1px solid var(--text-muted);
            border-radius: 0;
            background: transparent;
            font-family: 'IBM Plex Mono', monospace;
            font-size: 0.68rem;
        }

        .interaction-btn:hover {
            border-color: var(--accent);
            background: transparent;
            color: var(--accent);
        }

        .like-btn[aria-pressed="true"] {
            border-color: var(--orange);
            background: transparent;
            color: var(--orange);
        }

        .save-btn[aria-pressed="true"] {
            border-color: var(--accent);
            background: transparent;
            color: var(--accent);
        }

        .empty-state,
        .no-results {
            border: 2px solid var(--text-main);
            border-radius: 0;
            background: var(--surface-color);
        }

        @media (max-width: 1050px) {
            .masonry-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
            .featured { grid-template-columns: 1fr; }
            .featured-img { min-height: 300px; border-right: 0; border-bottom: 2px solid var(--text-main); }
            .masthead-summary { grid-template-columns: 1fr; }
        }

        @media (max-width: 720px) {
            body { border-top-width: 4px; }
            .navbar { padding: 0 0.8rem; }
            .nav-topline {
                display: grid;
                grid-template-columns: minmax(0, 1fr) auto;
                min-height: 0;
                gap: 0.65rem;
                padding: 0.65rem 0;
            }
            .brand { width: auto; min-width: 0; }
            .brand > span:first-child { min-height: 2.3rem; }
            .brand-domain { display: block; }
            .nav-issue-meta { display: none; }
            .nav-topline .issue-navigation { width: auto; min-width: 0; justify-content: flex-end; }
            .nav-topline .issue-link:not([aria-current="page"]) { display: none; }
            .archive-dropdown label { display: none; }
            .archive-dropdown select { width: min(8.5rem, 34vw); }
            .nav-controls { flex-direction: column; align-items: stretch; gap: 0.35rem; padding: 0.35rem 0 0.55rem; }
            .category-toggle { width: 100%; min-height: 3rem; }
            .cat-btn { min-height: 3rem; scroll-snap-align: start; }
            .lang-toggle { align-self: flex-end; }
            .container { padding: 1rem 0.8rem 3rem; }
            .masthead-row { grid-template-columns: 1fr; align-items: start; padding: 1rem; }
            .masthead-title { font-size: clamp(2.8rem, 14vw, 4.5rem); }
            .guide-link { width: 100%; justify-content: space-between; }
            .masthead-summary { padding: 1rem; }
            .masthead-metrics { grid-template-columns: 1fr; }
            .field-note { grid-template-columns: 1fr; }
            .featured-content { padding: 1.25rem; }
        }

        @media (max-width: 620px) {
            .masonry-grid { grid-template-columns: 1fr; }
            .discovery-panel { grid-template-columns: 1fr; }
            .saved-filter { width: 100%; }
            .masthead-kicker { align-items: center; padding-top: 0.55rem; }
            .masthead-title { max-width: 10ch; }
            .featured-title { font-size: 2rem; }
            .featured-img { min-height: 230px; }
        }
        
        /* Language System */
        .lang-content { display: none; }
        html[lang="en"] .lang-en { display: block; }
        html[lang="ja"] .lang-ja { display: block; }
        html[lang="ko"] .lang-ko { display: block; }
        
        /* Inline language display for meta */
        html[lang="en"] span.lang-en { display: inline; }
        html[lang="ja"] span.lang-ja { display: inline; }
        html[lang="ko"] span.lang-ko { display: inline; }

    </style>
</head>
<body>

    <a class="skip-link" href="#main-content">
        <span class="lang-content lang-en">Skip to stories</span>
        <span class="lang-content lang-ja">記事へ移動</span>
        <span class="lang-content lang-ko">기사로 바로가기</span>
    </a>

    <nav class="navbar">
        <div class="nav-topline">
            <a class="brand" href="index.html">
                <span>CHUNHYO</span>
                <span class="brand-domain">DAILY FEED · 10:00</span>
            </a>
            <div class="issue-navigation" aria-label="Issue navigation">
                <a class="issue-link" href="index.html" {% if is_latest_page %}aria-current="page"{% endif %}>
                    <span class="lang-content lang-en">Latest</span>
                    <span class="lang-content lang-ja">最新</span>
                    <span class="lang-content lang-ko">최신</span>
                </a>
                {% if older_archive %}
                <a class="issue-link" href="{{ older_archive.path }}">
                    <span aria-hidden="true">&larr;</span>
                    <span class="lang-content lang-en">Older</span>
                    <span class="lang-content lang-ja">前の日</span>
                    <span class="lang-content lang-ko">이전 날짜</span>
                    <time datetime="{{ older_archive.date }}">{{ older_archive.date }}</time>
                </a>
                {% endif %}
                {% if newer_archive %}
                <a class="issue-link" href="{{ newer_archive.path }}">
                    <span class="lang-content lang-en">Newer</span>
                    <span class="lang-content lang-ja">次の日</span>
                    <span class="lang-content lang-ko">다음 날짜</span>
                    <time datetime="{{ newer_archive.date }}">{{ newer_archive.date }}</time>
                    <span aria-hidden="true">&rarr;</span>
                </a>
                {% endif %}
                <div class="archive-dropdown">
                    <label for="archive-select">
                        <span class="lang-content lang-en">Date</span>
                        <span class="lang-content lang-ja">日付</span>
                        <span class="lang-content lang-ko">날짜</span>
                    </label>
                    <select id="archive-select" onchange="if (this.value) window.location.href=this.value">
                        <option value="index.html" {% if is_latest_page %}selected{% endif %}>Latest / 最新 / 최신</option>
                        {% for arc in archives %}
                        <option value="{{ arc.path }}" {% if not is_latest_page and arc.date == selected_date %}selected{% endif %}>{{ arc.date }}</option>
                        {% endfor %}
                    </select>
                </div>
            </div>
            <p class="nav-issue-meta">
                <span class="issue-number">№ {{ "%03d"|format(issue_number) }}</span>
                <span aria-hidden="true"> · </span>
                <span>{{ date }}</span>
                <span aria-hidden="true"> · </span>
                <span>DAILY ARCHIVE</span>
            </p>
        </div>
        <div class="nav-controls">
            <div class="category-toggle">
                <button class="cat-btn active" onclick="setCategory('All')" id="cat-All">All</button>
                <button class="cat-btn" onclick="setCategory('IT/Tech')" id="cat-IT/Tech">IT/Tech</button>
                <button class="cat-btn" onclick="setCategory('AI')" id="cat-AI">AI</button>
                <button class="cat-btn" onclick="setCategory('Game Engine')" id="cat-Game Engine">Game Engine</button>
                <button class="cat-btn" onclick="setCategory('Game')" id="cat-Game">Game</button>
                <button class="cat-btn" onclick="setCategory('VTuber')" id="cat-VTuber">VTuber</button>
                <button class="cat-btn" onclick="setCategory('Anime')" id="cat-Anime">Anime</button>
                <button class="cat-btn" onclick="setCategory('Cosplay/Event')" id="cat-Cosplay/Event">Cosplay/Event</button>
                <button class="cat-btn" onclick="setCategory('CG/Blender')" id="cat-CG/Blender">CG/Blender</button>
            </div>
            <div class="lang-toggle">
                <button class="lang-btn" onclick="setLanguage('en')" id="btn-en">EN</button>
                <button class="lang-btn" onclick="setLanguage('ja')" id="btn-ja">JA</button>
                <button class="lang-btn active" onclick="setLanguage('ko')" id="btn-ko">KO</button>
            </div>
        </div>
    </nav>

    <main class="container" id="main-content">
        <header class="editorial-masthead">
            <div class="masthead-kicker">
                <span>COLLECTED DAILY · 10:00 JST / KST</span>
                <time datetime="{{ date }}">{{ date }}</time>
            </div>
            <div class="masthead-row">
                <h1 class="masthead-title" id="digest-title">
                    <span class="lang-content lang-en">WHAT CAME IN TODAY</span>
                    <span class="lang-content lang-ja">今日届いたもの</span>
                    <span class="lang-content lang-ko">오늘 들어온 것들</span>
                </h1>
                <a class="guide-link" href="#lead-story">
                    <span class="lang-content lang-en">Start reading</span>
                    <span class="lang-content lang-ja">記事を見る</span>
                    <span class="lang-content lang-ko">첫 기사 보기</span>
                    <span aria-hidden="true">↓</span>
                </a>
            </div>
            <div class="masthead-summary">
                <p class="masthead-copy">
                    <strong>
                        <span class="lang-content lang-en">Morning edition</span>
                        <span class="lang-content lang-ja">朝刊</span>
                        <span class="lang-content lang-ko">아침판</span>
                    </strong><br>
                    <span class="lang-content lang-en">Tech, AI, games and digital culture, collected every morning and arranged in three languages.</span>
                    <span class="lang-content lang-ja">テクノロジー、AI、ゲーム、デジタル文化の話題を毎朝集め、3言語で整理します。</span>
                    <span class="lang-content lang-ko">테크·AI·게임·디지털 문화 소식을 매일 아침 모아 세 언어로 정리합니다.</span>
                </p>
                <div class="masthead-metrics">
                    <dl class="digest-stats">
                        <div>
                            <dt><span class="lang-content lang-en">Stories</span><span class="lang-content lang-ja">記事</span><span class="lang-content lang-ko">기사</span></dt>
                            <dd>{{ article_count }}</dd>
                        </div>
                        <div>
                            <dt><span class="lang-content lang-en">Sources</span><span class="lang-content lang-ja">媒体</span><span class="lang-content lang-ko">출처</span></dt>
                            <dd>{{ source_count }}</dd>
                        </div>
                        <div>
                            <dt><span class="lang-content lang-en">Topics</span><span class="lang-content lang-ja">分野</span><span class="lang-content lang-ko">주제</span></dt>
                            <dd>{{ category_count }}</dd>
                        </div>
                    </dl>
                    <dl id="daily-traffic" class="daily-traffic" aria-live="polite" aria-busy="true" data-state="loading">
                        <div>
                            <dt><span class="lang-content lang-en">Views today</span><span class="lang-content lang-ja">今日の閲覧数</span><span class="lang-content lang-ko">오늘 조회수</span></dt>
                            <dd id="today-views">&mdash;</dd>
                        </div>
                        <div>
                            <dt><span class="lang-content lang-en">Visitors</span><span class="lang-content lang-ja">訪問者</span><span class="lang-content lang-ko">방문자</span></dt>
                            <dd id="today-visitors">&mdash;</dd>
                        </div>
                    </dl>
                </div>
            </div>
        </header>

        {% if featured_article %}
        <section class="discovery-panel" aria-label="Article discovery tools">
            <label class="search-field" for="news-search">
                <svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="11" cy="11" r="7"></circle><path d="m20 20-4-4"></path></svg>
                <input id="news-search" type="search" autocomplete="off"
                    placeholder="기사 제목·요약·출처 검색"
                    aria-label="기사 검색">
            </label>
            <button class="saved-filter" id="saved-filter" type="button" aria-pressed="false">
                <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M6.5 4.5h11v15l-5.5-3-5.5 3z"></path></svg>
                <span class="lang-content lang-en">Saved</span>
                <span class="lang-content lang-ja">保存済み</span>
                <span class="lang-content lang-ko">읽기 목록</span>
                <span class="saved-filter-count" id="saved-count">0</span>
            </button>
            <div class="results-status">
                <span id="results-count" aria-live="polite"></span>
                <button class="reset-filter" id="reset-filter" type="button">
                    <span class="lang-content lang-en">Reset filters</span>
                    <span class="lang-content lang-ja">条件をリセット</span>
                    <span class="lang-content lang-ko">필터 초기화</span>
                </button>
            </div>
        </section>
        {% endif %}

        {% if featured_article %}
        <article class="featured article-card" id="lead-story" data-category="{{ canonical_category(featured_article.category, featured_article) }}" data-article-key="{{ article_key(featured_article) }}" data-search="{{ article_search_text(featured_article) }}">
            {% if featured_article.image_url %}
            <img src="{{ featured_article.image_url }}" alt="Featured Image" class="featured-img" onerror="this.style.display='none'{% if is_cosplay_article(featured_article) %};this.nextElementSibling.hidden=false{% endif %}">
            {% if is_cosplay_article(featured_article) %}
            <div class="featured-img article-placeholder cosplay-placeholder" role="img" aria-label="Cosplay event" hidden>
                <span class="placeholder-kicker">CULTURE</span>
                <span class="placeholder-title">COSPLAY EVENT</span>
            </div>
            {% endif %}
            {% elif is_cosplay_article(featured_article) %}
            <div class="featured-img article-placeholder cosplay-placeholder" role="img" aria-label="Cosplay event">
                <span class="placeholder-kicker">CULTURE</span>
                <span class="placeholder-title">COSPLAY EVENT</span>
            </div>
            {% else %}
            <div class="featured-img"></div>
            {% endif %}
            
            <div class="featured-content">
                <div class="meta">
                    <span>{{ display_category(featured_article) }}</span>
                    <span>&mdash;</span>
                    <span>{{ featured_article.source }}</span>
                </div>
                
                <h2 class="featured-title">
                    <a href="{{ featured_article.link }}" target="_blank" rel="noopener noreferrer">
                        <span class="lang-content lang-en">{{ featured_article.title_en or featured_article.title_ko or featured_article.title_ja }}</span>
                        <span class="lang-content lang-ja">{{ featured_article.title_ja or featured_article.title_ko or featured_article.title_en }}</span>
                        <span class="lang-content lang-ko">{{ featured_article.title_ko or featured_article.title_ja or featured_article.title_en }}</span>
                    </a>
                </h2>
                
                <div class="featured-summary">
                    <span class="lang-content lang-en">{{ featured_article.summary_en or featured_article.summary_ko or featured_article.summary_ja }}</span>
                    <span class="lang-content lang-ja">{{ featured_article.summary_ja or featured_article.summary_ko or featured_article.summary_en }}</span>
                    <span class="lang-content lang-ko">{{ featured_article.summary_ko or featured_article.summary_ja or featured_article.summary_en }}</span>
                </div>
                <div class="article-actions">
                    <button class="interaction-btn save-btn" type="button" data-save-key="{{ article_key(featured_article) }}" aria-pressed="false">
                        <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M6.5 4.5h11v15l-5.5-3-5.5 3z"></path></svg>
                        <span class="save-default lang-content lang-en">Save</span><span class="save-active lang-content lang-en">Saved</span>
                        <span class="save-default lang-content lang-ja">保存</span><span class="save-active lang-content lang-ja">保存済み</span>
                        <span class="save-default lang-content lang-ko">저장</span><span class="save-active lang-content lang-ko">저장됨</span>
                    </button>
                    <button class="interaction-btn like-btn" type="button" data-like-key="like{{ article_key(featured_article) }}" data-like-loaded="false" aria-pressed="false">
                        <span class="like-heart" aria-hidden="true">♡</span>
                        <span class="lang-content lang-en">Like</span>
                        <span class="lang-content lang-ja">いいね</span>
                        <span class="lang-content lang-ko">좋아요</span>
                        <span class="like-count" aria-live="polite">&mdash;</span>
                    </button>
                </div>
            </div>
        </article>
        {% endif %}

        {% if featured_article %}
        <div class="masonry-grid">
            {% for item in articles %}
            <article class="article-card" data-category="{{ canonical_category(item.category, item) }}" data-article-key="{{ article_key(item) }}" data-search="{{ article_search_text(item) }}">
                {% if item.image_url %}
                <img src="{{ item.image_url }}" alt="Thumbnail" class="article-img" loading="lazy" onerror="this.style.display='none'{% if is_cosplay_article(item) %};this.nextElementSibling.hidden=false{% endif %}">
                {% if is_cosplay_article(item) %}
                <div class="article-img article-placeholder cosplay-placeholder" role="img" aria-label="Cosplay event" hidden>
                    <span class="placeholder-kicker">CULTURE</span>
                    <span class="placeholder-title">COSPLAY EVENT</span>
                </div>
                {% endif %}
                {% elif is_cosplay_article(item) %}
                <div class="article-img article-placeholder cosplay-placeholder" role="img" aria-label="Cosplay event">
                    <span class="placeholder-kicker">CULTURE</span>
                    <span class="placeholder-title">COSPLAY EVENT</span>
                </div>
                {% endif %}
                
                <div class="meta">
                    <span>{{ display_category(item) }}</span>
                    <span>&bull;</span>
                    <span>{{ item.source }}</span>
                </div>
                
                <h2 class="article-title">
                    <a href="{{ item.link }}" target="_blank" rel="noopener noreferrer">
                        <span class="lang-content lang-en">{{ item.title_en or item.title_ko or item.title_ja }}</span>
                        <span class="lang-content lang-ja">{{ item.title_ja or item.title_ko or item.title_en }}</span>
                        <span class="lang-content lang-ko">{{ item.title_ko or item.title_ja or item.title_en }}</span>
                    </a>
                </h2>
                
                <div class="article-summary">
                    <span class="lang-content lang-en">{{ item.summary_en or item.summary_ko or item.summary_ja }}</span>
                    <span class="lang-content lang-ja">{{ item.summary_ja or item.summary_ko or item.summary_en }}</span>
                    <span class="lang-content lang-ko">{{ item.summary_ko or item.summary_ja or item.summary_en }}</span>
                </div>
                <div class="article-actions">
                    <button class="interaction-btn save-btn" type="button" data-save-key="{{ article_key(item) }}" aria-pressed="false">
                        <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M6.5 4.5h11v15l-5.5-3-5.5 3z"></path></svg>
                        <span class="save-default lang-content lang-en">Save</span><span class="save-active lang-content lang-en">Saved</span>
                        <span class="save-default lang-content lang-ja">保存</span><span class="save-active lang-content lang-ja">保存済み</span>
                        <span class="save-default lang-content lang-ko">저장</span><span class="save-active lang-content lang-ko">저장됨</span>
                    </button>
                    <button class="interaction-btn like-btn" type="button" data-like-key="like{{ article_key(item) }}" data-like-loaded="false" aria-pressed="false">
                        <span class="like-heart" aria-hidden="true">♡</span>
                        <span class="lang-content lang-en">Like</span>
                        <span class="lang-content lang-ja">いいね</span>
                        <span class="lang-content lang-ko">좋아요</span>
                        <span class="like-count" aria-live="polite">&mdash;</span>
                    </button>
                </div>
            </article>
            {% endfor %}
        </div>
        <section class="no-results" id="no-results" hidden role="status">
            <svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="11" cy="11" r="7"></circle><path d="m20 20-4-4"></path></svg>
            <h2><span class="lang-content lang-en">No matching articles</span><span class="lang-content lang-ja">条件に合う記事がありません</span><span class="lang-content lang-ko">조건에 맞는 기사가 없어요</span></h2>
            <p><span class="lang-content lang-en">Try another keyword or reset the filters.</span><span class="lang-content lang-ja">別のキーワードか条件のリセットをお試しください。</span><span class="lang-content lang-ko">다른 검색어를 입력하거나 필터를 초기화해 보세요.</span></p>
            <button class="interaction-btn" type="button" onclick="resetArticleFilters()"><span class="lang-content lang-en">Show all</span><span class="lang-content lang-ja">すべて表示</span><span class="lang-content lang-ko">전체 보기</span></button>
        </section>
        {% else %}
        <section class="empty-state" role="status">
            <h1>
                <span class="lang-content lang-en">No news for this issue</span>
                <span class="lang-content lang-ja">この日付のニュースはありません</span>
                <span class="lang-content lang-ko">이 날짜의 뉴스가 없습니다</span>
            </h1>
            <p>
                <span class="lang-content lang-en">Choose another date or return to the latest issue.</span>
                <span class="lang-content lang-ja">別の日付を選ぶか、最新号に戻ってください。</span>
                <span class="lang-content lang-ko">다른 날짜를 선택하거나 최신 뉴스로 돌아가세요.</span>
            </p>
        </section>
        {% endif %}
    </main>

    <script>
        const COUNTER_API_BASE = 'https://api.counterapi.dev/v1';
        const COUNTER_NAMESPACE = 'techmagehxhflnews7f4c2d91';
        const LIVE_COUNTER_HOSTS = new Set(['ehxhfl.github.io']);
        const SAVED_ARTICLES_KEY = 'techmag-saved-articles';
        let lastTrafficPayload = null;
        let activeCategory = 'All';
        let savedOnly = false;
        let savedArticles = readSavedArticles();
        let visibleArticleCount = 0;

        function isLiveCounterSite() {
            return location.protocol === 'https:' && LIVE_COUNTER_HOSTS.has(location.hostname);
        }

        function safeStorageGet(key) {
            try { return localStorage.getItem(key); } catch { return null; }
        }

        function safeStorageSet(key, value) {
            try { localStorage.setItem(key, value); return true; } catch { return false; }
        }

        function readSavedArticles() {
            try {
                const value = JSON.parse(localStorage.getItem(SAVED_ARTICLES_KEY) || '[]');
                return new Set(Array.isArray(value) ? value.filter(key => typeof key === 'string') : []);
            } catch {
                return new Set();
            }
        }

        function writeSavedArticles() {
            safeStorageSet(SAVED_ARTICLES_KEY, JSON.stringify(Array.from(savedArticles)));
        }

        function renderSavedState(button) {
            const saved = savedArticles.has(button.dataset.saveKey);
            button.setAttribute('aria-pressed', saved ? 'true' : 'false');
        }

        function renderSavedCount() {
            const count = document.getElementById('saved-count');
            if (count) count.textContent = String(savedArticles.size);
        }

        function renderResultsCount(count) {
            visibleArticleCount = count;
            const target = document.getElementById('results-count');
            if (!target) return;
            const language = document.documentElement.lang;
            target.textContent = language === 'en'
                ? `${count} article${count === 1 ? '' : 's'} shown`
                : language === 'ja' ? `${count}件の記事を表示` : `${count}개 기사 표시`;
        }

        function applyArticleFilters() {
            const search = document.getElementById('news-search');
            const query = String(search?.value || '').trim().toLocaleLowerCase();
            let visible = 0;
            document.querySelectorAll('.article-card').forEach(card => {
                const categoryMatches = activeCategory === 'All' || card.dataset.category === activeCategory;
                const searchMatches = !query || String(card.dataset.search || '').includes(query);
                const savedMatches = !savedOnly || savedArticles.has(card.dataset.articleKey);
                card.hidden = !(categoryMatches && searchMatches && savedMatches);
                if (!card.hidden) visible += 1;
            });
            const empty = document.getElementById('no-results');
            if (empty) empty.hidden = visible !== 0;
            renderResultsCount(visible);
        }

        function initDiscoveryTools() {
            document.getElementById('news-search')?.addEventListener('input', applyArticleFilters);
            document.getElementById('saved-filter')?.addEventListener('click', () => {
                savedOnly = !savedOnly;
                document.getElementById('saved-filter')?.setAttribute('aria-pressed', savedOnly ? 'true' : 'false');
                applyArticleFilters();
            });
            document.getElementById('reset-filter')?.addEventListener('click', resetArticleFilters);
            document.querySelectorAll('.save-btn').forEach(button => {
                renderSavedState(button);
                button.addEventListener('click', () => {
                    const key = button.dataset.saveKey;
                    if (!key) return;
                    if (savedArticles.has(key)) savedArticles.delete(key);
                    else savedArticles.add(key);
                    writeSavedArticles();
                    document.querySelectorAll('.save-btn').forEach(renderSavedState);
                    renderSavedCount();
                    applyArticleFilters();
                });
            });
            renderSavedCount();
        }

        function resetArticleFilters() {
            const search = document.getElementById('news-search');
            if (search) search.value = '';
            savedOnly = false;
            document.getElementById('saved-filter')?.setAttribute('aria-pressed', 'false');
            setCategory('All');
        }

        async function withCounterLock(key, task) {
            if (navigator.locks && typeof navigator.locks.request === 'function') {
                return navigator.locks.request(`techmag:${key}`, task);
            }
            return task();
        }

        function validCount(value) {
            const count = Number(value);
            return Number.isSafeInteger(count) && count >= 0 ? count : null;
        }

        function countFormatters() {
            const locale = { en: 'en-US', ja: 'ja-JP', ko: 'ko-KR' }[document.documentElement.lang] || 'ko-KR';
            return {
                compact: new Intl.NumberFormat(locale, { notation: 'compact', maximumFractionDigits: 1 }),
                full: new Intl.NumberFormat(locale)
            };
        }

        async function counterRequest(key, action = '', signal = undefined, allowMissing = false) {
            const suffix = action ? '/' + action : '/';
            const url = `${COUNTER_API_BASE}/${encodeURIComponent(COUNTER_NAMESPACE)}/${encodeURIComponent(key)}${suffix}`;
            const response = await fetch(url, {
                method: 'GET',
                cache: 'no-store',
                credentials: 'omit',
                referrerPolicy: 'no-referrer',
                signal
            });
            if (!response.ok) {
                let errorPayload = null;
                if (allowMissing && (response.status === 400 || response.status === 404)) {
                    try { errorPayload = await response.json(); } catch { /* Ignore invalid error JSON. */ }
                    if (response.status === 404 ||
                        String(errorPayload?.message || '').toLowerCase() === 'record not found') {
                        return { count: 0 };
                    }
                }
                throw new Error(`Counter request failed: ${response.status}`);
            }
            const payload = await response.json();
            if (validCount(payload?.count) === null) throw new Error('Invalid counter response');
            return payload;
        }

        function jstDateKey() {
            const parts = new Intl.DateTimeFormat('en-US', {
                timeZone: 'Asia/Tokyo',
                year: 'numeric',
                month: '2-digit',
                day: '2-digit'
            }).formatToParts(new Date());
            const values = Object.fromEntries(parts.map(part => [part.type, part.value]));
            return `${values.year}${values.month}${values.day}`;
        }

        function renderTraffic(payload) {
            const root = document.getElementById('daily-traffic');
            const fields = {
                views: document.getElementById('today-views'),
                visitors: document.getElementById('today-visitors')
            };
            if (!root || !fields.views || !fields.visitors) return;

            const formatters = countFormatters();
            let rendered = 0;
            Object.entries(fields).forEach(([key, element]) => {
                const count = validCount(payload?.[key]);
                element.textContent = count === null ? '—' : formatters.compact.format(count);
                element.title = count === null ? '' : formatters.full.format(count);
                if (count !== null) rendered += 1;
            });
            root.dataset.state = rendered === 2 ? 'ready' : rendered === 1 ? 'partial' : 'unavailable';
            root.setAttribute('aria-busy', 'false');
        }

        async function recordAndReadTodayTraffic(signal) {
            const day = jstDateKey();
            const visitorMarker = `techmag-visitor-${day}`;
            const viewPromise = counterRequest(`views${day}`, 'up', signal);
            const visitorPromise = withCounterLock(`visitor${day}`, async () => {
                if (safeStorageGet(visitorMarker) === '1') {
                    return counterRequest(`visitors${day}`, '', signal, true);
                }
                if (!safeStorageSet(visitorMarker, '1')) {
                    return counterRequest(`visitors${day}`, '', signal, true);
                }
                return counterRequest(`visitors${day}`, 'up', signal);
            });
            const [viewResult, visitorResult] = await Promise.allSettled([viewPromise, visitorPromise]);

            const views = viewResult.status === 'fulfilled' ? validCount(viewResult.value.count) : null;
            const visitors = visitorResult.status === 'fulfilled' ? validCount(visitorResult.value.count) : null;
            return { views, visitors };
        }

        async function loadTodayTraffic() {
            if (!isLiveCounterSite()) {
                renderTraffic(null);
                return;
            }
            const controller = new AbortController();
            const timeout = window.setTimeout(() => controller.abort(), 5000);
            try {
                lastTrafficPayload = await recordAndReadTodayTraffic(controller.signal);
                renderTraffic(lastTrafficPayload);
            } catch {
                renderTraffic(null);
            } finally {
                window.clearTimeout(timeout);
            }
        }

        function renderLikeCount(button, count) {
            const valid = validCount(count);
            const countElement = button.querySelector('.like-count');
            if (!countElement) return;
            if (valid === null) {
                countElement.textContent = '—';
                countElement.title = '';
                delete button.dataset.likeCount;
                return;
            }
            const formatters = countFormatters();
            countElement.textContent = formatters.compact.format(valid);
            countElement.title = formatters.full.format(valid);
            button.dataset.likeCount = String(valid);
        }

        function setLikedState(button, liked) {
            button.setAttribute('aria-pressed', liked ? 'true' : 'false');
            const heart = button.querySelector('.like-heart');
            if (heart) heart.textContent = liked ? '♥' : '♡';
        }

        async function loadLikeCount(button) {
            if (button.dataset.likeLoaded === 'true' || !isLiveCounterSite()) return true;
            button.dataset.likeLoaded = 'true';
            const version = button.dataset.likeVersion || '0';
            const controller = new AbortController();
            const timeout = window.setTimeout(() => controller.abort(), 5000);
            try {
                const payload = await counterRequest(button.dataset.likeKey, '', controller.signal, true);
                if ((button.dataset.likeVersion || '0') === version) {
                    renderLikeCount(button, payload.count);
                }
                return true;
            } catch {
                if ((button.dataset.likeVersion || '0') === version) {
                    renderLikeCount(button, null);
                }
                button.dataset.likeLoaded = 'false';
                return false;
            } finally {
                window.clearTimeout(timeout);
            }
        }

        function initLikeButtons() {
            const buttons = Array.from(document.querySelectorAll('.like-btn'));
            buttons.forEach(button => {
                const storageKey = `techmag-${button.dataset.likeKey}`;
                button.dataset.likeStorageKey = storageKey;
                setLikedState(button, safeStorageGet(storageKey) === '1');
                button.addEventListener('click', async () => {
                    if (!isLiveCounterSite() || button.getAttribute('aria-pressed') === 'true') return;
                    button.disabled = true;
                    button.dataset.likeVersion = String(Number(button.dataset.likeVersion || '0') + 1);
                    try {
                        const payload = await withCounterLock(button.dataset.likeKey, async () => {
                            if (safeStorageGet(storageKey) === '1') {
                                return counterRequest(button.dataset.likeKey, '', undefined, true);
                            }
                            const result = await counterRequest(button.dataset.likeKey, 'up');
                            safeStorageSet(storageKey, '1');
                            return result;
                        });
                        setLikedState(button, true);
                        renderLikeCount(button, payload.count);
                    } catch {
                        renderLikeCount(button, button.dataset.likeCount ?? null);
                    } finally {
                        button.disabled = false;
                    }
                });
            });

            if (!isLiveCounterSite()) {
                buttons.forEach(button => { button.disabled = true; });
                return;
            }
            if ('IntersectionObserver' in window) {
                const observer = new IntersectionObserver(entries => {
                    entries.forEach(entry => {
                        if (!entry.isIntersecting) return;
                        loadLikeCount(entry.target).then(loaded => {
                            if (loaded) observer.unobserve(entry.target);
                        });
                    });
                }, { rootMargin: '400px 0px' });
                buttons.forEach(button => observer.observe(button));
            } else {
                buttons.forEach(loadLikeCount);
            }

            window.addEventListener('storage', event => {
                if (event.newValue !== '1') return;
                buttons.forEach(button => {
                    if (button.dataset.likeStorageKey !== event.key) return;
                    button.dataset.likeVersion = String(Number(button.dataset.likeVersion || '0') + 1);
                    setLikedState(button, true);
                });
            });
        }

        function setCategory(cat) {
            activeCategory = cat;
            document.querySelectorAll('.cat-btn').forEach(btn => {
                btn.classList.remove('active');
                btn.setAttribute('aria-pressed', 'false');
            });
            const activeBtn = document.getElementById('cat-' + cat);
            if (activeBtn) {
                activeBtn.classList.add('active');
                activeBtn.setAttribute('aria-pressed', 'true');
            }
            safeStorageSet('preferredCat', cat);
            applyArticleFilters();
        }

        function setLanguage(lang) {
            const supportedLanguages = ['en', 'ja', 'ko'];
            if (!supportedLanguages.includes(lang)) lang = 'ko';
            document.documentElement.setAttribute('lang', lang);
            document.querySelectorAll('.lang-btn').forEach(btn => btn.classList.remove('active'));
            const activeButton = document.getElementById('btn-' + lang);
            if (activeButton) activeButton.classList.add('active');
            safeStorageSet('preferredLang', lang);
            if (lastTrafficPayload) renderTraffic(lastTrafficPayload);
            document.querySelectorAll('.like-btn[data-like-count]').forEach(button => {
                renderLikeCount(button, button.dataset.likeCount);
            });
            renderResultsCount(visibleArticleCount);
        }

        // Init language and category
        const savedLang = safeStorageGet('preferredLang') || 'ko';
        setLanguage(savedLang);

        const supportedCategories = ['All', 'IT/Tech', 'AI', 'Game Engine', 'Game', 'VTuber', 'Anime', 'Cosplay/Event', 'CG/Blender'];
        const savedCat = safeStorageGet('preferredCat') || 'All';
        initDiscoveryTools();
        setCategory(supportedCategories.includes(savedCat) ? savedCat : 'All');
        loadTodayTraffic();
        initLikeButtons();
    </script>
</body>
</html>
"""

def generate_html(articles, output_path="index.html", display_date=None):
    archives = discover_archives()
    output_name = os.path.basename(os.fspath(output_path))
    output_date_match = ARCHIVE_FILE_RE.fullmatch(output_name)
    selected_date = output_date_match.group(1) if output_date_match else None

    if not display_date:
        display_date = selected_date or datetime.now().strftime("%Y-%m-%d %H:%M")

    if not selected_date and isinstance(display_date, str):
        try:
            datetime.strptime(display_date, "%Y-%m-%d")
            selected_date = display_date
        except ValueError:
            pass

    is_latest_page = output_name == "index.html"
    navigation_date = selected_date
    if is_latest_page and archives:
        navigation_date = archives[0]["date"]

    older_archive = None
    newer_archive = None
    if navigation_date:
        current_index = next(
            (index for index, archive in enumerate(archives) if archive["date"] == navigation_date),
            None,
        )
        if current_index is not None:
            if current_index + 1 < len(archives):
                older_archive = archives[current_index + 1]
            if current_index > 0:
                newer_archive = archives[current_index - 1]

    articles = articles or []
    featured_article = articles[0] if articles else None
    rest_articles = articles[1:] if len(articles) > 1 else []
    article_count = len(articles)
    source_count = len({
        str(article.get("source") or "").strip()
        for article in articles
        if isinstance(article, dict) and str(article.get("source") or "").strip()
    })
    category_count = len({
        canonical_category(article.get("category"), article)
        for article in articles
        if isinstance(article, dict) and canonical_category(article.get("category"), article)
    })

    ascending_archives = list(reversed(archives))
    issue_number = len(ascending_archives)
    if navigation_date:
        archive_index = next(
            (index for index, archive in enumerate(ascending_archives) if archive["date"] == navigation_date),
            None,
        )
        if archive_index is not None:
            issue_number = archive_index + 1

    environment = Environment(autoescape=True)
    template = environment.from_string(HTML_TEMPLATE)
    html_content = template.render(
        featured_article=featured_article,
        articles=rest_articles,
        date=display_date,
        archives=archives,
        selected_date=selected_date,
        is_latest_page=is_latest_page,
        older_archive=older_archive,
        newer_archive=newer_archive,
        canonical_category=canonical_category,
        display_category=display_category,
        article_key=article_key,
        article_search_text=article_search_text,
        is_cosplay_article=is_cosplay_article,
        article_count=article_count,
        source_count=source_count,
        category_count=category_count,
        issue_number=max(issue_number, 1),
    )
    
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html_content)

if __name__ == "__main__":
    pass
