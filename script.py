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
    1: """TEMPLATE 1: "The Shift"
   - Line 1 (Hook): One bold, counter-intuitive claim about what just changed — under 12 words. Make readers stop scrolling.
   - Lines 2-3 (Context): 2 short sentences grounding the claim in the news/data. Be specific. No vague language.
   - Lines 4-5 (The Shift): Explain what this means for the reader — what does it change for them, their team, or their industry?
   - Line 6 (CTA): Ask a single, specific question that professionals in this space would actually want to answer.""",

    2: """TEMPLATE 2: "Before / After"
   - Line 1 (Hook): A stark contrast between the old reality and the new one — under 12 words. Make it feel like whiplash.
   - Lines 2-3 (Before): Describe the old way in 1-2 short sentences. Be relatable — this is what readers currently do.
   - Lines 4-5 (After): Describe the new reality. Use a single concrete outcome or number if the source has one.
   - Line 6 (CTA): Invite readers to share where they are in this transition.""",

    3: """TEMPLATE 3: "Mini Case Study"
   - Line 1 (Hook): Lead with the most striking number or outcome from the source — under 12 words.
   - Lines 2-3 (Setup): Context on who did this, what problem they were solving, and what they tried.
   - Lines 4-5 (Lesson): The insight — why this worked, what others can learn, what the broader pattern is.
   - Line 6 (CTA): A direct question — has anyone else seen this pattern, or tried something similar?""",

    4: """TEMPLATE 4: "Contrarian Take"
   - Line 1 (Hook): Challenge a widely accepted belief — something most readers in this space assume is true. Under 12 words.
   - Lines 2-3 (Evidence): 2-3 concrete data points or examples that undercut the conventional wisdom.
   - Lines 4-5 (Nuance): Explain the subtlety — not "X is wrong" but "X is right in context Y, wrong in context Z."
   - Line 6 (CTA): Invite respectful pushback with a pointed question. This template thrives on debate.""",

    5: """TEMPLATE 5: "Observation + List"
   - Line 1 (Hook): A bold one-sentence observation about something you're noticing — under 12 words. First person is fine.
   - Lines 2-4 (List): 3 short, punchy bullet points — each a single line, each a distinct insight drawn from the source.
   - Line 5 (POV): Your synthesis in 1-2 sentences — what this all adds up to in your view.
   - Line 6 (CTA): End with the one question this raises for you.""",
}

POST_PROMPT_TEMPLATE = """
You are writing a LinkedIn post for a seasoned ESG & Sustainability professional. 
Tone: Conversational, insightful, and slightly contrarian. Think like a top-tier LinkedIn creator—short, punchy sentences, relatable observations, and zero corporate fluff or robotic phrasing.
DO NOT forcefully inject the words "telemetry", "AI", or "ESG" if the article is about something else. Find the human or business angle.

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

Recent high-performing posts (these received the highest engagement relative to others):
{recent_successes}

IMPROVEMENT ENGINE DIRECTIVE:
Study the hooks, tone, and pacing of the high-performing posts above. Adapt your output to match the rhythm, formatting, and perspective of what is proven to work for this audience. Do not just copy them, but deeply reverse-engineer their success to improve today's post.

Choose the best-fitting structure for today's story and strictly follow its line-by-line format. 
CRITICAL INSTRUCTION: If the story is political or a lawsuit (e.g., EPA, government), focus on the *compliance or business impact*, not just the politics. Make it sound like a real person talking to peers.

Global constraints:
- 70-130 words total (keep it highly scannable)
- Use everyday professional language. Break up paragraphs (1-2 lines each).
- Start with a scroll-stopping, counter-intuitive hook.
- Generate exactly 2-3 specific LinkedIn hashtags (e.g. #Sustainability #ESG)

Output format — EXACTLY this, nothing else:
TEMPLATE: <number 1-5 of the structure you used>
---
<the finished post text, no title, no notes, no sign-off, no hashtags>
---
<hashtags, space-separated, each starting with #>
"""

