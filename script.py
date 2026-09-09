"""
Daily LinkedIn content bot — v3.2 Pure Text-Only Edition (linkedin-vis)
(multi-source + Gemini candidate scoring + 5 storytelling rotation + tagline + text-only publishing)

Pipeline:
  Multi-sources (RSS categories + Hacker News + Reddit + NewsAPI)
    -> dedupe + remove already-used links / similar titles
    -> Gemini scores every remaining candidate (0-100) using Environmental/ESG rubric
    -> take the top-scoring candidate
    -> Gemini writes the pure text post, rotating 5 storytelling templates + avoiding repeat hooks
    -> tagline & hashtags appended
    -> text-only post published directly to LinkedIn REST API
    -> logs the result as a GitHub Issue, updates content_memory.json
"""

import os
import sys
import json
import re
import time
import difflib
from datetime import date

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

import feedparser
import requests
from google import genai

# ---------------------------------------------------------------------------
# Content Sources — Sustainability, ESG, Telemetry & AI Agents
# ---------------------------------------------------------------------------
SOURCES = {
    "sustainability": [
        "https://www.theguardian.com/environment/rss",
        "https://www.carbonbrief.org/feed",
        "https://www.esgtoday.com/feed/",
        "https://www.wri.org/news/rss.xml",
    ],
    "esg_cleantech": [
        "https://canarymedia.com/feed",
        "https://cleantechnica.com/feed/",
        "https://www.trellis.net/feed/",
    ],
    "research_telemetry": [
        "https://news.mit.edu/rss/topic/environment",
        "https://huggingface.co/blog/feed.xml",
        "http://export.arxiv.org/rss/cs.AI",
    ],
    "ai_agents": [
        "https://deepmind.google/blog/rss.xml",
        "https://blog.google/technology/ai/rss/",
        "https://venturebeat.com/category/ai/feed/",
    ],
}

HN_QUERIES = [
    "sustainability carbon emissions", "Scope 3 emissions telemetry",
    "ESG reporting BRSR CSRD", "environmental sensors data",
    "AI agents autonomous workflow", "CleanTech energy grid",
    "industrial decarbonization", "climate data analytics",
    "green computing edge AI", "carbon footprint tracking",
]

REDDIT_SUBREDDITS = [
    "environment", "sustainability", "energy", "MachineLearning",
    "artificial", "technology", "Futurology",
]

NEWSAPI_KEY = os.environ.get("NEWSAPI_KEY", "").strip()

CLICKBAIT_PATTERNS = [
    r"you won'?t believe", r"\bshocking\b", r"\bgone wrong\b",
    r"^\d+ (things|reasons|ways) ", r"\bclickbait\b",
]

MAX_CANDIDATES_TO_SCORE = 60

# ---------------------------------------------------------------------------
# Storytelling Templates
# ---------------------------------------------------------------------------
TEMPLATES = {
    1: """TEMPLATE 1: "The Regulatory & Supply Chain Impact Teardown"
   - Head (The Urgent Signal): The first line must be a compelling, direct hook stating a specific regulatory or market mandate (BRSR Core, EU CBAM, CSRD, Scope 3 assurance, SEC, or ISO net-zero) and why non-compliance is suddenly expensive. (Max 18 words).
   - Body (The Operational Breakdown): Break down 2-3 concrete operational realities. What must Tier-1 suppliers or corporate ESG teams actually change? Include hard numbers (deadlines, carbon border tariffs, assurance scopes).
   - Tail (Actionable Takeaway): Provide 1 clear, strategic imperative for leadership. Conclude with a sharp, technical discussion question that invites experienced peers to share how they are solving it.""",

    2: """TEMPLATE 2: "The Carbon Accounting & Data Reality"
   - Head (The Hard Metric): Start with an eye-opening number or metric (emissions intensity, Scope 3 audit failure rates, carbon credit discount, or energy conversion metric). Make the reader stop scrolling immediately.
   - Body (The Calculation & Pitfalls): Explain the underlying methodology. Where are companies miscalculating? Contrast reported claims vs physical emissions math (grid factors, supplier estimates, emission factor errors).
   - Tail (The Solution Architecture): Outline the right data architecture or mitigation step. End with a focused question on measurement standards.""",

    3: """TEMPLATE 3: "The Engineering & Ground-Level Reality Check"
   - Head (The Plant-Floor / Field Reality): An authentic observation contrasting boardroom net-zero commitments with ground-level industrial reality (water recycling, constructed wetlands, captive renewables, heat recovery).
   - Body (The Engineering Dilemma): Share the practical friction points: CAPEX vs payback, grid interconnection delays, sensor calibration, or local biodiversity impacts. Ground it in technical facts.
   - Tail (The Strategic Lesson): What works in practice versus what only looks good on a corporate slide deck. End with a technical peer question.""",

    4: """TEMPLATE 4: "The Executive Sunday 5-Point Brief"
   - Head (The Executive Horizon): A powerful 1-sentence macro synthesis of where ESG, carbon regulation, and climate tech are moving this upcoming week.
   - Body (The 5 Strategic Developments): Exactly 5 distinct, emoji-bulleted points (📊 Policy, ⚡ Tech, 💰 Capital, 🏭 Industry, 🔍 Audit) covering key shifts with exact numbers and organizations.
   - Tail (The Monday Morning Priority): One high-leverage question or focus area for CFOs, Sustainability Heads, and Operations Leaders."""
}

