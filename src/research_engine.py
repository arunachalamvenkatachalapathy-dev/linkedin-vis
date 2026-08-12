import os
import json
import logging
import time
from yt_dlp import YoutubeDL
from youtube_transcript_api import YouTubeTranscriptApi

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
        """Uses Gemini to brainstorm a novel, highly specific long-tail search query."""
        prompt = (
            "You are a master researcher. I need to search YouTube for a highly technical, specific video.\n"
            "Pick ONE of the following core themes at random:\n"
            f"{', '.join(CORE_THEMES)}\n\n"
            "Now, generate exactly ONE technical search query (2 to 4 words maximum) related to that theme. "
            "It must be broad enough to have many educational lectures on YouTube, but still highly technical.\n"
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
        import random
        return random.choice(FALLBACK_QUERIES)

    def fetch_youtube_videos(self, query: str) -> list:
        log.info(f"Searching YouTube with dynamic query: '{query}'")
        ydl_opts = {
            'quiet': True,
            'extract_flat': True,
            'force_generic_extractor': True
            # Removed dateafter filter so we can always find great content based on the niche query
        }
        
        items = []
        try:
            with YoutubeDL(ydl_opts) as ydl:
                result = ydl.extract_info(f"ytsearch50:{query}", download=False)
                if 'entries' in result:
                    for entry in result['entries']:
                        if entry and entry.get('id'):
                            items.append({
                                'source': 'YouTube Transcript',
                                'title': entry.get('title', ''),
                                'url': entry.get('url', f"https://www.youtube.com/watch?v={entry['id']}"),
                                'id': entry['id']
                            })
        except Exception as e:
            log.warning(f"YouTube search failed: {e}")
            
        return items

    def extract_youtube_transcript(self, video_id: str) -> str:
        try:
            transcript = YouTubeTranscriptApi.get_transcript(video_id)
            return " ".join([t['text'] for t in transcript])
        except Exception:
            return ""

    def select_topic(self) -> dict:
        """Brainstorms a query, searches YouTube, and returns the first fresh transcript."""
        for attempt in range(10):
            query = self.generate_niche_query()
            youtube_candidates = self.fetch_youtube_videos(query)
            
            for yt in youtube_candidates:
                if not self.memory.is_duplicate(yt['id']):
                    transcript = self.extract_youtube_transcript(yt['id'])
                    if transcript and len(transcript) > 500:
                        yt['raw_text'] = transcript[:10000]
                        log.info(f"✅ Selected YouTube Video: {yt['title']}")
                        return yt
                        
            log.warning(f"Attempt {attempt + 1}: No valid transcripts found for '{query}'. Retrying in 5s...")
            time.sleep(5)
            
        log.error("CRITICAL: Failed to find a valid transcript after 10 attempts. Using hardcoded emergency fallback.")
        fallback = {
            "source": "Emergency Fallback Document",
            "title": "The Hidden Water Footprint of AI Data Centers",
            "id": "emergency_fallback_ai_water_1",
            "raw_text": "Evaporative cooling towers in hyper-scale data centers consume massive volumes of potable water. Transitioning to closed-loop direct-to-chip liquid cooling eliminates water evaporation completely while unlocking 100kW+ rack thermal density. Traditional evaporative cooling consumes 1.8 Liters of fresh water per kWh, whereas closed-loop systems yield zero water loss and a 40% PUE efficiency reduction."
        }
        if not self.memory.is_duplicate(fallback['id']):
            return fallback
        return {}
