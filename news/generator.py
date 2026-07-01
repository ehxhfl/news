import os
import glob
from jinja2 import Template
from datetime import datetime

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI Curated Japan News - {{ date }}</title>
    <style>
        @import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/static/pretendard.css');
        
        :root {
            --bg-color: #f4f7fb;
            --text-main: #1e293b;
            --text-muted: #64748b;
            --card-bg: #ffffff;
            --primary: #4f46e5;
            --primary-hover: #4338ca;
            --sidebar-bg: linear-gradient(180deg, #0f172a 0%, #1e293b 100%);
            --accent: #0ea5e9;
        }
        
        html {
            scroll-behavior: smooth;
        }

        body {
            font-family: 'Pretendard', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            background-color: var(--bg-color);
            color: var(--text-main);
            line-height: 1.6;
            margin: 0;
            padding: 0;
            display: flex;
            min-height: 100vh;
            -webkit-font-smoothing: antialiased;
        }
        
        /* Sidebar Styling */
        .sidebar {
            width: 260px;
            background: var(--sidebar-bg);
            color: white;
            padding: 30px 20px;
            box-sizing: border-box;
            flex-shrink: 0;
            position: sticky;
            top: 0;
            height: 100vh;
            overflow-y: auto;
            box-shadow: 4px 0 15px rgba(0,0,0,0.05);
        }
        .sidebar::-webkit-scrollbar { width: 6px; }
        .sidebar::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.2); border-radius: 10px; }
        
        .sidebar h2 {
            font-size: 1.1em;
            text-transform: uppercase;
            letter-spacing: 1px;
            color: #94a3b8;
            margin-top: 0;
            margin-bottom: 20px;
            font-weight: 700;
        }
        .archive-list {
            list-style: none;
            padding: 0;
            margin: 0;
        }
        .archive-list li {
            margin-bottom: 12px;
        }
        .archive-list a {
            color: #cbd5e1;
            text-decoration: none;
            display: flex;
            align-items: center;
            padding: 10px 15px;
            border-radius: 8px;
            transition: all 0.3s ease;
            font-size: 0.95em;
        }
        .archive-list a:hover {
            background-color: rgba(255, 255, 255, 0.1);
            color: white;
            transform: translateX(5px);
        }
        
        /* Main Content */
        .content {
            flex-grow: 1;
            padding: 50px 60px;
            box-sizing: border-box;
            max-width: 1400px;
            margin: 0 auto;
        }
        
        header {
            margin-bottom: 40px;
            padding-bottom: 25px;
            border-bottom: 1px solid #e2e8f0;
            display: flex;
            justify-content: space-between;
            align-items: flex-end;
        }
        h1 { 
            margin: 0; 
            font-size: 2.8em; 
            font-weight: 800;
            background: linear-gradient(135deg, var(--primary), var(--accent));
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            letter-spacing: -1px;
        }
        .date { 
            color: var(--text-muted); 
            font-size: 1.1em; 
            font-weight: 500;
        }
        
        /* Category Navigation */
        .category-nav {
            display: flex;
            flex-wrap: wrap;
            gap: 12px;
            margin-bottom: 50px;
        }
        .category-nav a {
            background-color: white;
            color: var(--text-main);
            padding: 10px 20px;
            border-radius: 30px;
            text-decoration: none;
            font-weight: 600;
            font-size: 0.95em;
            box-shadow: 0 2px 10px rgba(0,0,0,0.03);
            border: 1px solid #e2e8f0;
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        }
        .category-nav a:hover {
            background-color: var(--primary);
            color: white;
            border-color: var(--primary);
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(79, 70, 229, 0.2);
        }
        
        /* Categories and Grid */
        .category-section { 
            margin-bottom: 70px; 
            scroll-margin-top: 40px; 
        }
        .category-title {
            font-size: 2em;
            font-weight: 800;
            color: var(--text-main);
            margin-bottom: 30px;
            display: flex;
            align-items: center;
            gap: 12px;
        }
        .category-title::before {
            content: "";
            display: block;
            width: 6px;
            height: 28px;
            background: var(--primary);
            border-radius: 4px;
        }
        
        .grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(340px, 1fr));
            gap: 30px;
        }
        
        /* News Cards */
        .card {
            background-color: var(--card-bg);
            border-radius: 20px;
            box-shadow: 0 10px 25px -5px rgba(0,0,0,0.05), 0 8px 10px -6px rgba(0,0,0,0.01);
            overflow: hidden;
            display: flex;
            flex-direction: column;
            transition: transform 0.3s ease, box-shadow 0.3s ease;
            border: 1px solid rgba(226, 232, 240, 0.8);
        }
        .card:hover {
            transform: translateY(-8px);
            box-shadow: 0 20px 35px -5px rgba(0,0,0,0.1), 0 10px 15px -5px rgba(0,0,0,0.04);
        }
        
        .card-img {
            width: 100%;
            height: 220px;
            object-fit: cover;
            background-color: #f1f5f9;
            border-bottom: 1px solid #f1f5f9;
        }
        
        .card-content {
            padding: 30px;
            flex-grow: 1;
            display: flex;
            flex-direction: column;
        }
        
        .source {
            font-size: 0.75em;
            color: var(--primary);
            background-color: rgba(79, 70, 229, 0.1);
            padding: 6px 12px;
            border-radius: 20px;
            display: inline-block;
            margin-bottom: 15px;
            font-weight: 700;
            letter-spacing: 0.5px;
            align-self: flex-start;
        }
        
        .title {
            font-size: 1.35em;
            font-weight: 800;
            margin: 0 0 15px 0;
            line-height: 1.4;
            color: #0f172a;
        }
        
        .summary {
            font-size: 1.05em;
            color: #475569;
            line-height: 1.7;
            margin-bottom: 25px;
            flex-grow: 1;
        }
        
        /* Action Buttons */
        .link-btn {
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 8px;
            background-color: var(--text-main);
            color: white;
            text-decoration: none;
            padding: 12px 20px;
            border-radius: 12px;
            font-weight: 600;
            margin-bottom: 20px;
            transition: all 0.2s ease;
            width: 100%;
            box-sizing: border-box;
        }
        .link-btn:hover {
            background-color: var(--primary);
            box-shadow: 0 4px 12px rgba(79, 70, 229, 0.3);
        }
        
        /* Japanese Original Toggle */
        details {
            font-size: 0.9em;
            color: var(--text-muted);
            background-color: #f8fafc;
            padding: 15px;
            border-radius: 12px;
            border: 1px solid #e2e8f0;
            transition: all 0.3s ease;
        }
        details[open] {
            background-color: #ffffff;
            box-shadow: inset 0 2px 4px rgba(0,0,0,0.02);
        }
        summary { 
            cursor: pointer; 
            font-weight: 600; 
            outline: none; 
            color: #334155;
            list-style: none;
            display: flex;
            align-items: center;
            gap: 5px;
        }
        summary::-webkit-details-marker { display: none; }
        summary::before {
            content: '🇯🇵';
            font-size: 1.2em;
        }
        details p {
            margin-top: 15px;
            margin-bottom: 0;
            padding-top: 15px;
            border-top: 1px dashed #cbd5e1;
            line-height: 1.6;
        }
        
        /* List View Override */
        .content.list-view .grid {
            display: flex;
            flex-direction: column;
            gap: 20px;
        }
        .content.list-view .card {
            flex-direction: row;
            align-items: stretch;
            min-height: 180px;
        }
        .content.list-view .card-img {
            width: 280px;
            height: auto;
            border-bottom: none;
            border-right: 1px solid #f1f5f9;
        }
        .content.list-view .card-content {
            padding: 20px 30px;
            justify-content: center;
        }
        .content.list-view .title {
            font-size: 1.25em;
            margin-bottom: 10px;
        }
        .content.list-view .summary {
            font-size: 0.95em;
            margin-bottom: 15px;
        }
        .content.list-view .link-btn {
            width: auto;
            align-self: flex-start;
            padding: 8px 16px;
        }

        /* Text View Override */
        .content.text-view .grid {
            display: flex;
            flex-direction: column;
            gap: 15px;
        }
        .content.text-view .card {
            border-radius: 10px;
            box-shadow: 0 2px 5px rgba(0,0,0,0.05);
        }
        .content.text-view .card-img {
            display: none;
        }
        .content.text-view .card-content {
            padding: 20px;
        }
        .content.text-view .title {
            font-size: 1.2em;
            margin-bottom: 10px;
        }
        .content.text-view .summary {
            font-size: 0.95em;
            margin-bottom: 15px;
        }
        .content.text-view .link-btn {
            width: auto;
            align-self: flex-start;
            padding: 8px 16px;
        }

        /* View Toggle Button */
        .view-toggle {
            display: flex;
            gap: 10px;
            margin-bottom: 30px;
        }
        .view-toggle button {
            background: white;
            border: 1px solid #e2e8f0;
            padding: 10px;
            border-radius: 8px;
            cursor: pointer;
            color: var(--text-muted);
            transition: all 0.2s;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        .view-toggle button:hover {
            background: #f8fafc;
            color: var(--primary);
        }
        .view-toggle button.active {
            background: var(--primary);
            color: white;
            border-color: var(--primary);
        }
        
        @media (max-width: 768px) {
            body { flex-direction: column; }
            .sidebar { width: 100%; height: auto; position: relative; padding: 20px; }
            .content { padding: 30px 20px; }
            header { flex-direction: column; align-items: flex-start; gap: 10px; }
            h1 { font-size: 2.2em; }
        }
    </style>
</head>
<body>
    <div class="sidebar">
        <h2>📚 아카이브 (Archive)</h2>
        <ul class="archive-list">
            <li><a href="index.html">오늘의 뉴스 (최신)</a></li>
            {% for arc in archives %}
            <li><a href="{{ arc.path }}">{{ arc.date }}</a></li>
            {% endfor %}
        </ul>
    </div>
    <div class="content" id="main-content">
        <header>
            <h1>AI Curated Japan News</h1>
            <div class="date">{{ date }} 업데이트</div>
        </header>

        <div class="view-toggle">
            <button id="btn-grid" class="active" title="크게 보기 (Grid)">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="7" height="7"></rect><rect x="14" y="3" width="7" height="7"></rect><rect x="14" y="14" width="7" height="7"></rect><rect x="3" y="14" width="7" height="7"></rect></svg>
            </button>
            <button id="btn-list" title="리스트 보기 (List)">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="8" y1="6" x2="21" y2="6"></line><line x1="8" y1="12" x2="21" y2="12"></line><line x1="8" y1="18" x2="21" y2="18"></line><line x1="3" y1="6" x2="3.01" y2="6"></line><line x1="3" y1="12" x2="3.01" y2="12"></line><line x1="3" y1="18" x2="3.01" y2="18"></line></svg>
            </button>
            <button id="btn-text" title="텍스트만 보기 (Text)">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="4" y1="6" x2="20" y2="6"></line><line x1="4" y1="12" x2="20" y2="12"></line><line x1="4" y1="18" x2="20" y2="18"></line></svg>
            </button>
        </div>

        <div class="category-nav">
            {% for category in articles_by_category.keys() %}
            <a href="#cat-{{ loop.index }}">{{ category }}</a>
            {% endfor %}
        </div>

        {% for category, items in articles_by_category.items() %}
        <section class="category-section" id="cat-{{ loop.index }}">
            <div class="category-title">{{ category }}</div>
            <div class="grid">
                {% for item in items %}
                <article class="card">
                    {% if item.image_url %}
                    <img src="{{ item.image_url }}" alt="Thumbnail" class="card-img" onerror="this.style.display='none'">
                    {% endif %}
                    
                    <div class="card-content">
                        <div><span class="source">{{ item.source }}</span></div>
                        <h2 class="title">{{ item.title_ko }}</h2>
                        <div class="summary">✨ {{ item.summary_ko }}</div>
                        
                        <a href="{{ item.link }}" target="_blank" rel="noopener" class="link-btn">🔗 원문 기사 보러가기</a>
                        
                        <details>
                            <summary>🇯🇵 일본어 원문 확인</summary>
                            <p><strong>{{ item.title_ja }}</strong></p>
                            <p>{{ item.summary_ja }}</p>
                        </details>
                    </div>
                </article>
                {% endfor %}
            </div>
        </section>
        {% endfor %}
    </div>

    <script>
        const content = document.getElementById('main-content');
        const btnGrid = document.getElementById('btn-grid');
        const btnList = document.getElementById('btn-list');
        const btnText = document.getElementById('btn-text');

        const savedView = localStorage.getItem('viewMode') || 'grid';
        
        function setViewMode(mode) {
            content.classList.remove('list-view', 'text-view');
            btnGrid.classList.remove('active');
            btnList.classList.remove('active');
            btnText.classList.remove('active');
            
            if (mode === 'list') {
                content.classList.add('list-view');
                btnList.classList.add('active');
            } else if (mode === 'text') {
                content.classList.add('text-view');
                btnText.classList.add('active');
            } else {
                btnGrid.classList.add('active');
            }
            localStorage.setItem('viewMode', mode);
        }

        setViewMode(savedView);

        btnGrid.addEventListener('click', () => setViewMode('grid'));
        btnList.addEventListener('click', () => setViewMode('list'));
        btnText.addEventListener('click', () => setViewMode('text'));
    </script>
</body>
</html>
"""

def generate_html(articles, output_path="index.html"):
    # Get list of archives
    archive_files = sorted(glob.glob("archive-*.html"), reverse=True)
    archives = []
    for f in archive_files:
        filename = os.path.basename(f)
        date_str = filename.replace("archive-", "").replace(".html", "")
        archives.append({"path": filename, "date": date_str})
        
    # Group articles by category
    categorized = {}
    for a in articles:
        cat = a.get("category", "기타")
        if cat not in categorized:
            categorized[cat] = []
        categorized[cat].append(a)
    
    template = Template(HTML_TEMPLATE)
    html_content = template.render(
        date=datetime.now().strftime("%Y-%m-%d %H:%M"),
        articles_by_category=categorized,
        archives=archives
    )
    
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html_content)
    print(f"Generated {output_path}")
