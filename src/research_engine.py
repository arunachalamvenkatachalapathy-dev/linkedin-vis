import os
import json
import logging
import time
import random
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
from datetime import datetime

log = logging.getLogger("ecopulse")

# 7-DAY SCHEDULE: 4 Days CleanTech/Sustainability + 3 Days AI Agents & Forward Deployment
DAY_SCHEDULE = {
    0: {  # Monday [CLEANTECH 1/4]
        "pillar": "CleanTech & Industrial Decarbonization",
        "theme": "Heavy Industry Decarbonization (Steel, Cement, Green Hydrogen, Circularity)",
        "arxiv_cat": "physics.chem-ph",
        "queries": ["green hydrogen direct reduction steel", "LC3 calcined clay cement decarbonization", "industrial thermal heat pump", "carbon mineralization concrete"]
    },
    1: {  # Tuesday [AI & FDE 1/3]
        "pillar": "AI Agent Architecture & Forward Deployment",
        "theme": "Production Agent State Machines & Deterministic Routing",
        "arxiv_cat": "cs.AI",
        "queries": ["multi-agent state graph DAG", "deterministic tool calling reliability", "agent memory evaluation benchmark", "function calling schema validation"]
    },
    2: {  # Wednesday [CLEANTECH 2/4]
        "pillar": "CleanTech & Energy Systems",
        "theme": "Grid-Scale Energy Storage & Advanced Photovoltaics",
        "arxiv_cat": "physics.soc-ph",
        "queries": ["sodium ion battery grid storage degradation", "perovskite silicon tandem solar cell stability", "solid state battery electrolyte", "flow battery long duration storage"]
    },
    3: {  # Thursday [AI & FDE 2/3]
        "pillar": "Forward Deployment Engineering (FDE)",
        "theme": "Enterprise ERP Integration, Human-in-the-Loop & Dirty Data",
        "devto_tag": "architecture",
        "queries": ["enterprise AI agent post-mortem", "dirty database schema AI integration", "human in the loop audit gate", "unconstrained tool execution failure"]
    },
    4: {  # Friday [CLEANTECH 3/4]
        "pillar": "ESG Telemetry & Compliance",
        "theme": "BRSR Core, CSRD / ESRS, Scope 1/2/3 Supply Chain Audits",
        "arxiv_cat": "econ.GN",
        "queries": ["Scope 3 supply chain carbon emission factor audit", "BRSR Core ESG telemetry disclosure", "corporate GHG protocol assurance", "double materiality carbon accounting"]
    },
    5: {  # Saturday [CLEANTECH 4/4]
        "pillar": "Clean Computing & Datacenter Thermal Systems",
        "theme": "AI Datacenter Power, Liquid Cooling & PUE Efficiency",
        "arxiv_cat": "cs.DC",
        "queries": ["direct to chip dielectric liquid cooling datacenter", "PUE reduction AI compute thermal", "closed loop evaporative water reduction datacenter", "grid aware AI workload scheduling"]
    },
    6: {  # Sunday [AI & FDE 3/3]
        "pillar": "FDE Tactical Playbooks & Contrarian Insights",
        "theme": "Why 90% of Autonomous Demos Fail in Production & Field Rules",
        "devto_tag": "devops",
        "queries": ["why autonomous agents fail in production", "deterministic workflow vs raw prompt loop", "air gapped LLM deployment security", "production FDE field lessons"]
    }
}

