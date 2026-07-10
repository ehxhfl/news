import os
import glob
import re
from datetime import datetime
from jinja2 import Environment


DATA_FILE_RE = re.compile(r"^data-(\d{4}-\d{2}-\d{2})\.json$")
ARCHIVE_FILE_RE = re.compile(r"^archive-(\d{4}-\d{2}-\d{2})\.html$")


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


def canonical_category(category):
    """Map current and legacy labels to the five filter keys without changing display text."""
    value = str(category or "").strip()
    folded = value.casefold()

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


HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="ko" data-theme="system">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Global Tech Magazine</title>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Noto+Sans+JP:wght@400;500;700&display=swap');
        @import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/static/pretendard.css');
        
        :root {
            /* Light Theme */
            --bg-color: #ffffff;
            --text-main: #111111;
            --text-muted: #666666;
            --border-color: #eaeaea;
            --nav-bg: rgba(255, 255, 255, 0.95);
            --accent: #000000;
            --hover-bg: #f9f9f9;
        }

        html {
            scrollbar-gutter: stable;
        }

        @media (prefers-color-scheme: dark) {
            :root {
                /* Premium Muted Dark Mode */
                --bg-color: #0d0d0d;
                --text-main: #f0f0f0;
                --text-muted: #a0a0a0;
                --border-color: #222222;
                --nav-bg: rgba(13, 13, 13, 0.95);
                --accent: #ffffff;
                --hover-bg: #161616;
            }
        }

        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }

        body {
            font-family: 'Inter', 'Pretendard', 'Noto Sans JP', sans-serif;
            background-color: var(--bg-color);
            color: var(--text-main);
            line-height: 1.6;
            -webkit-font-smoothing: antialiased;
        }
        
        a {
            color: inherit;
            text-decoration: none;
        }

        /* Top Navigation */
        .navbar {
            position: sticky;
            top: 0;
            z-index: 1000;
            background: var(--nav-bg);
            backdrop-filter: blur(10px);
            -webkit-backdrop-filter: blur(10px);
            border-bottom: 1px solid var(--border-color);
            padding: 1rem 2rem;
            display: flex;
            flex-wrap: wrap;
            gap: 1rem;
            justify-content: space-between;
            align-items: center;
            z-index: 1000;
        }

        .brand {
            font-weight: 700;
            font-size: 1.25rem;
            letter-spacing: -0.02em;
        }

        .nav-controls {
            display: flex;
            gap: 2rem;
            align-items: center;
            justify-content: flex-end;
            flex-wrap: wrap;
            min-width: 0;
            max-width: 100%;
        }
        
        /* Category Filter */
        .category-toggle {
            display: flex;
            gap: 1rem;
            font-size: 0.85rem;
            font-weight: 500;
            justify-content: center;
            flex-wrap: wrap;
            min-width: 0;
        }
        .cat-btn {
            flex: 0 0 auto;
            cursor: pointer;
            color: var(--text-muted);
            transition: color 0.2s, border-color 0.2s, background-color 0.2s;
            border: 1px solid transparent;
            border-radius: 999px;
            background: none;
            font-family: inherit;
            font-weight: 600;
            padding: 0.2rem 0.5rem;
            white-space: nowrap;
        }
        .cat-btn.active, .cat-btn:hover {
            color: var(--text-main);
            border-color: var(--border-color);
            background: var(--hover-bg);
        }

        .lang-toggle {
            display: flex;
            gap: 1rem;
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
            border-radius: 0.35rem;
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
        .lang-btn:focus-visible {
            outline: 2px solid var(--accent);
            outline-offset: 2px;
        }

        .issue-navigation {
            display: flex;
            align-items: center;
            justify-content: center;
            flex-wrap: wrap;
            gap: 0.75rem;
        }

        .issue-link {
            display: inline-flex;
            align-items: center;
            gap: 0.3rem;
            border: 1px solid var(--border-color);
            border-radius: 999px;
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

        /* Header Date */
        .header-date {
            font-size: 0.85rem;
            color: var(--text-muted);
            text-transform: uppercase;
            letter-spacing: 0.05em;
            margin-bottom: 2rem;
            border-bottom: 1px solid var(--border-color);
            padding-bottom: 1rem;
        }

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

        .article-img {
            width: 100%;
            height: auto;
            margin-bottom: 1rem;
            background: var(--hover-bg);
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

        @media (max-width: 1024px) {
            .masonry-grid { column-count: 2; }
            .featured { grid-template-columns: 1fr; gap: 2rem; }
            .featured-img { min-height: 300px; }
            .featured-title { font-size: 2.5rem; }
        }

        @media (max-width: 640px) {
            .masonry-grid { column-count: 1; }
            .navbar { flex-direction: column; gap: 1rem; padding: 1rem; }
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
            .featured-img { min-height: 200px; }
            .featured-title { font-size: 2rem; }
            .container { padding: 1rem; }
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

    <nav class="navbar">
        <div class="brand">TECH MAG</div>
        <div class="nav-controls">
            <div class="category-toggle">
                <button class="cat-btn active" onclick="setCategory('All')" id="cat-All">All</button>
                <button class="cat-btn" onclick="setCategory('IT/Tech')" id="cat-IT/Tech">IT/Tech</button>
                <button class="cat-btn" onclick="setCategory('AI')" id="cat-AI">AI</button>
                <button class="cat-btn" onclick="setCategory('Game')" id="cat-Game">Game</button>
                <button class="cat-btn" onclick="setCategory('Anime')" id="cat-Anime">Anime</button>
                <button class="cat-btn" onclick="setCategory('CG/Blender')" id="cat-CG/Blender">CG/Blender</button>
            </div>
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
            <div class="lang-toggle">
                <button class="lang-btn" onclick="setLanguage('en')" id="btn-en">EN</button>
                <button class="lang-btn" onclick="setLanguage('ja')" id="btn-ja">JA</button>
                <button class="lang-btn active" onclick="setLanguage('ko')" id="btn-ko">KO</button>
            </div>
        </div>
    </nav>

    <div class="container">
        <div class="header-date">{{ date }} EDITORIAL ISSUE</div>

        {% if featured_article %}
        <article class="featured article-card" data-category="{{ canonical_category(featured_article.category) }}">
            {% if featured_article.image_url %}
            <img src="{{ featured_article.image_url }}" alt="Featured Image" class="featured-img" onerror="this.style.display='none'">
            {% else %}
            <div class="featured-img"></div>
            {% endif %}
            
            <div class="featured-content">
                <div class="meta">
                    <span>{{ featured_article.category }}</span>
                    <span>&mdash;</span>
                    <span>{{ featured_article.source }}</span>
                </div>
                
                <h1 class="featured-title">
                    <a href="{{ featured_article.link }}" target="_blank" rel="noopener noreferrer">
                        <span class="lang-content lang-en">{{ featured_article.title_en or featured_article.title_ko or featured_article.title_ja }}</span>
                        <span class="lang-content lang-ja">{{ featured_article.title_ja or featured_article.title_ko or featured_article.title_en }}</span>
                        <span class="lang-content lang-ko">{{ featured_article.title_ko or featured_article.title_ja or featured_article.title_en }}</span>
                    </a>
                </h1>
                
                <div class="featured-summary">
                    <span class="lang-content lang-en">{{ featured_article.summary_en or featured_article.summary_ko or featured_article.summary_ja }}</span>
                    <span class="lang-content lang-ja">{{ featured_article.summary_ja or featured_article.summary_ko or featured_article.summary_en }}</span>
                    <span class="lang-content lang-ko">{{ featured_article.summary_ko or featured_article.summary_ja or featured_article.summary_en }}</span>
                </div>
            </div>
        </article>
        {% endif %}

        {% if featured_article %}
        <div class="masonry-grid">
            {% for item in articles %}
            <article class="article-card" data-category="{{ canonical_category(item.category) }}">
                {% if item.image_url %}
                <img src="{{ item.image_url }}" alt="Thumbnail" class="article-img" loading="lazy" onerror="this.style.display='none'">
                {% endif %}
                
                <div class="meta">
                    <span>{{ item.category }}</span>
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
            </article>
            {% endfor %}
        </div>
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
    </div>

    <script>
        function setCategory(cat) {
            document.querySelectorAll('.cat-btn').forEach(btn => btn.classList.remove('active'));
            const activeBtn = document.getElementById('cat-' + cat);
            if (activeBtn) activeBtn.classList.add('active');
            
            document.querySelectorAll('.article-card').forEach(card => {
                if (cat === 'All' || card.getAttribute('data-category') === cat) {
                    card.style.display = '';
                } else {
                    card.style.display = 'none';
                }
            });
            localStorage.setItem('preferredCat', cat);
        }

        function setLanguage(lang) {
            const supportedLanguages = ['en', 'ja', 'ko'];
            if (!supportedLanguages.includes(lang)) lang = 'ko';
            document.documentElement.setAttribute('lang', lang);
            document.querySelectorAll('.lang-btn').forEach(btn => btn.classList.remove('active'));
            const activeButton = document.getElementById('btn-' + lang);
            if (activeButton) activeButton.classList.add('active');
            localStorage.setItem('preferredLang', lang);
        }

        // Init language and category
        const savedLang = localStorage.getItem('preferredLang') || 'ko';
        setLanguage(savedLang);

        const supportedCategories = ['All', 'IT/Tech', 'AI', 'Game', 'Anime', 'CG/Blender'];
        const savedCat = localStorage.getItem('preferredCat') || 'All';
        setCategory(supportedCategories.includes(savedCat) ? savedCat : 'All');
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
    )
    
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html_content)

if __name__ == "__main__":
    pass
