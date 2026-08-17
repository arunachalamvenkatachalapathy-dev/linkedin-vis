import logging
import sys

logging.basicConfig(level=logging.INFO)
sys.path.append('.')

from src.memory_engine import MemoryEngine
from src.research_engine import ResearchEngine

def test():
    memory = MemoryEngine("state")
    research = ResearchEngine(memory)
    
    print("Testing YouTube Search & Transcript Extraction...")
    data = research.select_topic()
    
    print("\n--- Result ---")
    print(f"Title: {data.get('title')}")
    print(f"Video ID: {data.get('video_id')}")
    print(f"URL: {data.get('url')}")
    print(f"Transcript Length: {len(data.get('transcript_text', ''))} characters")
    
if __name__ == '__main__':
    test()