POST_PROMPT_TEMPLATE = """
You are writing a LinkedIn post for Arunachalam Venkatachalapathy, an authoritative ESG & Sustainability Leader with deep expertise in BRSR Core, GHG Carbon Accounting (Scope 1, 2, 3), Environmental Engineering, and Climate Tech.

Target Audience: 8,300+ Sustainability Directors, Chief Sustainability Officers, ESG Analysts, Environmental Engineers, and Corporate Leaders who demand actionable depth, real numbers, and technical substance.

Source headline: {title}
Source category: {category}
Source summary: {summary}
Source link: {link}

Recently covered topics (avoid repeating these themes):
{recent_topics}

Recently used opening hooks (write a genuinely different opening style/rhythm than these):
{recent_hooks}

Available storytelling structures:
{templates_list}

Recently used structures:
{recent_templates}

Recent high-performing benchmarks:
{recent_successes}

CRITICAL EDITORIAL GUIDELINES (VIRAL & PROFESSIONAL):
1. **AUTHENTIC EXPERT VOICE:** Write like an experienced sustainability consultant who has audited factories, calculated Scope 3 supply chain emissions, and reviewed BRSR disclosures. Confident, direct, and pragmatic.
2. **BAN CLICHÉ SYNTHETIC CONTRASTS:** NEVER use the tired formulas:
   - "It isn't X — it's Y" or "isn't about X — it's about Y"
   - "We keep treating X like Y, right up until Z"
   - "Think about that number for a second"
   - "The real question isn't whether X matters..."
   - "Most leaders do X, but the real test is Y"
   Write natural, insightful, substance-driven prose instead.
3. **GROUND IN SPECIFICS:** Use real metrics, percentages, dollar/rupee amounts, emissions units (tCO2e, kg CO2/kWh), regulations (SEBI BRSR, EU CBAM, CSRD, GRI, GHG Protocol), or engineering concepts.
4. **READABILITY & SCANNABILITY:** 1-2 sentence paragraphs maximum. Clean line breaks. No dense blocks of text.
5. **LENGTH:** 140-230 words for the post body.
6. **HASHTAGS:** Exactly 3 hyper-relevant hashtags (e.g., #Sustainability #BRSR #ClimateTech).
7. **FIRST COMMENT GENERATION:** Generate a high-value "First Comment" (50-80 words) to be posted within the first 5 minutes. The comment should add a practical tip, cite an extra benchmark/stat, or pose a nuanced follow-up question to ignite peer discussion.

Output format — EXACTLY this, nothing else:
TEMPLATE: <number 1-4 of the structure you used>
---
<the finished post text, no title, no notes, no sign-off, no hashtags>
---
<3 hashtags, space-separated, each starting with #>
---
<First Comment text for the Golden Hour discussion starter>
"""

SCORING_PROMPT_TEMPLATE = """
You are the Chief Content Scout for Arunachalam Venkatachalapathy, an ESG & Sustainability Leader with 8,300+ professional followers.
Score each candidate story below from 0-100 based strictly on its value to sustainability directors, environmental engineers, and corporate compliance leaders:

- ESG & Climate Relevance (0-35): Is this directly relevant to sustainability, carbon emissions, BRSR/CBAM/CSRD compliance, clean energy, or environmental tech? (Give ZERO to generic tech, politics, crypto, or unrelated general news).
- Strategic & Professional Value (0-30): Does this provide actionable insight for corporate leaders, supply chain heads, or ESG analysts?
- Concrete Data & Substance (0-20): Does the story contain verifiable data, specific numbers, metrics, or case studies rather than vague buzzwords?
- Novelty & Freshness (0-15): Is this a timely breakthrough or fresh angle?

Candidates (JSON array, each with an "id"):
{candidates_json}

Respond with ONLY a JSON array (no markdown fences, no commentary) of the top 5 candidates,
each formatted as: {{"id": <id>, "score": <total 0-100>, "reason": "<one short sentence>"}}
Sort descending by score.
"""

MEMORY_FILE = "content_memory.json"
LINKEDIN_VERSION = "202607"


