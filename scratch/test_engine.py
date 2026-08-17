import logging
import sys

logging.basicConfig(level=logging.INFO)
sys.path.append('.')

from src.memory_engine import MemoryEngine
from src.research_engine import ResearchEngine
from src.gemini_client import GeminiClient

def test():
    memory = MemoryEngine("state")
    gemini = GeminiClient()
    research = ResearchEngine(memory, gemini)
    
    print("Testing ArXiv Search & Abstract Extraction...")
    data = research.select_topic()
    
    print("\n--- Result ---")
    print(f"Title: {data.get('title')}")
    print(f"ID: {data.get('id')}")
    print(f"URL: {data.get('url')}")
    print(f"Abstract Length: {len(data.get('raw_text', ''))} characters")
    
if __name__ == '__main__':
    test()
