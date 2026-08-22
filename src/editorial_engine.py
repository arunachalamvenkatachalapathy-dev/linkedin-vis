"""
Editorial Engine — Two-Pass Gemini Post Composer

Pass 1: Draft generation using selected modules (hook_type, framing, body_structure, etc.)
Pass 2: Turn line extraction & sharpening — extract one quotable standalone sentence.

Replaces the old monolithic thesis generation with a config-driven, modular approach.
"""

import json
import logging

from src.post_config import (
    PostConfig,
    HOOK_PATTERNS, FRAMING_DESCRIPTIONS,
    BODY_STRUCTURE_DESCRIPTIONS, CTA_DESCRIPTIONS,
    LENGTH_PRESETS,
)

log = logging.getLogger("ecopulse")


# ── Cliché blacklist (Section 13) ────────────────────────────────────────────

CLICHE_PHRASES = [
    "In today's fast-paced world",
    "Let that sink in",
    "Here's the thing",
    "I'm not going to lie",
    "Not going to lie",
    "game-changer",
    "game changer",
    "paradigm shift",
    "synergy",
    "Repost if you agree",
    "Tag someone who needs this",
    "🚀🔥💯",
    "Agree?",
    "Thoughts?",
    "Let me know in the comments",
]


class EditorialEngine:
    def __init__(self, gemini_client):
        self.llm = gemini_client

    def compose_post(self, config: PostConfig, raw_data: dict) -> PostConfig:
        """
        Two-pass post composition:
          Pass 1 → Draft the full post using selected modules
          Pass 2 → Extract and sharpen the Turn line
        Returns the updated PostConfig with post_text, proof_fact, turn_line.
        """
        # Pass 1: Draft
        config = self._pass1_draft(config, raw_data)

        # Pass 2: Turn line extraction
        if config.post_text:
            config = self._pass2_turn_line(config)

        return config

    # ── Pass 1: Draft Generation ─────────────────────────────────────────

    def _pass1_draft(self, config: PostConfig, raw_data: dict) -> PostConfig:
        raw_text = raw_data.get("raw_text", "")
        title = raw_data.get("title", "")
        source_name = raw_data.get("source", "")

        hook_desc = HOOK_PATTERNS.get(config.hook_type, "")
        frame_desc = FRAMING_DESCRIPTIONS.get(config.framing, "")
        body_desc = BODY_STRUCTURE_DESCRIPTIONS.get(config.body_structure, "")
        cta_desc = CTA_DESCRIPTIONS.get(config.cta_type, "")
        length_spec = LENGTH_PRESETS.get(config.length_preset, LENGTH_PRESETS["standard"])

        prompt = f"""You are a top-performing LinkedIn content strategist writing a post for Arunachalam Venkatachalapathy, an AI Agent & Forward Deployment Engineer who also works in environmental engineering / CleanTech / ESG systems.

SOURCE MATERIAL:
Title: {title}
Source: {source_name}
Content:
{raw_text[:4000]}

INSTRUCTIONS — Write a LinkedIn post using EXACTLY these selected modules:

HOOK TYPE: {config.hook_type}
{hook_desc}
Rules: First line must be ≤12 words. Never start with "I" + mundane verb ("I recently...", "I wanted to..."). No emoji in the hook line.

FRAMING: {config.framing}
{frame_desc}

BODY STRUCTURE: {config.body_structure} — {body_desc}

LENGTH: {config.length_preset} ({length_spec['min_words']}–{length_spec['max_words']} words total)

CTA TYPE: {config.cta_type}
{cta_desc}

FORMATTING RULES:
- Short paragraphs: 1–3 lines max, then a line break. LinkedIn's feed is narrow.
- No more than one emoji per 100 words, never as bullet replacements (no ☑️➡️📌).
- Do NOT use "Agree?", "Thoughts?", "🔥" as standalone lines.
- Maximum 2–3 hashtags, placed inline or at the very end.
- Vary paragraph rhythm — don't make every paragraph the same length.
- No markdown formatting (no **, no #, no bullet points with - or *). Use plain text only.
- For emphasis, use CAPS sparingly or Unicode bold characters.

PROOF REQUIREMENT:
Extract ONE precise, specific, citable fact from the source material (a number, a named source, a dataset, a timeframe). This must appear in the post body. Do not average the source into vague paraphrase.

CLICHÉ FILTER — Do NOT use any of these:
{', '.join(f'"{c}"' for c in CLICHE_PHRASES[:8])}

Return ONLY valid JSON:
{{
  "post_text": "the full post text ready to publish",
  "proof_fact": "the one concrete data point extracted from the source"
}}"""

        try:
            res = self.llm.generate_text(prompt, temperature=0.65, json_mode=True)
            if res:
                parsed = json.loads(res)
                config.post_text = parsed.get("post_text", "").strip()
                config.proof_fact = parsed.get("proof_fact", "").strip()
                log.info(f"Pass 1 draft: {len(config.post_text.split())} words, proof_fact='{config.proof_fact[:60]}...'")
                return config
        except Exception as e:
            log.warning(f"Pass 1 draft generation failed: {e}")

        # Fallback: minimal structured post
        config.post_text = self._fallback_post(config, raw_data)
        config.proof_fact = title
        return config

    # ── Pass 2: Turn Line Extraction ─────────────────────────────────────

    def _pass2_turn_line(self, config: PostConfig) -> PostConfig:
        prompt = f"""You are a senior editor. Read this LinkedIn post and extract or generate ONE single sentence that:
1. Could stand alone as a quotable line (the kind people screenshot)
2. Flips the reader's assumption, states the cost of NOT knowing this, or compresses the whole insight

POST:
{config.post_text}

Return ONLY valid JSON:
{{
  "turn_line": "the one quotable sentence",
  "improved_post": "the full post text with the turn line given its own paragraph for emphasis (do not add bold markers or special formatting — just ensure it stands alone as its own short paragraph)"
}}"""

        try:
            res = self.llm.generate_text(prompt, temperature=0.4, json_mode=True)
            if res:
                parsed = json.loads(res)
                turn = parsed.get("turn_line", "").strip()
                improved = parsed.get("improved_post", "").strip()
                if turn:
                    config.turn_line = turn
                if improved and len(improved) > len(config.post_text) * 0.5:
                    config.post_text = improved
                log.info(f"Pass 2 turn line: '{config.turn_line[:80]}...'")
        except Exception as e:
            log.warning(f"Pass 2 turn line extraction failed: {e}")
            # Extract a candidate manually — pick the longest sentence
            sentences = [s.strip() for s in config.post_text.replace('\n', ' ').split('.') if len(s.strip()) > 30]
            if sentences:
                config.turn_line = max(sentences, key=len) + "."

        return config

    # ── Fallback ─────────────────────────────────────────────────────────

    def _fallback_post(self, config: PostConfig, raw_data: dict) -> str:
        title = raw_data.get("title", "Engineering Systems")
        summary = raw_data.get("raw_text", "")[:300]
        return (
            f"{title}\n\n"
            f"{summary}\n\n"
            f"The engineering details matter more than the headline.\n\n"
            f"#Engineering #Systems"
        )
