import os
import json
import logging
import time
import random
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET

log = logging.getLogger("ecopulse")

CORE_THEMES = [
    "Environmental Engineering",
    "Clean Energy Transition",
    "Industrial Decarbonization",
    "GHG Accounting & ESG Telemetry",
    "Advanced Materials & Circular Economy",
    "Direct Air Capture & Carbon Removal",
    "Grid Scale Energy Storage & AI Datacenters"
]

class ResearchEngine:
    def __init__(self, memory_engine, gemini_client):
        self.memory = memory_engine
        self.llm = gemini_client

    def generate_niche_query(self) -> str:
        prompt = (
            "You are a Senior Technology & Environmental Analyst.\n"
            "Pick ONE topic theme from this list:\n"
            f"{', '.join(CORE_THEMES)}\n\n"
            "Generate ONE highly specific 2 to 4 word search term for academic papers or technical deep dives.\n"
            "Examples: 'perovskite solar degradation', 'closed loop datacenter cooling', 'biogenic carbon accounting'.\n"
            "Output ONLY the raw search string without quotes or punctuation."
        )
        try:
            query = self.llm.generate_text(prompt, temperature=0.8).strip().replace('"', '').replace("'", "")
            if query:
                return query
        except Exception as e:
            log.warning(f"LLM query generation fallback: {e}")

        fallback_queries = [
            "grid scale battery storage",
            "direct air capture efficiency",
            "datacenter liquid cooling",
            "perovskite tandem solar",
            "green hydrogen electrolysis",
            "carbon mineralization concrete",
            "scope 3 supply chain telemetry"
        ]
        return random.choice(fallback_queries)

    def fetch_arxiv(self, query: str) -> list:
        log.info(f"Querying ArXiv API for: '{query}'")
        encoded_query = urllib.parse.quote(f'all:"{query}"')
        url = f"http://export.arxiv.org/api/query?search_query={encoded_query}&start=0&max_results=25&sortBy=submittedDate&sortOrder=descending"
        
        items = []
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'EcoPulseBot/4.0'})
            with urllib.request.urlopen(req, timeout=25) as response:
                data = response.read()
                
            root = ET.fromstring(data)
            ns = {'atom': 'http://www.w3.org/2005/Atom'}
            
            for entry in root.findall('atom:entry', ns):
                title = entry.find('atom:title', ns).text.strip().replace('\n', ' ')
                summary = entry.find('atom:summary', ns).text.strip().replace('\n', ' ')
                link = entry.find('atom:id', ns).text.strip()
                paper_id = link.split('/')[-1]
                
                items.append({
                    'source': 'ArXiv Scientific Research',
                    'title': title,
                    'url': link,
                    'id': f"arxiv_{paper_id}",
                    'abstract': summary
                })
        except Exception as e:
            log.warning(f"ArXiv query failed: {e}")
            
        return items

    def fetch_devto(self) -> list:
        log.info("Querying Dev.to API for fresh engineering insights")
        tags = ["sustainability", "architecture", "devops", "cloud", "ai", "database"]
        selected_tag = random.choice(tags)
        url = f"https://dev.to/api/articles?tag={selected_tag}&per_page=20&state=fresh"
        
        items = []
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'EcoPulseBot/4.0'})
            with urllib.request.urlopen(req, timeout=25) as response:
                articles = json.loads(response.read().decode('utf-8'))
                for art in articles:
                    items.append({
                        'source': f"Dev.to Engineering ({selected_tag})",
                        'title': art.get('title'),
                        'url': art.get('url'),
                        'id': f"devto_{art.get('id')}",
                        'abstract': art.get('description', '')
                    })
        except Exception as e:
            log.warning(f"Dev.to query failed: {e}")
        return items

    def fetch_wikipedia(self) -> list:
        log.info("Querying Wikipedia API for scientific overview")
        url = "https://en.wikipedia.org/api/rest_v1/page/random/summary"
        items = []
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'EcoPulseBot/4.0 (contact@ecopulse.org)'})
            with urllib.request.urlopen(req, timeout=20) as response:
                data = json.loads(response.read().decode('utf-8'))
                items.append({
                    'source': 'Wikipedia Encyclopedia',
                    'title': data.get('title'),
                    'url': data.get('content_urls', {}).get('desktop', {}).get('page', ''),
                    'id': f"wiki_{data.get('pageid')}",
                    'abstract': data.get('extract', '')
                })
        except Exception as e:
            log.warning(f"Wikipedia query failed: {e}")
        return items

    def fetch_hackernews(self) -> list:
        log.info("Querying Hacker News API for top tech developments")
        items = []
        try:
            req = urllib.request.Request("https://hacker-news.firebaseio.com/v0/topstories.json", headers={'User-Agent': 'EcoPulseBot/4.0'})
            with urllib.request.urlopen(req, timeout=20) as response:
                story_ids = json.loads(response.read().decode('utf-8'))[:15]

            for sid in story_ids:
                try:
                    s_req = urllib.request.Request(f"https://hacker-news.firebaseio.com/v0/item/{sid}.json", headers={'User-Agent': 'EcoPulseBot/4.0'})
                    with urllib.request.urlopen(s_req, timeout=10) as s_resp:
                        story = json.loads(s_resp.read().decode('utf-8'))
                        if story and story.get('title') and (story.get('text') or story.get('url')):
                            items.append({
                                'source': 'Hacker News Top Story',
                                'title': story.get('title'),
                                'url': story.get('url', f"https://news.ycombinator.com/item?id={sid}"),
                                'id': f"hn_{sid}",
                                'abstract': story.get('text', story.get('title'))
                            })
                except Exception:
                    continue
        except Exception as e:
            log.warning(f"Hacker News query failed: {e}")
        return items

    def select_topic(self) -> dict:
        sources = ['arxiv', 'devto', 'wikipedia', 'hackernews']
        random.shuffle(sources)

        for source in sources:
            candidates = []
            if source == 'arxiv':
                query = self.generate_niche_query()
                candidates = self.fetch_arxiv(query)
            elif source == 'devto':
                candidates = self.fetch_devto()
            elif source == 'wikipedia':
                candidates = self.fetch_wikipedia()
            elif source == 'hackernews':
                candidates = self.fetch_hackernews()

            for item in candidates:
                if not self.memory.is_duplicate(item.get('id', '')):
                    abstract = item.get('abstract', '')
                    if source == 'devto' and 'devto_' in item.get('id', ''):
                        art_id = item['id'].replace('devto_', '')
                        try:
                            req = urllib.request.Request(f"https://dev.to/api/articles/{art_id}", headers={'User-Agent': 'EcoPulseBot/4.0'})
                            with urllib.request.urlopen(req, timeout=10) as res:
                                full_data = json.loads(res.read().decode('utf-8'))
                                abstract = full_data.get('body_markdown', abstract)[:4000]
                        except Exception:
                            pass

                    if abstract and len(abstract) > 60:
                        item['raw_text'] = abstract
                        log.info(f"✅ Selected Topic [{item['source']}]: {item['title']}")
                        return item

        log.error("CRITICAL: Failed to discover fresh content from all sources. Using emergency fallback.")
        fallback = {
            "source": "Emergency Fallback Document",
            "title": "Closed-Loop Liquid Cooling in High-Density AI Data Centers",
            "id": "emergency_fallback_ai_cooling_v4",
            "raw_text": "Evaporative cooling towers in hyper-scale data centers consume up to 1.8 liters of potable water per kilowatt-hour. Transitioning to closed-loop direct-to-chip dielectric liquid cooling eliminates operational water evaporation entirely while unlocking 100kW+ rack thermal density and delivering a 40% reduction in Power Usage Effectiveness (PUE)."
        }
        if not self.memory.is_duplicate(fallback['id']):
            return fallback
        return {}