# ---------------------------------------------------------------------------
# Memory Management
# ---------------------------------------------------------------------------
def load_memory():
    if os.path.exists(MEMORY_FILE):
        with open(MEMORY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def save_memory(memory):
    with open(MEMORY_FILE, "w", encoding="utf-8") as f:
        json.dump(memory[-200:], f, indent=2)


def used_links_set(memory):
    return {entry["link"] for entry in memory if "link" in entry}


def recent_topics_text(memory, n=5):
    recent = memory[-n:]
    if not recent:
        return "(none yet)"
    return "\n".join(f"- {entry['title']}" for entry in recent if "title" in entry)


def recent_hooks_text(memory, n=4):
    recent = [e for e in memory[-n:] if e.get("hook")]
    if not recent:
        return "(none yet)"
    return "\n".join(f"- {e['hook']}" for e in recent)


def recent_templates_text(memory, n=3):
    recent = [str(e["template"]) for e in memory[-n:] if e.get("template")]
    return ", ".join(recent) if recent else "(none yet)"


def recent_successes_text(memory, n=3):
    successes = [e for e in memory if e.get("performed_well")]
    if not successes:
        return (
            "- Benchmark 1: Top 1,000 Indian corporates face 53% surge in FY25 emissions\n"
            "  Format style: Led with the raw data point, audited Scope 3 supply chain risks, avoided buzzwords.\n\n"
            "- Benchmark 2: SEBI BRSR Core mandatory assurance roadmap for value chain\n"
            "  Format style: Specific clause citations, compliance timeline, 3 tactical audit-readiness steps for Tier-1 vendors."
        )
    recent = successes[-n:]
    return "\n\n".join(f"- Title: {e['title']}\n  Hook: {e.get('hook', 'N/A')}\n  Template: {e.get('template', 'N/A')}" for e in recent)


def update_performance_engine(memory, access_token):
    """
    Constant Improvement Engine:
    Reads the last 15 posts from memory, checks their actual engagement on LinkedIn,
    and dynamically tags top posts as 'performed_well' so the AI learns from them.
    Gracefully handles restricted permissions without crashing or spamming.
    """
    import urllib.parse

    recent_indices = list(range(max(0, len(memory) - 15), len(memory)))

    if access_token:
        for idx in recent_indices:
            entry = memory[idx]
            post_id = entry.get("post_id")
            if not post_id or not post_id.startswith("urn:li:"):
                continue

            safe_urn = urllib.parse.quote(post_id, safe="")
            url = f"https://api.linkedin.com/v2/socialActions/{safe_urn}"
            headers = {
                "Authorization": f"Bearer {access_token}",
                "X-Restli-Protocol-Version": "2.0.0",
            }
            try:
                res = requests.get(url, headers=headers, timeout=10)
                if res.status_code == 200:
                    data = res.json()
                    likes    = data.get("likesSummary",   {}).get("totalLikes", 0)
                    comments = data.get("commentsSummary", {}).get("totalFirstLevelComments", 0)
                    memory[idx]["engagement_score"] = likes + (comments * 2)
                elif res.status_code == 403:
                    # 403 Forbidden is normal for standard w_member_social tokens; silently ignore
                    pass
                else:
                    print(f"Improvement Engine: LinkedIn API {res.status_code} for {post_id}")
            except Exception:
                pass

    # Rank whatever we have scored (even from prior runs)
    scored_indices = [i for i in recent_indices if "engagement_score" in memory[i]]
    if len(scored_indices) >= 3:
        scored_indices.sort(key=lambda i: memory[i]["engagement_score"], reverse=True)
        top_n = max(1, len(scored_indices) // 3)  # Top 33%
        top_threshold = memory[scored_indices[top_n - 1]]["engagement_score"]

        for i in scored_indices:
            score = memory[i]["engagement_score"]
            # Must have >0 engagement to earn the "performed_well" flag
            memory[i]["performed_well"] = (score >= top_threshold and score > 0)

        top_posts = [memory[i]["title"][:60] for i in scored_indices[:top_n]]
        print(f"Improvement Engine: Tagged {top_n} top post(s) as high-performing: {top_posts}")


# ---------------------------------------------------------------------------
# Ingestion
# ---------------------------------------------------------------------------
def fetch_rss():
    items = []
    for category, urls in SOURCES.items():
        for url in urls:
            try:
                resp = requests.get(url, timeout=10)
                feed = feedparser.parse(resp.content)
                for entry in feed.entries[:6]:
                    items.append({
                        "title": entry.get("title", ""),
                        "summary": entry.get("summary", entry.get("title", "")),
                        "link": entry.get("link", ""),
                        "category": category,
                        "source": feed.feed.get("title", url),
                    })
            except Exception as e:
                print(f"RSS fetch failed for {url}: {e}")
    return items


def fetch_hackernews():
    items = []
    for query in HN_QUERIES:
        try:
            resp = requests.get(
                "https://hn.algolia.com/api/v1/search_by_date",
                params={"tags": "story", "query": query, "hitsPerPage": 4},
                timeout=15,
            )
            resp.raise_for_status()
            for hit in resp.json().get("hits", []):
                title = hit.get("title") or ""
                url = hit.get("url") or f"https://news.ycombinator.com/item?id={hit.get('objectID')}"
                if title:
                    items.append({
                        "title": title, "summary": title, "link": url,
                        "category": "community", "source": "Hacker News"
                    })
        except Exception as e:
            print(f"Hacker News fetch failed for '{query}': {e}")
    return items


def fetch_reddit():
    client_id = os.environ.get("REDDIT_CLIENT_ID")
    client_secret = os.environ.get("REDDIT_CLIENT_SECRET")
    if not client_id or not client_secret:
        return []
    try:
        resp = requests.post(
            "https://www.reddit.com/api/v1/access_token",
            auth=(client_id, client_secret),
            data={"grant_type": "client_credentials"},
            headers={"User-Agent": "linkedin-content-bot/1.0"},
            timeout=15,
        )
        resp.raise_for_status()
        token = resp.json()["access_token"]
    except Exception:
        return []

    items = []
    headers = {"Authorization": f"Bearer {token}", "User-Agent": "linkedin-content-bot/1.0"}
    for sub in REDDIT_SUBREDDITS:
        try:
            resp = requests.get(
                f"https://oauth.reddit.com/r/{sub}/top",
                params={"t": "week", "limit": 4},
                headers=headers,
                timeout=15,
            )
            resp.raise_for_status()
            for post in resp.json().get("data", {}).get("children", []):
                data = post.get("data", {})
                title = data.get("title", "")
                link = "https://reddit.com" + data.get("permalink", "")
                if title:
                    items.append({
                        "title": title, "summary": title, "link": link,
                        "category": "community", "source": f"r/{sub}"
                    })
        except Exception as e:
            print(f"Reddit fetch failed for r/{sub}: {e}")
    return items


def fetch_newsapi(custom_queries=None):
    if not NEWSAPI_KEY:
        print("NEWSAPI_KEY not set — skipping NewsAPI source")
        return []
    items = []
    headers = {"X-Api-Key": NEWSAPI_KEY}
    queries = custom_queries if custom_queries else ["sustainability ESG AI", "Scope 3 carbon emissions", "AI agents autonomous workflow"]
    for q in queries:
        try:
            url = f"https://newsapi.org/v2/everything?q={requests.utils.quote(q)}&sortBy=publishedAt&pageSize=4&language=en"
            resp = requests.get(url, headers=headers, timeout=15)
            if resp.status_code == 200:
                for art in resp.json().get("articles", []):
                    title = art.get("title", "").strip()
                    summary = art.get("description") or title
                    link = art.get("url", "")
                    if title and link and not title.startswith("[Removed]"):
                        items.append({
                            "title": title, "summary": summary, "link": link,
                            "category": "breaking_news", "source": f"NewsAPI ({art.get('source', {}).get('name', '')})"
                        })
        except Exception as e:
            print(f"NewsAPI fetch error for '{q}': {e}")
    return items


def fetch_exa(custom_queries=None):
    api_key = os.environ.get("EXA_API_KEY", "").strip()
    if not api_key:
        return []
    items = []
    queries = custom_queries if custom_queries else [
        "technical challenges scope 3 emissions telemetry",
        "latest AI agent workflows in enterprise",
        "biggest trending controversy in tech startups this week",
        "recent breakthroughs in carbon accounting data"
    ]
    url = "https://api.exa.ai/search"
    headers = {"x-api-key": api_key, "Content-Type": "application/json"}
    
    from datetime import datetime, timedelta
    start_date = (datetime.utcnow() - timedelta(days=3)).strftime("%Y-%m-%dT%H:%M:%S.000Z")
    
    for q in queries:
        try:
            payload = {
                "query": q,
                "numResults": 3,
                "useAutoprompt": True,
                "startPublishedDate": start_date
            }
            resp = requests.post(url, headers=headers, json=payload, timeout=15)
            if resp.status_code == 200:
                for res in resp.json().get("results", []):
                    items.append({
                        "title": res.get("title", ""),
                        "summary": res.get("title", ""),
                        "link": res.get("url", ""),
                        "category": "deep_research",
                        "source": "Exa AI Search"
                    })
        except Exception as e:
            print(f"Exa fetch error for '{q}': {e}")
    return items

def fetch_tavily(custom_queries=None):
    api_key = os.environ.get("TAVILY_API_KEY", "").strip()
    if not api_key:
        return []
    items = []
    url = "https://api.tavily.com/search"
    headers = {"Content-Type": "application/json"}
    queries = custom_queries if custom_queries else [
        "latest trending news in artificial intelligence and Nvidia",
        "biggest business or tech news today",
        "top stories in climate tech and startups today"
    ]
    for q in queries:
        try:
            payload = {
                "api_key": api_key,
                "query": q,
                "search_depth": "basic",
                "include_answer": False,
                "max_results": 4,
                "topic": "news",
                "days": 2
            }
            resp = requests.post(url, headers=headers, json=payload, timeout=15)
            if resp.status_code == 200:
                for res in resp.json().get("results", []):
                    items.append({
                        "title": res.get("title", ""),
                        "summary": res.get("content", ""),
                        "link": res.get("url", ""),
                        "category": "trending_news",
                        "source": "Tavily AI Search"
                    })
        except Exception as e:
            print(f"Tavily fetch error for '{q}': {e}")
    return items

import random
from datetime import datetime

def fetch_all_candidates():
    day_of_week = datetime.utcnow().strftime("%A")
    print(f"Today is {day_of_week}. Implementing Thematic Schedule.")
    
    pool = []

    if day_of_week == "Monday":
        print("Theme: Climate Tech & Industrial Decarbonization (Source: Exa)")
        pool = fetch_exa([
            "climate tech industrial decarbonization",
            "green hydrogen hard to abate sectors",
            "industrial carbon capture clean tech innovations"
        ])
    elif day_of_week == "Tuesday":
        print("Theme: BRSR, CSRD, CBAM & ESG Regulatory Mandates (Source: Exa)")
        pool = fetch_exa([
            "SEBI BRSR Core assurance guidelines India",
            "EU CBAM carbon border adjustment mechanism compliance",
            "CSRD Scope 3 value chain sustainability reporting"
        ])
    elif day_of_week == "Wednesday":
        print("Theme: GHG Accounting, Carbon Markets & Nature Solutions (Source: Exa/Tavily)")
        pool = fetch_exa([
            "GHG Protocol Scope 3 carbon accounting methodology",
            "carbon credit integrity removal vs offset standards",
            "constructed wetlands industrial wastewater nature solutions"
        ])
    elif day_of_week == "Thursday":
        print("Theme: Geospatial AI, Remote Sensing & Environmental Monitoring (Source: Exa)")
        pool = fetch_exa([
            "satellite remote sensing methane emissions climate",
            "GIS spatial data environmental risk supply chain",
            "spatial monitoring deforestation water stress climate tech"
        ])
    elif day_of_week == "Friday":
        print("Theme: Sustainable Finance, Green Bonds & Transition Capital (Source: Tavily)")
        pool = fetch_tavily([
            "green bonds sustainable finance India global",
            "climate tech venture capital investment trends",
            "transition finance corporate ESG capital allocation"
        ])
    elif day_of_week == "Saturday":
        print("Theme: Plant-Floor & Environmental Engineering Reality (Source: NewsAPI & Reddit)")
        pool = fetch_newsapi([
            "industrial wastewater zero liquid discharge",
            "renewable energy grid integration industrial decarbonization"
        ]) + fetch_reddit()
    elif day_of_week == "Sunday":
        print("Theme: Executive Weekly ESG & Climate Strategy Brief (Source: Tavily)")
        pool = fetch_tavily([
            "global ESG regulations corporate sustainability shifts this week",
            "climate tech breakthroughs policy developments summary"
        ])

    if len(pool) < 5:
        print("Primary theme source returned too few articles, falling back to mixed ESG pool.")
        pool.extend(fetch_rss()[:5] + fetch_exa(["BRSR ESG carbon accounting climate tech"])[:10] + fetch_tavily(["corporate sustainability ESG green tech"])[:10])

    random.shuffle(pool)
    return pool


# ---------------------------------------------------------------------------
# Filtering
# ---------------------------------------------------------------------------
def cluster_sizes(candidates, threshold=0.55):
    titles = [c["title"].lower() for c in candidates]
    sizes = []
    for i, t in enumerate(titles):
        count = 1
        for j, other in enumerate(titles):
            if i != j and difflib.SequenceMatcher(None, t, other).ratio() >= threshold:
                count += 1
        sizes.append(count)
    return sizes


def is_clickbait(title):
    lowered = title.lower()
    return any(re.search(p, lowered) for p in CLICKBAIT_PATTERNS)


import math

def compute_embedding(client, text, retries=3):
    if not client or not text:
        return None
    for attempt in range(1, retries + 1):
        try:
            resp = client.models.embed_content(
                model="gemini-embedding-2",
                contents=text,
            )
            return resp.embeddings[0].values
        except Exception as e:
            if attempt == retries:
                print(f"Embedding error: {e}")
                return None
            time.sleep(2 * attempt)
    return None

def cosine_similarity(v1, v2):
    if not v1 or not v2: return 0.0
    dot = sum(a * b for a, b in zip(v1, v2))
    norm_a = math.sqrt(sum(a * a for a in v1))
    norm_b = math.sqrt(sum(b * b for b in v2))
    if norm_a == 0 or norm_b == 0: return 0.0
    return dot / (norm_a * norm_b)

def is_similar_topic(title, recent_titles, threshold=0.55):
    lowered = title.lower()
    for recent in recent_titles:
        if difflib.SequenceMatcher(None, lowered, recent.lower()).ratio() >= threshold:
            return True
    return False

def is_semantically_similar(client, title, summary, recent_embeddings, threshold=0.82):
    if not client:
        return False, None
    text = f"{title}\n{summary}"
    emb = compute_embedding(client, text)
    if not emb:
        return False, None
    for recent_emb in recent_embeddings:
        if cosine_similarity(emb, recent_emb) >= threshold:
            return True, emb
    return False, emb

def dedupe_and_filter(items, memory):
    used_links = {entry["link"] for entry in memory if "link" in entry}
    recent_titles = [entry["title"] for entry in memory[-30:] if entry.get("title")]
    
    # Load recent embeddings
    recent_embeddings = [entry["embedding"] for entry in memory[-15:] if entry.get("embedding")]
    
    client = gemini_client()
    
    seen_links = set()
    filtered = []
    for item in items:
        link = item.get("link", "")
        title = item.get("title", "")
        summary = item.get("summary", "")
        if not link or not title:
            continue
        if link in used_links or link in seen_links:
            continue
        if is_clickbait(title):
            continue
        # Cheap difflib pass
        if is_similar_topic(title, recent_titles):
            continue
        
        # Semantic pass
        is_sim, emb = is_semantically_similar(client, title, summary, recent_embeddings)
        if is_sim:
            continue
            
        item["embedding"] = emb  # Store for this run
        seen_links.add(link)
        filtered.append(item)
    return filtered


# ---------------------------------------------------------------------------
# Gemini API & Scoring
# ---------------------------------------------------------------------------
def gemini_client():
    api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not api_key:
        return None
    try:
        return genai.Client(api_key=api_key)
    except Exception:
        return None


def generate_with_retry(client, model, contents, retries=3, base_delay=4):
    last_error = None
    for attempt in range(1, retries + 1):
        try:
            return client.models.generate_content(model=model, contents=contents)
        except Exception as e:
            last_error = e
            time.sleep(base_delay * attempt)
    raise last_error


def score_candidates(client, candidates):
    if not candidates:
        return []
    pool = candidates[:MAX_CANDIDATES_TO_SCORE]
    if not client:
        return [{"id": 0, "score": 85, "reason": "first available candidate (local preview)", "candidate": pool[0]}]

    sizes = cluster_sizes(pool)
    slim = [
        {
            "id": i,
            "title": c["title"],
            "category": c["category"],
            "source": c["source"],
            "covered_by_n_sources": sizes[i],
        }
        for i, c in enumerate(pool)
    ]
    prompt = SCORING_PROMPT_TEMPLATE.format(candidates_json=json.dumps(slim, indent=2))
    for m_name in ["gemma-4-26b-a4b-it", "gemini-3.6-flash", "gemini-3.6-pro"]:
        try:
            response = generate_with_retry(client, m_name, prompt)
            if response and response.text:
                raw = response.text.strip()
                raw = re.sub(r"^```(json)?|```$", "", raw.strip(), flags=re.MULTILINE).strip()
                ranked = json.loads(raw)
                for r in ranked:
                    idx = r.get("id")
                    if isinstance(idx, int) and 0 <= idx < len(pool):
                        r["candidate"] = pool[idx]
                return [r for r in ranked if "candidate" in r]
        except Exception as e:
            print(f"Scoring fallback for model {m_name}: {e}")


    return [{"id": 0, "score": 85, "reason": "first candidate (scoring fallback)", "candidate": pool[0]}]


MAX_HASHTAGS = 3
MIN_WORDS = 110
MAX_WORDS = 250

def validate_post(post_body: str, hashtags: str) -> list[str]:
    """Return a list of validation failure reasons; empty list = passed."""
    failures = []
    word_count = len(post_body.split())
    if not (MIN_WORDS <= word_count <= MAX_WORDS):
        failures.append(f"word count {word_count} outside [{MIN_WORDS}, {MAX_WORDS}]")
    hashtag_count = len(re.findall(r"#\w+", hashtags))
    if hashtag_count > MAX_HASHTAGS:
        failures.append(f"hashtag wall: {hashtag_count} hashtags (max {MAX_HASHTAGS})")
    if hashtag_count == 0:
        failures.append("no hashtags found")

    # Hook validation — first line must be a short, punchy tagline
    first_line = post_body.strip().split("\n")[0].strip()
    weak_openers = ("a recent", "this week", "the world", "in a recent", "according to", "researchers", "new report")
    if any(first_line.lower().startswith(w) for w in weak_openers):
        failures.append(f"first line starts with a weak opener ('{first_line[:60]}...'), rewrite as a punchy tagline")
    if len(first_line.split()) > 20:
        failures.append(f"first line is too long ({len(first_line.split())} words) to be a tagline hook — make it punchier")

    # Cliche ban — reject generic AI contrast patterns
    banned_cliches = (
        "it isn't", "is not about", "isn't about", "we keep treating", 
        "think about that number", "the real question isn't", 
        "most leaders treat", "how is your team handling", 
        "how is your team approaching"
    )
    body_lower = post_body.lower()
    for phrase in banned_cliches:
        if phrase in body_lower:
            failures.append(f"contains banned cliche phrase '{phrase}', rewrite with direct, authentic engineering analysis")

    return failures

def generate_post(item, memory):
    client = gemini_client()
    templates_list = "\n".join(f"{k}. {v}" for k, v in TEMPLATES.items())
    
    from datetime import datetime
    day_of_week = datetime.utcnow().strftime("%A")
    forced_template_instruction = ""
    if day_of_week == "Sunday":
        forced_template_instruction = "CRITICAL INSTRUCTION: Today is Sunday. You MUST strictly use TEMPLATE 4 (The Executive Sunday 5-Point Brief). Do NOT choose any other template. Ensure exactly 5 bullet points."
    
    base_prompt = POST_PROMPT_TEMPLATE.format(
        title=item["title"],
        category=item.get("category", "general"),
        summary=item["summary"],
        link=item["link"],
        recent_topics=recent_topics_text(memory),
        recent_hooks=recent_hooks_text(memory),
        templates_list=templates_list,
        recent_templates=recent_templates_text(memory),
        recent_successes=recent_successes_text(memory),
    )
    
    if forced_template_instruction:
        base_prompt += f"\n\n{forced_template_instruction}"
    
    raw = None
    if client:
        prompt = base_prompt
        for attempt in range(1, 4):  # Max 3 attempts
            for m_name in ["gemini-3.6-flash", "gemma-4-26b-a4b-it"]:
                try:
                    response = generate_with_retry(client, m_name, prompt)
                    if response and response.text:
                        raw = response.text.strip()
                        parts = raw.split("---")
                        if len(parts) < 3:
                            print(f"Warning: Malformed output on attempt {attempt}")
                            raw = None
                            continue
                        
                        post_body = parts[1].strip()
                        hashtags = parts[2].strip()
                        failures = validate_post(post_body, hashtags)
                        
                        if not failures:
                            break  # Passed validation
                        
                        print(f"Validation failed on attempt {attempt}: {', '.join(failures)}")
                        prompt = base_prompt + f"\n\nYOUR PREVIOUS ATTEMPT FAILED VALIDATION: {', '.join(failures)}. Please fix these errors and ensure exactly 3 hashtags, {MIN_WORDS}-{MAX_WORDS} words, and NO cliche phrases."
                        raw = None
                        break  # Break inner loop to retry outer loop
                except Exception as exc:
                    print(f"Post generation error for model {m_name}: {exc}")
            if raw:
                break # We found a valid raw


    if not raw:
        # Fallback post if Gemini is unavailable — authentic ESG & Scope 3 audit reality
        title_clean = re.sub(r'<[^>]+>', '', item['title']).strip()
        summary_raw = item.get("summary") or item.get("title", "")
        summary_clean = re.sub(r'<[^>]+>', '', summary_raw).strip()[:140]
        raw = (
            "TEMPLATE: 1\n---\n"
            f"{title_clean[:90]}.\n\n"
            f"{summary_clean}\n\n"
            "For corporate sustainability teams and Tier-1 suppliers, the practical mandate is direct: audit readiness and verifiable Scope 3 data cannot wait until year-end reporting.\n\n"
            "What specific challenges is your organization encountering with primary supplier emission factors this quarter?\n---\n"
            "#Sustainability #BRSR #ClimateTech\n---\n"
            "Key question for practitioners: Are you seeing primary supplier data meeting reasonable assurance standards yet, or are proxy factors still dominating your Scope 3 inventory?"
        )

    template_used = None
    match = re.search(r"TEMPLATE:\s*(\d)", raw)
    if match:
        template_used = int(match.group(1))

    parts = raw.split("---")
    post_body = parts[1].strip() if len(parts) > 1 else raw.strip()
    hashtags = parts[2].strip() if len(parts) > 2 else "#Sustainability #BRSR #ClimateTech"
    first_comment = parts[3].strip() if len(parts) > 3 else ""
    
    # Enforce hashtag truncation just in case
    hash_list = re.findall(r"(#\w+)", hashtags)
    if len(hash_list) > MAX_HASHTAGS:
        hashtags = " ".join(hash_list[:MAX_HASHTAGS])

    post_text = post_body
    if hashtags and hashtags not in post_text:
        post_text += f"\n\n{hashtags}"

    hook = post_body.split("\n")[0].strip()
    return post_text, template_used, hook, first_comment


# ---------------------------------------------------------------------------
# Pure Text-Only LinkedIn & Reddit Publishing
# ---------------------------------------------------------------------------

def with_retry(fn, *args, retries=3, base_delay=5, retryable_statuses=(429, 500, 502, 503, 504), **kwargs):
    last_exc = None
    for attempt in range(1, retries + 1):
        try:
            return fn(*args, **kwargs)
        except requests.exceptions.RequestException as e:
            status = getattr(e.response, "status_code", None)
            if status is not None and status not in retryable_statuses:
                raise  # don't retry on 4xx auth/validation errors, fail fast
            last_exc = e
            if attempt < retries:
                time.sleep(base_delay * attempt)
    raise last_exc


def get_person_urn(access_token):
    resp = requests.get(
        "https://api.linkedin.com/v2/userinfo",
        headers={"Authorization": f"Bearer {access_token}"},
        timeout=15,
    )
    resp.raise_for_status()
    return f"urn:li:person:{resp.json()['sub']}"


def post_to_linkedin(access_token, person_urn, text):
    """Publish a pure text post to LinkedIn. No images."""
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        "X-Restli-Protocol-Version": "2.0.0",
        "LinkedIn-Version": LINKEDIN_VERSION,
    }
    payload = {
        "author": person_urn,
        "commentary": text,
        "visibility": "PUBLIC",
        "distribution": {
            "feedDistribution": "MAIN_FEED",
            "targetEntities": [],
            "thirdPartyDistributionChannels": [],
        },
        "lifecycleState": "PUBLISHED",
        "isReshareDisabledByAuthor": False,
    }
    resp = with_retry(
        requests.post,
        "https://api.linkedin.com/rest/posts",
        headers=headers,
        json=payload,
        timeout=15
    )
    if resp.status_code == 201:
        return True, resp.headers.get("x-restli-id", "unknown")
    return False, f"{resp.status_code}: {resp.text}"


def post_comment_to_linkedin(access_token, person_urn, post_id, comment_text):
    """Attempt to post an initial discussion-starter comment to seed early engagement."""
    if not comment_text or not post_id or not post_id.startswith("urn:li:"):
        return False, "skipped"
    import urllib.parse
    safe_urn = urllib.parse.quote(post_id, safe="")
    url = f"https://api.linkedin.com/rest/socialActions/{safe_urn}/comments"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        "LinkedIn-Version": LINKEDIN_VERSION,
        "X-Restli-Protocol-Version": "2.0.0",
    }
    payload = {
        "actor": person_urn,
        "message": {"text": comment_text}
    }
    try:
        resp = with_retry(requests.post, url, headers=headers, json=payload, timeout=15)
        if resp.status_code in (200, 201):
            return True, "Commented successfully"
        return False, f"API {resp.status_code}"
    except Exception as e:
        return False, str(e)