SCORING_PROMPT_TEMPLATE = """
You are a content scout for a Tech, AI & Sustainability leader. Score each candidate
story below from 0-100 using this balanced rubric for LinkedIn engagement. You do NOT need to rely only on sustainability; highly trending tech, AI, and business topics are heavily encouraged:

- Virality & Emotion (0-35): Does this trigger a strong reaction (surprise, hope, frustration, debate)? Is it a trending topic everyone is talking about?
- Professional Relevance (0-30): Does this matter to tech workers, founders, AI engineers, or sustainability professionals in their day-to-day?
- Concrete Evidence (0-20): Is there a real-world result, a clear metric, or a specific case study, rather than just vague promises?
- Novelty (0-15): Is this a fresh angle? IMPORTANT: each candidate includes "covered_by_n_sources". A high number (3+) means this is mainstream — score novelty LOW unless taking a highly unique angle.

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
        return "(none marked yet)"
    recent = successes[-n:]
    return "\n\n".join(f"- Title: {e['title']}\n  Hook: {e.get('hook', 'N/A')}\n  Template: {e.get('template', 'N/A')}" for e in recent)


def update_performance_engine(memory, access_token):
    """
    Constant Improvement Engine:
    Reads the last 15 posts from memory, checks their actual engagement on LinkedIn,
    and dynamically tags the top 33% as 'performed_well' so the AI learns from them.
    Runs BEFORE post generation every day so the new post learns from real data.
    """
    import urllib.parse

    # Work on the actual memory entries (last 15), not a copy
    recent_indices = list(range(max(0, len(memory) - 15), len(memory)))

    if access_token:
        for idx in recent_indices:
            entry = memory[idx]
            post_id = entry.get("post_id")
            if not post_id or not post_id.startswith("urn:li:"):
                continue

            # URN must be double-encoded for the socialActions path parameter
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
                    # Comments worth 2x — signals real engagement, not passive scrolling
                    memory[idx]["engagement_score"] = likes + (comments * 2)
                else:
                    print(f"Improvement Engine: LinkedIn API {res.status_code} for {post_id}")
            except Exception as e:
                print(f"Improvement Engine: Failed to fetch stats for {post_id} - {e}")

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


def fetch_newsapi():
    if not NEWSAPI_KEY:
        print("NEWSAPI_KEY not set — skipping NewsAPI source")
        return []
    items = []
    headers = {"X-Api-Key": NEWSAPI_KEY}
    queries = ["sustainability ESG AI", "Scope 3 carbon emissions", "AI agents autonomous workflow"]
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


def fetch_exa():
    api_key = os.environ.get("EXA_API_KEY", "").strip()
    if not api_key:
        return []
    items = []
    queries = [
        "technical challenges scope 3 emissions telemetry",
        "latest AI agent workflows in enterprise",
        "biggest trending controversy in tech startups this week",
        "recent breakthroughs in carbon accounting data"
    ]
    url = "https://api.exa.ai/search"
    headers = {"x-api-key": api_key, "Content-Type": "application/json"}
    for q in queries:
        try:
            payload = {
                "query": q,
                "numResults": 3,
                "useAutoprompt": True
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

def fetch_tavily():
    api_key = os.environ.get("TAVILY_API_KEY", "").strip()
    if not api_key:
        return []
    items = []
    url = "https://api.tavily.com/search"
    headers = {"Content-Type": "application/json"}
    queries = [
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

def fetch_all_candidates():
    # Fetch all
    rss = fetch_rss()
    hn = fetch_hackernews()
    reddit = fetch_reddit()
    newsapi = fetch_newsapi()
    exa = fetch_exa()
    tavily = fetch_tavily()
    
    # Cap each major group so no single platform dominates the candidate pool
    # The scoring pool is MAX_CANDIDATES_TO_SCORE (60)
    random.shuffle(rss)
    random.shuffle(hn)
    random.shuffle(reddit)
    random.shuffle(newsapi)
    random.shuffle(exa)
    random.shuffle(tavily)
    
    pool = rss[:10] + exa[:10] + tavily[:10] + hn[:15] + reddit[:5] + newsapi[:10]
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

def generate_with_groq(prompt):
    api_key = os.environ.get("GROQ_API_KEY", "").strip()
    if not api_key:
        return None
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {
        "model": "llama-3.1-70b-versatile",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.7
    }
    for attempt in range(1, 4):
        try:
            resp = requests.post(url, headers=headers, json=payload, timeout=15)
            if resp.status_code == 200:
                return resp.json()["choices"][0]["message"]["content"]
            time.sleep(2 * attempt)
        except Exception as e:
            time.sleep(2 * attempt)
    return None


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
    for m_name in ["gemini-3.6-flash", "gemini-3.6-pro"]:
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

    # Fallback to Groq if Gemini completely fails
    try:
        print("Falling back to Groq for scoring...")
        raw_groq = generate_with_groq(prompt)
        if raw_groq:
            raw = re.sub(r"^```(json)?|```$", "", raw_groq.strip(), flags=re.MULTILINE).strip()
            ranked = json.loads(raw)
            for r in ranked:
                idx = r.get("id")
                if isinstance(idx, int) and 0 <= idx < len(pool):
                    r["candidate"] = pool[idx]
            return [r for r in ranked if "candidate" in r]
    except Exception as e:
        print(f"Groq scoring fallback error: {e}")

    return [{"id": 0, "score": 85, "reason": "first candidate (scoring fallback)", "candidate": pool[0]}]


MAX_HASHTAGS = 3
MIN_WORDS = 70
MAX_WORDS = 140

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
    return failures

def generate_post(item, memory):
    client = gemini_client()
    templates_list = "\n".join(f"{k}. {v}" for k, v in TEMPLATES.items())
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
    
    raw = None
    if client:
        prompt = base_prompt
        for attempt in range(1, 4):  # Max 3 attempts
            for m_name in ["gemini-3.6-flash", "gemini-3.6-pro"]:
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
                        prompt = base_prompt + f"\n\nYOUR PREVIOUS ATTEMPT FAILED VALIDATION: {', '.join(failures)}. Please fix these errors and ensure exactly 2-3 hashtags and between {MIN_WORDS}-{MAX_WORDS} words."
                        raw = None
                        break  # Break inner loop to retry outer loop
                except Exception as exc:
                    print(f"Post generation error for model {m_name}: {exc}")
            if raw:
                break # We found a valid raw

    if not raw:
        print("Falling back to Groq for post generation...")
        try:
            raw_groq = generate_with_groq(base_prompt)
            if raw_groq:
                raw = raw_groq.strip()
        except Exception as e:
            print(f"Groq generation fallback error: {e}")

    if not raw:
        # Fallback post if Gemini is unavailable — matches new conversational tone
        title_clean = re.sub(r'<[^>]+>', '', item['title']).strip()
        summary_raw = item.get("summary") or item.get("title", "")
        summary_clean = re.sub(r'<[^>]+>', '', summary_raw).strip()[:120]
        raw = (
            "TEMPLATE: 1\n---\n"
            f"{title_clean[:80]}.\n\n"
            f"{summary_clean}\n\n"
            "The real question isn't whether this matters — it's how fast your organisation is responding.\n\n"
            "What's your team's current approach here? Would love to hear below.\n---\n"
            "#Sustainability #ESG"
        )

    template_used = None
    match = re.search(r"TEMPLATE:\s*(\d)", raw)
    if match:
        template_used = int(match.group(1))

    parts = raw.split("---")
    post_body = parts[1].strip() if len(parts) > 1 else raw.strip()
    hashtags = parts[2].strip() if len(parts) > 2 else "#Sustainability #CleanTech #ESG"
    
    # Enforce hashtag truncation just in case
    hash_list = re.findall(r"(#\w+)", hashtags)
    if len(hash_list) > MAX_HASHTAGS:
        hashtags = " ".join(hash_list[:MAX_HASHTAGS])

    post_text = post_body
    if hashtags and hashtags not in post_text:
        post_text += f"\n\n{hashtags}"

    hook = post_body.split("\n")[0].strip()
    return post_text, template_used, hook


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
    token = get_reddit_user_token()
    if not token:
        print("Skipping Reddit publishing (REDDIT_USERNAME / REDDIT_PASSWORD not configured)")
        return False, "not configured"
    headers = {"Authorization": f"Bearer {token}", "User-Agent": "linkedin-content-bot/1.0"}
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

    post_text, template_used, hook = generate_post(item, memory)

    success, result = False, "DRY_RUN / missing access token"
    if access_token:
        try:
            person_urn = get_person_urn(access_token)
            success, result = post_to_linkedin(access_token, person_urn, post_text)
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
    print(reddit_status_line)
    print()
    print(f"Selection: {score_note}")
    print(f"Category: {item.get('category', 'n/a')} | Source: {item.get('source', 'n/a')} | Template: {template_used}")
    print()
    print("LinkedIn / Reddit post content:")
    print(post_text)
    print()
    print(f"---\nSource: {item['link']}")
    print("ISSUE_BODY_END")


if __name__ == "__main__":
    run()
