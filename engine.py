"""
EcoPulse LinkedIn Engine — Main Orchestrator (v5.0 Viral Post Framework)

8-Phase Pipeline:
  Phase 1: Multi-Source Research              (ResearchEngine — unchanged)
  Phase 2: Component Selection                (CombinationTracker)
  Phase 3: Two-Pass Post Composition          (EditorialEngine)
  Phase 4: Hook Engineering                   (HookEngine)
  Phase 5: Quality Gate Evaluation            (ReviewEngine — retry loop)
  Phase 6: Image Direction                    (ImageDirector)
  Phase 7: Publishing to LinkedIn             (Publisher — unchanged)
  Phase 8: State & Combination Logging        (MemoryEngine + CombinationTracker)

Quality gate retry: if gate fails, re-run Phases 2–5 with adjusted params (max 3 retries).
"""

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
from src.combination_tracker import CombinationTracker
from src.editorial_engine import EditorialEngine
from src.hook_engine import HookEngine
from src.review_engine import ReviewEngine
from src.image_director import ImageDirector
from src.publisher import publish_to_linkedin

MAX_RETRIES = 3


def main():
    log.info("══════════════════════════════════════════════════════════")
    log.info("🚀 EcoPulse LinkedIn Engine v5.0 — Viral Post Framework")
    log.info("══════════════════════════════════════════════════════════")

    # Initialize core engines
    gemini_client = GeminiClient()
    memory_engine = MemoryEngine(state_dir="state")
    research_engine = ResearchEngine(memory_engine, gemini_client)
    combo_tracker = CombinationTracker(state_dir="state")
    editorial_engine = EditorialEngine(gemini_client)
    hook_engine = HookEngine(gemini_client)
    review_engine = ReviewEngine(gemini_client)
    image_director = ImageDirector(gemini_client)

    # ── Phase 1: Multi-Source Research ───────────────────────────────────
    log.info("═══ Phase 1: Multi-Source Research & Deduplication ═══")
    raw_data = research_engine.select_topic()
    if not raw_data or not raw_data.get("raw_text"):
        log.warning("No novel content found today. Gracefully exiting.")
        sys.exit(0)

    source_type = _detect_source_type(raw_data)
    log.info(f"Selected Source: [{raw_data.get('source', 'Unknown')}] {raw_data.get('title', 'Untitled')}")
    log.info(f"Detected source_type: {source_type}")

    # ── Retry loop: Phases 2–5 ──────────────────────────────────────────
    config = None
    gate_result = None

    for attempt in range(1, MAX_RETRIES + 1):
        log.info(f"──── Generation attempt {attempt}/{MAX_RETRIES} ────")

        # ── Phase 2: Component Selection ────────────────────────────────
        log.info("═══ Phase 2: Component Selection ═══")
        config = combo_tracker.select_components(source_type=source_type)
        config.source_ref = raw_data.get("url", raw_data.get("id", ""))

        # ── Phase 3: Two-Pass Post Composition ──────────────────────────
        log.info("═══ Phase 3: Two-Pass Post Composition ═══")
        config = editorial_engine.compose_post(config, raw_data)

        if not config.post_text:
            log.warning("Post composition returned empty text. Retrying...")
            continue

        # ── Phase 4: Hook Engineering ───────────────────────────────────
        log.info("═══ Phase 4: Hook Engineering ═══")
        headline = raw_data.get("title", "")
        core_insight = config.turn_line or config.proof_fact or headline

        hooks = hook_engine.generate_hooks(
            hook_type=config.hook_type,
            headline=headline,
            core_insight=core_insight,
            framing=config.framing,
        )
        best_hook = hook_engine.select_best_hook(hooks, config.hook_type)

        if best_hook:
            # Splice the hook into the post if the current opening is weaker
            config.post_text = _splice_hook(config.post_text, best_hook)
            log.info(f"Selected hook: '{best_hook[:80]}...'")

        # ── Phase 5: Quality Gate Evaluation ────────────────────────────
        log.info("═══ Phase 5: Quality Gate Evaluation ═══")
        gate_result = review_engine.evaluate(
            post_text=config.post_text,
            turn_line=config.turn_line,
            proof_fact=config.proof_fact,
            hook_type=config.hook_type,
            image_style=config.image_style,
            combination_tracker=combo_tracker,
            config=config,
        )

        if gate_result["passed"]:
            log.info(f"✅ Quality Gate PASSED on attempt {attempt}")
            break
        else:
            log.warning(f"❌ Quality Gate FAILED on attempt {attempt}: {gate_result['failures']}")
            if attempt < MAX_RETRIES:
                log.info(f"Suggestions: {gate_result.get('suggestions', [])}")
                log.info("Retrying with fresh component selection...")

    if not gate_result or not gate_result.get("passed"):
        log.error("❌ Quality gate did not pass after all retries. BLOCKING PUBLISH to prevent degraded output.")
        sys.exit(1)

    # ── Phase 6: Image Direction ────────────────────────────────────────
    log.info("═══ Phase 6: Image Direction ═══")
    # Build thesis_data from what we have for the image director
    thesis_data = {
        "headline": raw_data.get("title", ""),
        "turn_line": config.turn_line,
        "proof_fact": config.proof_fact,
        "hard_metric": config.proof_fact,
        "topic_tag": _extract_topic_tag(raw_data),
        "baseline_stat": raw_data.get("metric_1_val", ""),
        "target_stat": raw_data.get("metric_2_val", ""),
    }

    image_path = image_director.generate_image(
        image_style=config.image_style,
        turn_line=config.turn_line,
        thesis_data=thesis_data,
        raw_data=raw_data,
        out_path="state/latest_image.png",
    )
    config.image_path = image_path

    # ── Phase 7: Publishing to LinkedIn ─────────────────────────────────
    log.info("═══ Phase 7: Publishing to LinkedIn ═══")
    pub_res = publish_to_linkedin(config.post_text, image_path)

    # ── Phase 8: State & Combination Logging ────────────────────────────
    log.info("═══ Phase 8: State & Combination Logging ═══")
    if pub_res.get("status") in ["published", "dry_run"]:
        config.post_id = pub_res.get("post_id", "")

        # Save to memory engine (posted_log.json)
        memory_engine.save_history(
            {
                "id": raw_data.get("id"),
                "source": raw_data.get("source"),
                "headline": raw_data.get("title", "")[:60],
                "topic": raw_data.get("theme"),
                "post_id": pub_res.get("post_id"),
                "post_url": pub_res.get("post_url"),
            },
            post_config=config,
        )

        # Save to combination tracker (used_post_combinations.json)
        combo_tracker.log_combination(config)
        log.info("State and combination history recorded.")

    log.info("══════════════════════════════════════════════════════════")
    log.info("✅ EcoPulse v5.0 Pipeline Execution Completed Successfully")
    log.info("══════════════════════════════════════════════════════════")


