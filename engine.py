import os
import sys
import logging
from dotenv import load_dotenv

load_dotenv()

# Set up logging before importing src modules
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
    log.info("═══ Starting LinkedIn Autopilot v3.0 (Gemini Engine) ═══")

    # 1. Initialize core engines
    gemini_client = GeminiClient()
    memory_engine = MemoryEngine(state_dir="state")
    research_engine = ResearchEngine(memory_engine, gemini_client)
    editorial_engine = EditorialEngine(gemini_client)
    hook_engine = HookEngine(gemini_client)
    review_engine = ReviewEngine(gemini_client)
    image_director = ImageDirector(gemini_client)

    # 2. Research & Selection
    log.info("═══ Phase 1: Research & Deduplication ═══")
    raw_data = research_engine.select_topic()
    log.info(f"Selected Topic Source: {raw_data.get('title', raw_data.get('headline', 'Fallback'))}")

    # 3. Editorial Thesis Generation
    log.info("═══ Phase 2: Editorial Thesis Generation ═══")
    thesis = editorial_engine.generate_thesis(raw_data)
    if not thesis:
        log.error("Failed to generate thesis. Aborting.")
        sys.exit(1)

    # 4. Hook Engineering
    log.info("═══ Phase 3: Hook Engineering ═══")
    hooks = hook_engine.generate_hooks(thesis)
    best_hook = hook_engine.select_best_hook(hooks)
    if not best_hook:
        log.error("Failed to generate hooks. Aborting.")
        sys.exit(1)

    # 5. Drafting & Review
    log.info("═══ Phase 4: Quality Review & Formatting ═══")
    final_post_text = review_engine.draft_and_review(best_hook, thesis)

    # 6. Image Generation
    log.info("═══ Phase 5: Image Director (Documentary Style) ═══")
    image_path = image_director.generate_image(thesis, out_path="state/latest_documentary.png")

    # 7. Publishing
    log.info("═══ Phase 6: Publishing to LinkedIn ═══")
    try:
        pub_res = publish_to_linkedin(final_post_text, image_path)
    except Exception as e:
        log.error(f"Failed to publish to LinkedIn: {e}")
        pub_res = {"status": "dry_run", "post_id": None, "post_url": None}
        
    with open("scratch/sample_post.txt", "w", encoding="utf-8") as f:
        f.write("FINAL GENERATED POST TEXT:\n")
        f.write("="*50 + "\n")
        f.write(final_post_text + "\n")
        f.write("="*50 + "\n")

    # 8. Memory Logging
    if pub_res.get("status") in ["published", "dry_run"]:
        memory_engine.save_history({
            "id": raw_data.get("id"),
            "source": raw_data.get("source"),
            "headline": thesis.get("headline"),
            "topic": thesis.get("topic"),
            "post_id": pub_res.get("post_id"),
            "post_url": pub_res.get("post_url")
        })

    log.info("═══ Pipeline Execution Completed Successfully ═══")

if __name__ == "__main__":
    main()