class ResearchEngine:
    def __init__(self, memory_engine, gemini_client):
        self.memory = memory_engine
        self.llm = gemini_client

    def get_today_config(self) -> dict:
        day_idx = datetime.utcnow().weekday()
        config = DAY_SCHEDULE.get(day_idx, DAY_SCHEDULE[0])
        log.info(f"📅 Today is Day {day_idx} ({datetime.utcnow().strftime('%A')}): [{config['pillar']}] -> {config['theme']}")
        return config

    def fetch_arxiv(self, category: str, query: str) -> list:
        log.info(f"Querying Peer-Reviewed ArXiv ({category}) for: '{query}'")
        encoded = urllib.parse.quote(f'cat:{category} AND all:"{query}"')
        url = f"http://export.arxiv.org/api/query?search_query={encoded}&start=0&max_results=12&sortBy=submittedDate&sortOrder=descending"
        items = []
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'EcoPulseAgent/7.0 (contact@ecopulse.org)'})
            with urllib.request.urlopen(req, timeout=20) as resp:
                data = resp.read()
            root = ET.fromstring(data)
            ns = {'atom': 'http://www.w3.org/2005/Atom'}
            for entry in root.findall('atom:entry', ns):
                title = entry.find('atom:title', ns).text.strip().replace('\n', ' ')
                summary = entry.find('atom:summary', ns).text.strip().replace('\n', ' ')
                link = entry.find('atom:id', ns).text.strip()
                paper_id = link.split('/')[-1]
                items.append({
                    'source': f'ArXiv Peer-Reviewed Paper ({category})',
                    'title': title,
                    'url': link,
                    'id': f"arxiv_{paper_id}",
                    'abstract': summary
                })
        except Exception as e:
            log.warning(f"ArXiv query failed: {e}")
        return items

    def fetch_hackernews(self, query: str) -> list:
        log.info(f"Querying Hacker News Algolia for verified discussions on: '{query}'")
        encoded = urllib.parse.quote(query)
        url = f"https://hn.algolia.com/api/v1/search?query={encoded}&tags=story&hitsPerPage=12"
        items = []
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'EcoPulseAgent/7.0'})
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode('utf-8'))
                for hit in data.get('hits', []):
                    title = hit.get('title')
                    story_text = hit.get('story_text') or title
                    hit_id = hit.get('objectID')
                    if title and hit_id:
                        items.append({
                            'source': 'Engineering Case Study / Discussion',
                            'title': title,
                            'url': hit.get('url') or f"https://news.ycombinator.com/item?id={hit_id}",
                            'id': f"hn_{hit_id}",
                            'abstract': story_text
                        })
        except Exception as e:
            log.warning(f"Hacker News query failed: {e}")
        return items

    def fetch_devto(self, tag: str) -> list:
        log.info(f"Querying Dev.to Architecture for tag: '{tag}'")
        url = f"https://dev.to/api/articles?tag={tag}&per_page=12&state=fresh"
        items = []
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'EcoPulseAgent/7.0'})
            with urllib.request.urlopen(req, timeout=15) as resp:
                articles = json.loads(resp.read().decode('utf-8'))
                for art in articles:
                    items.append({
                        'source': f"Technical Field Report ({tag})",
                        'title': art.get('title'),
                        'url': art.get('url'),
                        'id': f"devto_{art.get('id')}",
                        'abstract': art.get('description', '')
                    })
        except Exception as e:
            log.warning(f"Dev.to query failed: {e}")
        return items

    def select_topic(self) -> dict:
        config = self.get_today_config()
        queries = config.get("queries", ["sustainable engineering"])
        random.shuffle(queries)

        for q in queries:
            candidates = []
            if "arxiv_cat" in config:
                candidates = self.fetch_arxiv(config["arxiv_cat"], q)
            elif "devto_tag" in config:
                candidates = self.fetch_devto(config["devto_tag"])
            
            if not candidates:
                candidates = self.fetch_hackernews(q)

            for item in candidates:
                if not self.memory.is_duplicate(item.get('id', '')):
                    abstract = item.get('abstract', '')
                    if 'devto_' in item.get('id', ''):
                        art_id = item['id'].replace('devto_', '')
                        try:
                            req = urllib.request.Request(f"https://dev.to/api/articles/{art_id}", headers={'User-Agent': 'EcoPulseAgent/7.0'})
                            with urllib.request.urlopen(req, timeout=10) as res:
                                full_data = json.loads(res.read().decode('utf-8'))
                                abstract = full_data.get('body_markdown', abstract)[:4000]
                        except Exception:
                            pass

                    if abstract and len(abstract) > 80:
                        item['raw_text'] = abstract
                        item['theme'] = config['theme']
                        item['pillar'] = config['pillar']
                        log.info(f"✅ Selected Topic [{item['source']}]: {item['title']}")
                        return item

        log.info("Using high-signal CleanTech / FDE verified fallback.")
        fallback = {
            "source": "Industrial Systems Case Study",
            "title": "Closed-Loop Dielectric Liquid Cooling Cuts AI Datacenter Water Consumption to Zero",
            "id": f"cleantech_datacenter_cooling_day_{datetime.utcnow().weekday()}",
            "theme": config['theme'],
            "pillar": config['pillar'],
            "raw_text": "Evaporative cooling towers in hyper-scale AI data centers consume up to 1.8 liters of municipal potable water per kilowatt-hour. Transitioning to closed-loop direct-to-chip dielectric liquid cooling completely eliminates evaporative water loss while unlocking 100kW+ rack thermal density and delivering a 40% reduction in Power Usage Effectiveness (PUE)."
        }
        if not self.memory.is_duplicate(fallback['id']):
            return fallback
        return {}
