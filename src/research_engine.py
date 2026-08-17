import os
import json
import logging
import time
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
import random

log = logging.getLogger("ecopulse")

CORE_THEMES = [
    "Environmental Engineering",
    "Environmental Science",
    "Climate Risk",
    "GHG Accounting",
    "Sustainability Reporting Standards"
]

class ResearchEngine:
    def __init__(self, memory_engine, gemini_client):
        self.memory = memory_engine
        self.llm = gemini_client

    def generate_niche_query(self) -> str:
        """Uses Gemini to brainstorm a novel, highly specific long-tail search query for scientific papers."""
        prompt = (
            "You are a master scientific researcher. I need to search the ArXiv database for a highly technical, specific academic paper.\n"
            "Pick ONE of the following core themes at random:\n"
            f"{', '.join(CORE_THEMES)}\n\n"
            "Now, generate exactly ONE technical search query (2 to 4 words maximum) related to that theme. "
            "It must be academic and specific enough to find high-quality research papers.\n"
            "Example: 'scope 3 supply chain'\n"
            "Example: 'direct air capture efficiency'\n"
            "Example: 'grid scale battery storage'\n"
            "Output ONLY the query string. No quotes, no markdown, nothing else."
        )
        try:
            query = self.llm.generate_text(prompt, temperature=0.9).strip().replace('"', '')
            if query:
                return query
        except Exception as e:
            log.warning(f"Failed to brainstorm niche query: {e}")
        
        # Safe fallback if LLM fails (e.g., 429 Rate Limit or Timeout)
        FALLBACK_QUERIES = [
            "renewable energy transition",
            "solar power technology",
            "wind turbine engineering",
            "battery energy storage",
            "carbon capture technology",
            "climate change science",
            "electric vehicle manufacturing",
            "green hydrogen production",
            "sustainable agriculture",
            "circular economy recycling"
        ]
        return random.choice(FALLBACK_QUERIES)

    def fetch_arxiv_papers(self, query: str) -> list:
        log.info(f"Searching ArXiv with dynamic query: '{query}'")
        encoded_query = urllib.parse.quote(f'all:"{query}"')
        url = f'http://export.arxiv.org/api/query?search_query={encoded_query}&start=0&max_results=50&sortBy=submittedDate&sortOrder=descending'
        
        items = []
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=30) as response:
                data = response.read()
                
            root = ET.fromstring(data)
            ns = {'atom': 'http://www.w3.org/2005/Atom'}
            
            for entry in root.findall('atom:entry', ns):
                title = entry.find('atom:title', ns).text.strip().replace('\n', ' ')
                summary = entry.find('atom:summary', ns).text.strip().replace('\n', ' ')
                link = entry.find('atom:id', ns).text.strip()
                paper_id = link.split('/')[-1]
                
                items.append({
                    'source': 'ArXiv Scientific Paper',
                    'title': title,
                    'url': link,
                    'id': paper_id,
                    'abstract': summary
                })
        except Exception as e:
            log.warning(f"ArXiv search failed: {e}")
            
        return items

    def fetch_devto(self) -> list:
        log.info("Searching Dev.to for trending tech articles")
        url = "https://dev.to/api/articles?per_page=30&state=fresh"
        items = []
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=30) as response:
                articles = json.loads(response.read())
                for art in articles:
                    items.append({
                        'source': 'Dev.to Technical Article',
                        'title': art.get('title'),
                        'url': art.get('url'),
                        'id': str(art.get('id')),
                        'abstract': art.get('description', '')
                    })
        except Exception as e:
            log.warning(f"Dev.to search failed: {e}")
        return items

    def fetch_wikipedia(self) -> list:
        log.info("Fetching random Wikipedia conceptual summary")
        url = "https://en.wikipedia.org/api/rest_v1/page/random/summary"
        items = []
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=30) as response:
                data = json.loads(response.read())
                items.append({
                    'source': 'Wikipedia Encyclopedia',
                    'title': data.get('title'),
                    'url': data.get('content_urls', {}).get('desktop', {}).get('page', ''),
                    'id': str(data.get('pageid')),
                    'abstract': data.get('extract', '')
                })
        except Exception as e:
            log.warning(f"Wikipedia search failed: {e}")
        return items

    def select_topic(self) -> dict:
        """Brainstorms a query, picks a random API source, and returns the first novel piece of content."""
        sources = ['arxiv', 'devto', 'wikipedia']
        
        for attempt in range(10):
            source_choice = random.choice(sources)
            candidates = []
            
            if source_choice == 'arxiv':
                query = self.generate_niche_query()
                candidates = self.fetch_arxiv_papers(query)
            elif source_choice == 'devto':
                candidates = self.fetch_devto()
            elif source_choice == 'wikipedia':
                candidates = self.fetch_wikipedia()
                
            for paper in candidates:
                if not self.memory.is_duplicate(paper['id']):
                    abstract = paper.get('abstract', '')
                    if abstract and len(abstract) > 50:
                        if source_choice == 'devto':
                            try:
                                req = urllib.request.Request(f"https://dev.to/api/articles/{paper['id']}", headers={'User-Agent': 'Mozilla/5.0'})
                                with urllib.request.urlopen(req, timeout=10) as response:
                                    full_art = json.loads(response.read())
                                    abstract = full_art.get('body_markdown', abstract)[:5000]
                            except:
                                pass
                        
                        paper['raw_text'] = abstract
                        log.info(f"✅ Selected Content [{source_choice}]: {paper['title']}")
                        return paper
                        
            log.warning(f"Attempt {attempt + 1}: No valid new content found for {source_choice}. Retrying in 5s...")
            time.sleep(5)
            
        log.error("CRITICAL: Failed to find valid content after 10 attempts. Using hardcoded emergency fallback.")
        fallback = {
            "source": "Emergency Fallback Document",
            "title": "The Hidden Water Footprint of AI Data Centers",
            "id": "emergency_fallback_ai_water_1",
            "raw_text": "Evaporative cooling towers in hyper-scale data centers consume massive volumes of potable water. Transitioning to closed-loop direct-to-chip liquid cooling eliminates water evaporation completely while unlocking 100kW+ rack thermal density. Traditional evaporative cooling consumes 1.8 Liters of fresh water per kWh, whereas closed-loop systems yield zero water loss and a 40% PUE efficiency reduction."
        }
        if not self.memory.is_duplicate(fallback['id']):
            return fallback
        return {}
