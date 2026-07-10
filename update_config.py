import json


FEEDS_TO_ENSURE = [
    {
        "category": "Game",
        "name": "IGN Games",
        "url": "https://feeds.ign.com/ign/games-all",
    },
    {
        "category": "Game",
        "name": "Polygon",
        "url": "https://www.polygon.com/rss/index.xml",
    },
    {
        "category": "Game",
        "name": "Automaton (JP)",
        "url": "https://automaton-media.com/feed/",
    },
    {
        "category": "Game Engine",
        "name": "Unity Blog",
        "url": "https://unity.com/blog/rss",
    },
    {
        "category": "Game Engine",
        "name": "Unreal Engine Blog",
        "url": "https://www.unrealengine.com/rss",
    },
    {
        "category": "Game Engine",
        "name": "Godot Engine News",
        "url": "https://godotengine.org/rss.xml",
    },
    {
        "category": "VTuber",
        "name": "PANORA VTuber (JP)",
        "url": "https://panora.tokyo/archives/category/vtuber/feed",
    },
    {
        "category": "Anime",
        "name": "Anime News Network",
        "url": "https://www.animenewsnetwork.com/news/rss.xml",
    },
    {
        "category": "Anime",
        "name": "Crunchyroll News",
        "url": "https://cr-news-api-service.prd.crunchyrollsvc.com/v1/en-US/rss",
    },
    {
        "category": "Cosplay/Event",
        "name": "Japan Cosplay Committee (JP)",
        "url": "https://jpcc.or.jp/feed/",
    },
]


with open("config.json", "r", encoding="utf-8") as handle:
    config = json.load(handle)

managed_by_url = {feed["url"]: feed for feed in FEEDS_TO_ENSURE}
new_feeds = []
seen_urls = set()

for current in config.get("feeds", []):
    url = str(current.get("url") or "").strip()
    if not url or url in seen_urls:
        continue
    new_feeds.append(managed_by_url.get(url, current))
    seen_urls.add(url)

for feed in FEEDS_TO_ENSURE:
    if feed["url"] not in seen_urls:
        new_feeds.append(feed)
        seen_urls.add(feed["url"])

config["feeds"] = new_feeds

with open("config.json", "w", encoding="utf-8", newline="\n") as handle:
    json.dump(config, handle, indent=2, ensure_ascii=False)
    handle.write("\n")