# ── Helper functions ─────────────────────────────────────────────────────────

def _detect_source_type(raw_data: dict) -> str:
    """Detect the source type from raw_data for framing heuristics."""
    source_id = (raw_data.get("id") or "").lower()
    source_name = (raw_data.get("source") or "").lower()

    if "arxiv" in source_id or "arxiv" in source_name:
        return "arxiv"
    elif "devto" in source_id or "dev.to" in source_name or "engineering insight" in source_name:
        return "devto"
    elif "live_grid" in source_id or "grid" in source_name:
        return "realtime_grid"
    elif "live_climate" in source_id or "co2" in source_name or "atmospheric" in source_name:
        return "realtime_climate"
    elif "hn_" in source_id or "hacker" in source_name:
        return "hn"
    return "default"


def _extract_topic_tag(raw_data: dict) -> str:
    """Extract a short topic tag from raw_data."""
    theme = raw_data.get("theme", "")
    if theme:
        words = theme.split()[:3]
        return " ".join(words).upper()
    title = raw_data.get("title", "INSIGHT")
    words = title.split()[:3]
    return " ".join(words).upper()


def _splice_hook(post_text: str, hook: str) -> str:
    """
    Replace the first 1-2 lines of the post with the generated hook,
    only if the hook is materially different from the current opening.
    """
    lines = post_text.strip().split('\n')
    if not lines:
        return hook + "\n\n" + post_text

    # Check if hook is already similar to the opening
    first_line = lines[0].strip().lower()
    hook_lower = hook.strip().lower()
    if first_line == hook_lower or hook_lower in first_line:
        return post_text  # Hook already matches

    # Find where the "body" starts (skip empty lines after the opening)
    body_start = 1
    for i, line in enumerate(lines[1:], 1):
        if line.strip():
            body_start = i
            break

    body = '\n'.join(lines[body_start:])
    return hook.strip() + "\n\n" + body


if __name__ == "__main__":
    main()