def get_reddit_user_token():
    client_id = os.environ.get("REDDIT_CLIENT_ID")
    client_secret = os.environ.get("REDDIT_CLIENT_SECRET")
    username = os.environ.get("REDDIT_USERNAME")
    password = os.environ.get("REDDIT_PASSWORD")
    if not all([client_id, client_secret, username, password]):
        return None
    try:
        resp = requests.post(
            "https://www.reddit.com/api/v1/access_token",
            auth=(client_id, client_secret),
            data={
                "grant_type": "password",
                "username": username,
                "password": password,
            },
            headers={"User-Agent": "linkedin-content-bot/1.0"},
            timeout=15,
        )
        resp.raise_for_status()
        return resp.json().get("access_token")
    except Exception as e:
        print(f"Reddit user auth failed: {e}")
        return None


def post_to_reddit(title, text, subreddit="sustainability"):
    user_token = get_reddit_user_token()
    if not user_token:
        print("Skipping Reddit publishing (REDDIT_USERNAME / REDDIT_PASSWORD not configured)")
        return False, "not configured"
    headers = {"Authorization": f"Bearer {user_token}", "User-Agent": "linkedin-content-bot/1.0"}
    try:
        data = {
            "sr": subreddit,
            "kind": "self",
            "title": title[:290],
            "text": text,
        }
        resp = with_retry(
            requests.post,
            "https://oauth.reddit.com/api/submit",
            headers=headers,
            data=data,
            timeout=15,
        )
        resp.raise_for_status()
        res_json = resp.json()
        if res_json.get("json", {}).get("errors"):
            errs = res_json["json"]["errors"]
            return False, f"Reddit API error: {errs}"
        url = res_json.get("json", {}).get("data", {}).get("url", "success")
        return True, url
    except Exception as e:
        return False, f"Reddit posting error: {e}"


