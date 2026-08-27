import os
import sys
import feedparser
import requests

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

SOURCES = {
    "sustainability": [
        ("The Guardian Environment", "https://www.theguardian.com/environment/rss"),
        ("Carbon Brief", "https://www.carbonbrief.org/feed"),
        ("ESG Today", "https://www.esgtoday.com/feed/"),
        ("World Resources Institute", "https://www.wri.org/news/rss.xml"),
    ],
    "esg_cleantech": [
        ("Canary Media", "https://canarymedia.com/feed"),
        ("CleanTechnica", "https://cleantechnica.com/feed/"),
        ("Trellis (GreenBiz)", "https://www.trellis.net/feed/"),
    ],
    "research_telemetry": [
        ("MIT Environment News", "https://news.mit.edu/rss/topic/environment"),
        ("Hugging Face Blog", "https://huggingface.co/blog/feed.xml"),
        ("ArXiv AI Research", "http://export.arxiv.org/rss/cs.AI"),
    ],
    "ai_agents": [
        ("Google DeepMind Blog", "https://deepmind.google/blog/rss.xml"),
        ("Google AI Technology Blog", "https://blog.google/technology/ai/rss/"),
        ("VentureBeat AI", "https://venturebeat.com/category/ai/feed/"),
    ],
}

HN_QUERIES = [
    "sustainability carbon emissions",
    "Scope 3 emissions telemetry",
    "ESG reporting BRSR CSRD",
    "AI agents autonomous workflow",
]

REDDIT_SUBREDDITS = [
    "environment", "sustainability", "energy", "MachineLearning", "artificial", "technology", "Futurology"
]

NEWSAPI_KEY = "8e34b55b561e4f0e921b30934cac03b8"

print("--- TESTING ALL SOURCES ONE BY ONE ---")

print("\n1. RSS FEEDS TEST:")
for cat, feeds in SOURCES.items():
    print(f"\nCategory: [{cat}]")
    for name, url in feeds:
        try:
            feed = feedparser.parse(url)
            count = len(feed.entries)
            if count > 0:
                latest = feed.entries[0].get("title", "")[:60]
                print(f"  ✅ [SUCCESS] {name}: {count} items found. Latest: '{latest}'")
            else:
                print(f"  ⚠️ [WARNING] {name}: 0 items found.")
        except Exception as e:
            print(f"  ❌ [FAILED] {name}: {e}")

print("\n2. HACKER NEWS API TEST:")
for q in HN_QUERIES:
    try:
        resp = requests.get(
            "https://hn.algolia.com/api/v1/search_by_date",
            params={"tags": "story", "query": q, "hitsPerPage": 3},
            timeout=10,
        )
        if resp.status_code == 200:
            hits = resp.json().get("hits", [])
            print(f"  ✅ [SUCCESS] Query '{q}': {len(hits)} hits found.")
        else:
            print(f"  ❌ [FAILED] Query '{q}': HTTP {resp.status_code}")
    except Exception as e:
        print(f"  ❌ [FAILED] Query '{q}': {e}")

print("\n3. REDDIT API TEST:")
client_id = os.environ.get("REDDIT_CLIENT_ID")
client_secret = os.environ.get("REDDIT_CLIENT_SECRET")
if not client_id or not client_secret:
    print("  ⏭️ [SKIPPED] Reddit API (REDDIT_CLIENT_ID / REDDIT_CLIENT_SECRET not configured in local env)")
else:
    print("  ✅ [CONFIGURED] Reddit API credentials found.")

print("\n4. NEWSAPI TEST:")
try:
    headers = {"X-Api-Key": NEWSAPI_KEY}
    url = "https://newsapi.org/v2/everything?q=sustainability+ESG&sortBy=publishedAt&pageSize=3&language=en"
    resp = requests.get(url, headers=headers, timeout=10)
    if resp.status_code == 200:
        articles = resp.json().get("articles", [])
        print(f"  ✅ [SUCCESS] NewsAPI (Key {NEWSAPI_KEY[:8]}...): {len(articles)} articles found. Latest: '{articles[0].get('title', '')[:60]}'")
    else:
        print(f"  ❌ [FAILED] NewsAPI: HTTP {resp.status_code} - {resp.text}")
except Exception as e:
    print(f"  ❌ [FAILED] NewsAPI: {e}")
