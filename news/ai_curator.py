import requests
import json
import logging
import os

def load_api_key(config_path="config.json"):
    config = {}
    try:
        if os.path.exists(config_path):
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
    except Exception:
        pass
    
    api_key = os.environ.get("GEMINI_API_KEY") or config.get("api_key")
    return api_key if api_key else ""

def curate_category(category_name, articles):
    api_key = load_api_key()
    if not api_key:
        logging.error("No Gemini API key found in config.json or environment variables")
        return []

    # Prepare prompt data
    articles_data = []
    for a in articles:
        articles_data.append({
            "link": a["link"],
            "title": a["title_ja"],
            "summary": a["summary_ja"]
        })
    
    prompt = f"""
    당신은 일본의 트렌드를 분석하는 전문 뉴스레터 에디터입니다.
    다음은 '{category_name}' 카테고리에서 수집된 기사들입니다. 이 중에서 한국 독자(개발자, 게이머, 아티스트)에게 가장 유용하고 인기가 있을 만한 핵심 기사들을 최대한 많이(최소 5개에서 최대 10개) 엄선해주세요.
    
    [중요 선정 기준]
    - 단순 나열이 아닌, 현재 웹상에서 가장 조회수나 검색량이 높을 것으로 예상되거나 SNS에서 '좋아요/공유'가 많이 일어날 화제의 기사를 최우선으로 선정하세요.
    - 업계 트렌드에 미치는 파급력과 화제성을 바탕으로 필터링하세요.
    
    기사 데이터:
    {json.dumps(articles_data, ensure_ascii=False, indent=2)}
    
    응답 규칙:
    반드시 선택된 기사들의 목록을 아래 JSON 배열 형식으로만 출력하세요. 다른 텍스트는 절대 포함하지 마세요. (json 형식)
    [
      {{
        "link": "선택한 기사의 원문 링크",
        "title_ko": "매끄럽게 번역되고 다듬어진 한국어 제목",
        "summary_ko": "이 기사가 왜 중요하고 어떤 내용인지 2~3문장으로 아주 잘 요약한 한국어 내용"
      }}
    ]
    """

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"
    headers = {'Content-Type': 'application/json'}
    data = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"response_mime_type": "application/json"}
    }

    try:
        logging.info(f"Asking Gemini to curate '{category_name}'...")
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()
        
        result = response.json()
        text = result["candidates"][0]["content"]["parts"][0]["text"]
        
        # Clean up JSON if model wrapped in markdown
        if text.startswith("```json"):
            text = text[7:-3]
        curated_items = json.loads(text.strip())
        
        # Merge back images and original text
        final_articles = []
        for item in curated_items:
            orig = next((x for x in articles if x["link"] == item["link"]), None)
            if orig:
                final_articles.append({
                    "category": category_name,
                    "source": orig["source"],
                    "title_ja": orig["title_ja"],
                    "summary_ja": orig["summary_ja"],
                    "link": orig["link"],
                    "published": orig["published"],
                    "image_url": orig["image_url"],
                    "title_ko": item.get("title_ko", ""),
                    "summary_ko": item.get("summary_ko", "")
                })
        return final_articles
    except Exception as e:
        logging.error(f"Failed to curate category {category_name}: {e}")
        return []

def curate_articles(articles):
    categorized = {}
    for a in articles:
        cat = a["category"]
        if cat not in categorized:
            categorized[cat] = []
        categorized[cat].append(a)
        
    final_curated = []
    for cat, arts in categorized.items():
        if not arts:
            continue
        curated = curate_category(cat, arts)
        final_curated.extend(curated)
        
    return final_curated