# ---------------------------------------------------------------------------
# Main Execution
# ---------------------------------------------------------------------------
def run():
    memory = load_memory()
    
    access_token = os.environ.get("LINKEDIN_ACCESS_TOKEN", "").strip()

    # Run the Continuous Improvement Engine to learn from past posts before generating a new one.
    # Even without an access_token it re-ranks posts by cached engagement_score from prior runs.
    update_performance_engine(memory, access_token)

    raw_candidates = fetch_all_candidates()
    candidates = dedupe_and_filter(raw_candidates, memory)

    if not candidates:
        print("ISSUE_TITLE: No content found today")
        print("ISSUE_BODY_START")
        print("Could not find any usable, non-duplicate candidate today.")
        print("ISSUE_BODY_END")
        return

    client = gemini_client()
    ranked = score_candidates(client, candidates)

    if ranked:
        winner_entry = ranked[0]
        item = winner_entry.get("candidate", candidates[0])
        score_note = f"Scored {winner_entry.get('score', '?')}/100 — {winner_entry.get('reason', '')}"
    else:
        item = candidates[0]
        score_note = "Scoring unavailable, used first candidate"

    post_text, template_used, hook, first_comment = generate_post(item, memory)

    access_token = os.environ.get("LINKEDIN_ACCESS_TOKEN", "").strip()
    success, result = False, "DRY_RUN / missing access token"
    comment_status = "not attempted"
    if access_token:
        try:
            person_urn = get_person_urn(access_token)
            success, result = post_to_linkedin(access_token, person_urn, post_text)
            if success and first_comment:
                comment_ok, comment_res = post_comment_to_linkedin(access_token, person_urn, result, first_comment)
                comment_status = f"✅ Auto-commented: {comment_res}" if comment_ok else f"ℹ️ Auto-comment notice: {comment_res}"
        except Exception as exc:
            result = f"Posting error: {exc}"

    reddit_success, reddit_result = post_to_reddit(item["title"], post_text, subreddit="sustainability")

    memory.append({
        "link": item["link"],
        "title": item["title"],
        "date": str(date.today()),
        "template": template_used,
        "hook": hook,
        "embedding": item.get("embedding"),
        "post_id": result if success else None,
        "performed_well": False  # Will be dynamically updated next run by the Improvement Engine
    })
    save_memory(memory)

    status_line = (
        f"✅ Posted to LinkedIn successfully. Post ID: {result}"
        if success
        else f"ℹ️ LinkedIn Preview / Dry-run status: {result}"
    )

    if reddit_result == "not configured":
        reddit_status_line = "⏭️ Reddit publishing not configured (skipped)"
    elif reddit_success:
        reddit_status_line = f"✅ Posted to Reddit: {reddit_result}"
    else:
        reddit_status_line = f"❌ Reddit posting failed: {reddit_result}"

    print(f"ISSUE_TITLE: {'Posted' if success else 'Draft Preview'} — {item['title'][:50]}")
    print("ISSUE_BODY_START")
    print(status_line)
    if success and first_comment:
        print(f"💬 LinkedIn First Comment status: {comment_status}")
    print(reddit_status_line)
    print()
    print(f"Selection: {score_note}")
    print(f"Category: {item.get('category', 'n/a')} | Source: {item.get('source', 'n/a')} | Template: {template_used}")
    print()
    print("LinkedIn / Reddit post content:")
    print(post_text)
    print()
    if first_comment:
        print("💬 FIRST COMMENT (Seed the Golden Hour — post this within 5 minutes if not auto-commented):")
        print(first_comment)
        print()
    print(f"---\nSource: {item['link']}")
    print("ISSUE_BODY_END")


if __name__ == "__main__":
    run()
