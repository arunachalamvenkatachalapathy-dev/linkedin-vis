import os
import sys
import logging
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
log = logging.getLogger("ecopulse")

from src.gemini_client import GeminiClient
from src.memory_engine import MemoryEngine
from src.research_engine import ResearchEngine
from src.editorial_engine import EditorialEngine
from src.hook_engine import HookEngine
from src.review_engine import ReviewEngine
from src.image_director import ImageDirector
from src.publisher import publish_to_linkedin

def main():
    log.info("══════════════════════════════════════════════════════════")
    log.info("🚀 Starting EcoPulse LinkedIn Insight Engine (v4.0 Unified)")
    log.info("══════════════════════════════════════════════════════════")

    # 1. Initialize core engines
    gemini_client = GeminiClient()
    memory_engine = MemoryEngine(state_dir="state")
    research_engine = ResearchEngine(memory_engine, gemini_client)
    editorial_engine = EditorialEngine(gemini_client)
    hook_engine = HookEngine(gemini_client)
    review_engine = ReviewEngine(gemini_client)
    image_director = ImageDirector(gemini_client)

    # 2. Phase 1: Multi-Source Research
    log.info("═══ Phase 1: Multi-Source Research & Deduplication ═══")
    raw_data = research_engine.select_topic()
    if not raw_data or not raw_data.get('raw_text'):
        log.warning("No novel content found today. Gracefully exiting.")
        sys.exit(0)

    log.info(f"Selected Source: [{raw_data.get('source', 'Unknown')}] {raw_data.get('title', 'Untitled')}")

    # 3. Phase 2: Editorial Thesis Generation
    log.info("═══ Phase 2: Editorial Thesis Generation ═══")
    thesis = editorial_engine.generate_thesis(raw_data)
    if not thesis:
        log.error("Failed to generate thesis. Aborting.")
        sys.exit(1)

    log.info(f"Thesis Headline: {thesis.get('headline')}")

    # 4. Phase 3: Hook Engineering
    log.info("═══ Phase 3: Hook Engineering ═══")
    hooks = hook_engine.generate_hooks(thesis)
    best_hook = hook_engine.select_best_hook(hooks)
    if not best_hook:
        best_hook = thesis.get('headline', '')
    log.info(f"Selected Hook: {best_hook}")

    # 5. Phase 4: Quality Review & Formatting
    log.info("═══ Phase 4: Quality Review & Formatting ═══")
    final_post_text = review_engine.draft_and_review(best_hook, thesis)

    # 6. Phase 5: Image Direction
    log.info("═══ Phase 5: Image Direction ═══")
    image_path = image_director.generate_image(thesis, out_path="state/latest_image.png")

    # 7. Phase 6: Publishing to LinkedIn
    log.info("═══ Phase 6: Publishing to LinkedIn ═══")
    pub_res = publish_to_linkedin(final_post_text, image_path)

    # 8. Phase 7: Memory State Update
    if pub_res.get("status") in ["published", "dry_run"]:
        memory_engine.save_history({
            "id": raw_data.get("id"),
            "source": raw_data.get("source"),
            "headline": thesis.get("headline"),
            "topic": thesis.get("topic"),
            "post_id": pub_res.get("post_id"),
            "post_url": pub_res.get("post_url")
        })
        log.info("State recorded in memory history.")

    log.info("══════════════════════════════════════════════════════════")
    log.info("✅ EcoPulse Pipeline Execution Completed Successfully")
    log.info("══════════════════════════════════════════════════════════")

if __name__ == "__main__":
    main()
