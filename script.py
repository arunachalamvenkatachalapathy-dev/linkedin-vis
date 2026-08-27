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

NEWSAPI_KEY = os.environ.get("NEWSAPI_KEY", "8e34b55b561e4f0e921b30934cac03b8").strip()

CLICKBAIT_PATTERNS = [
    r"you won'?t believe", r"\bshocking\b", r"\bgone wrong\b",
    r"^\d+ (things|reasons|ways) ", r"\bclickbait\b",
]

MAX_CANDIDATES_TO_SCORE = 60

# ---------------------------------------------------------------------------
# Sign-off Tagline & Storytelling Templates
# ---------------------------------------------------------------------------
TAGLINE = "— Tracking where Sustainability, Telemetry, and AI Agents collide."

TEMPLATES = {
    1: "\"The Shift\" — Hook (bold one-liner) -> Context (what happened in 1-2 lines) -> "
       "The shift (what this changes for sustainability leaders/engineers) -> Technical Take -> CTA (a question)",
    2: "\"Before/After\" — Hook (\"here's how Scope 3/ESG reporting used to look vs now\") -> Before -> After -> "
       "Why it matters (one concrete outcome) -> CTA",
    3: "\"Mini case study\" — Hook (a specific emission/reduction number) -> Setup -> What happened -> Telemetry Lesson -> CTA",
    4: "\"Contrarian take\" — Hook (challenge a popular ESG/decarbonization myth) -> Evidence (2-3 proof points) -> "
       "Technical Nuance -> CTA (invite debate)",
    5: "\"Curated list + POV\" — Hook -> 3-5 punchy points -> your synthesis -> CTA",
}

POST_PROMPT_TEMPLATE = """
You are writing a LinkedIn post for an Environmental & CleanTech professional writing in a
direct, analytical, technical tone (no corporate fluff, no "game-changer" or "revolutionize").
This author focuses on Environmental Telemetry, Scope 3 Emissions, ESG Reporting (BRSR/CSRD), and AI Agents for industrial workflows.

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

Choose the best-fitting structure for today's story.

Rules:
- 120-150 words total (strictly enforce high-engagement mobile length)
- Line 1 (The Hook): A sharp, scroll-stopping bold technical claim under 12 words
- Lines 2-3 (Context & Telemetry): 1-2 concise lines summarizing the breaking news/metric from the source
- Lines 4-5 (The Shift): Technical reframe explaining what changes for ESG leaders, engineers, or Scope 3 auditors
- Line 6 (The Question): A high-stakes, specific technical question to drive comments
- Direct, analytical, authoritative tone (no fluff, no "game-changer" or "revolutionize")
- Short paragraphs (1-2 lines each with blank lines between)
- Generate 3-5 specific LinkedIn hashtags (e.g. #Sustainability #Scope3Emissions #ESG #BRSR #CleanTech)

Output format — EXACTLY this, nothing else:
TEMPLATE: <number 1-5 of the structure you used>
---
<the finished post text, no title, no notes, no sign-off, no hashtags>
---
<hashtags, space-separated, each starting with #>
"""

SCORING_PROMPT_TEMPLATE = """
You are a content scout for a Sustainability & Environmental Tech leader. Score each candidate
story below from 0-100 using this rubric tailored to Environmental Engineering, ESG, and AI Workflows:

- Environmental & Future Impact (0-30): Does this signal significant progress in carbon emissions reduction, Scope 3 telemetry, or CleanTech transition?
- Real-world Evidence (0-25): Is this a concrete enterprise result, sensor telemetry deployment, or regulatory compliance metric (BRSR/CSRD)?
- ESG & Enterprise Relevance (0-20): Does this matter for sustainability officers, ESG reporting teams, or industrial engineers?
- Novelty (0-15): Is this a fresh technical angle, not something oversaturated everywhere? IMPORTANT: each candidate
  includes "covered_by_n_sources" — how many different outlets in today's pool are running this same
  story. A high number (3+) means this is a mainstream story — score novelty LOW unless taking a unique technical angle.
- Conversation & Community Potential (0-10): Would a thoughtful LinkedIn audience of sustainability professionals and engineers want to discuss this?

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


# ---------------------------------------------------------------------------
# Ingestion
# ---------------------------------------------------------------------------
def fetch_rss():
    items = []
    for category, urls in SOURCES.items():
        for url in urls:
            try:
                feed = feedparser.parse(url)
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


def fetch_all_candidates():
    return fetch_rss() + fetch_hackernews() + fetch_reddit() + fetch_newsapi()


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


def is_similar_topic(title, recent_titles, threshold=0.55):
    lowered = title.lower()
    for recent in recent_titles:
        ratio = difflib.SequenceMatcher(None, lowered, recent.lower()).ratio()
        if ratio >= threshold:
            return True
    return False


def dedupe_and_filter(items, used_links, recent_titles):
    seen_links = set()
    filtered = []
    for item in items:
        link = item.get("link", "")
        title = item.get("title", "")
        if not link or not title:
            continue
        if link in used_links or link in seen_links:
            continue
        if is_clickbait(title):
            continue
        if is_similar_topic(title, recent_titles):
            continue
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
    for m_name in ["gemini-2.5-flash", "gemini-2.0-flash", "gemini-1.5-flash"]:
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


def generate_post(item, memory):
    client = gemini_client()
    templates_list = "\n".join(f"{k}. {v}" for k, v in TEMPLATES.items())
    prompt = POST_PROMPT_TEMPLATE.format(
        title=item["title"],
        category=item.get("category", "general"),
        summary=item["summary"],
        link=item["link"],
        recent_topics=recent_topics_text(memory),
        recent_hooks=recent_hooks_text(memory),
        templates_list=templates_list,
        recent_templates=recent_templates_text(memory),
    )
    raw = None
    if client:
        for m_name in ["gemini-2.5-flash", "gemini-2.0-flash", "gemini-1.5-flash"]:
            try:
                response = generate_with_retry(client, m_name, prompt)
                if response and response.text:
                    raw = response.text.strip()
                    break
            except Exception as exc:
                print(f"Post generation error for model {m_name}: {exc}")

    if not raw:
        # Dynamic, multi-paragraph high-authority post constructed according to your friend's Template 1 ("The Shift")
        summary_raw = item.get("summary") or item.get("title", "")
        summary_clean = re.sub(r'<[^>]+>', '', summary_raw).strip()
        summary_snippet = summary_clean[:180].strip()
        title_clean = re.sub(r'<[^>]+>', '', item['title']).strip()
        raw = (
            "TEMPLATE: 1\n---\n"
            f"Most sustainability frameworks treat {title_clean[:55]} as a static compliance requirement.\n\n"
            f"That boundary just moved. Recent field telemetry indicates that {summary_snippet} — altering how engineering teams validate carbon claims.\n\n"
            "The shift isn't just adopting new software. It's moving from annual estimation spreadsheets to continuous, automated sensor verification across Scope 3 data pipelines.\n\n"
            "When regulatory frameworks like CSRD and BRSR demand audited metrics, unverified third-party data becomes an operational risk.\n\n"
            "What primary verification mechanism is your team using to validate vendor environmental data?\n---\n"
            "#Sustainability #Scope3Emissions #ESG #CleanTech #EnvironmentalTelemetry"
        )

    template_used = None
    match = re.search(r"TEMPLATE:\s*(\d)", raw)
    if match:
        template_used = int(match.group(1))

    parts = raw.split("---")
    post_body = parts[1].strip() if len(parts) > 1 else raw.strip()
    hashtags = parts[2].strip() if len(parts) > 2 else "#Sustainability #CleanTech #ESG"

    post_text = post_body
    if TAGLINE not in post_text:
        post_text += f"\n\n{TAGLINE}"
    if hashtags and hashtags not in post_text:
        post_text += f"\n\n{hashtags}"

    hook = post_body.split("\n")[0].strip()
    return post_text, template_used, hook


# ---------------------------------------------------------------------------
# Pure Text-Only LinkedIn & Reddit Publishing
# ---------------------------------------------------------------------------
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

    resp = requests.post(
        "https://api.linkedin.com/rest/posts", headers=headers, json=payload, timeout=15
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
        resp = requests.post(
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
    used_links = used_links_set(memory)
    recent_titles = [entry["title"] for entry in memory[-30:] if entry.get("title")]

    raw_candidates = fetch_all_candidates()
    candidates = dedupe_and_filter(raw_candidates, used_links, recent_titles)

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

    access_token = os.environ.get("LINKEDIN_ACCESS_TOKEN", "").strip()
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
