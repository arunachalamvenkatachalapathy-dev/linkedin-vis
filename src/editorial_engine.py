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
    CLICHE_PHRASES,
)

log = logging.getLogger("ecopulse")


# ── Cliché blacklist imported from post_config ─────────────────────────────

class EditorialEngine:
    def __init__(self, gemini_client):
        self.llm = gemini_client

    def compose_post(self, config: PostConfig, raw_data: dict) -> PostConfig:
        """
        Two-pass post composition:
          Pass 1 → Draft full post (or carousel slide deck) using selected modules
          Pass 2 → Extract and sharpen the Turn line
        Returns the updated PostConfig with post_text, proof_fact, turn_line, slides.
        """
        # Pass 1: Draft
        if config.post_format == "carousel":
            config = self._pass1_draft_carousel(config, raw_data)
        else:
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

        from datetime import datetime as _dt
        _niche_day = _dt.utcnow().weekday()  # 0=Mon, 6=Sun
        _is_ai_day = (_niche_day % 2 == 0)  # Mon/Wed/Fri/Sun → AI Engineering
        _persona = (
            "Arunachalam Venkatachalapathy — a Senior AI & Forward Deployment Engineer "
            "who architects enterprise sustainability systems, Scope 3 tracking frameworks, and data-driven ESG solutions. "
            "Your voice is that of someone who has debugged these systems at 2 AM, not someone describing them from a whitepaper."
            if _is_ai_day else
            "Arunachalam Venkatachalapathy — a CleanTech & ESG Systems Engineer "
            "who works on grid decarbonization, BRSR compliance, industrial Scope 3 measurement, and clean energy systems. "
            "Your voice is that of someone who has read the emissions sensor data, not just the sustainability report."
        )
        _tone_rule = (
            "VOICE: Sharp, technical, zero corporate fluff. Write like a senior engineer explaining this to another senior engineer "
            "at a whiteboard. No 'leverage', no 'ecosystem', no 'unlock value'. Name the specific failure mode, the specific system, "
            "the specific number. If a sentence could appear in a McKinsey deck, delete it and rewrite."
        )

        prompt = f"""You are a top-performing LinkedIn content strategist writing a post for {_persona}

VOICE & TONE:
{_tone_rule}

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

STORYTELLING RULES (critical for reach):
- TENSION ARC: Every post must have a setup → tension → resolution structure. Name what the reader ASSUMES, then break that assumption with evidence.
- SPECIFICITY: Never say "many companies" — say "a Fortune 500 manufacturer" or "a 200-person DevOps team". Concrete details create credibility.
- MICRO-STORY: For narrative framings, include at least one scene with a specific moment (a time, a place, a reaction). "The dashboard turned red at 2:47 AM" beats "systems sometimes fail."
- CONTRAST: The strongest posts name what most people do WRONG before showing what works. Start from the reader's current belief.

FORMATTING RULES:
- Short paragraphs: 1–3 lines max, then a line break. LinkedIn's feed is narrow.
- No more than one emoji per 100 words, never as bullet replacements (no ☑️➡️📌).
- Do NOT use "Agree?", "Thoughts?", "🔥" as standalone lines.
- Maximum 2–3 hashtags, placed inline or at the very end.
- Vary paragraph rhythm — don't make every paragraph the same length.
- No markdown formatting (no **, no #, no bullet points with - or *). Use plain text only.
- For emphasis, use CAPS sparingly or Unicode bold characters.
- WHITESPACE: Use generous line breaks. A wall of text kills engagement.

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

    # ── Pass 1: Carousel Draft Generation ────────────────────────────────

    def _pass1_draft_carousel(self, config: PostConfig, raw_data: dict) -> PostConfig:
        raw_text = raw_data.get("raw_text", "")
        title = raw_data.get("title", "")
        source_name = raw_data.get("source", "")

        hook_desc = HOOK_PATTERNS.get(config.hook_type, "")
        frame_desc = FRAMING_DESCRIPTIONS.get(config.framing, "")
        body_desc = BODY_STRUCTURE_DESCRIPTIONS.get(config.body_structure, "")
        cta_desc = CTA_DESCRIPTIONS.get(config.cta_type, "")

        prompt = f"""You are a top-performing LinkedIn content strategist creating an 8 to 10 SLIDE CAROUSEL (PDF document post) for Arunachalam Venkatachalapathy, an Sustainability Professional in CleanTech / ESG systems.

SOURCE MATERIAL:
Title: {title}
Source: {source_name}
Content:
{raw_text[:4000]}

INSTRUCTIONS — Create a carousel slide deck (EXACTLY 8 to 10 slides) and a short caption using these selected modules:

HOOK TYPE: {config.hook_type}
{hook_desc}
Slide 1 MUST be the hook. Under 12 words. No emoji in hook line.

FRAMING: {config.framing}
{frame_desc}

BODY STRUCTURE: {config.body_structure} — {body_desc}

CTA TYPE: {config.cta_type}
{cta_desc}
Final slide MUST be the CTA.

SLIDE REQUIREMENTS (8 slides total) — STORYTELLING ARC:
- Slide 1 (role: "hook"): Hook line (≤12 words). MUST be clear and stop the scroll.
- Slide 2, 3, 4, 5 (role: "story"): Storytelling based on the content. Guide the reader through the narrative organically without rigid bullet points.
- Slide 6 (role: "takeaway"): Start revealing the most important takeaway from the source.
- Slide 7, 8 (role: "freedom"): You have creative freedom for these two slides (could be further insights, conclusion, or a CTA in slide 8). Final slide MUST ask the audience to "Follow for more on sustainability."

CAPTION:
Short LinkedIn caption (150-300 characters). First line MUST be the hook. The carousel PDF carries the depth, not the caption.

ADDITIONAL CONTEXT FIELDS:
- "subtitle": A short source attribution line for the cover slide (e.g., "ArXiv Research · Clean Computing" or "Live Grid Telemetry · ESG Systems"). Max 6 words.
- "metric_preview": The single most impactful number from the source (e.g., "95% reduction", "64 gCO2/kWh", "78% failure rate"). This appears prominently on the cover slide.

CLICHÉ FILTER — Do NOT use any of these:
{', '.join(f'"{c}"' for c in CLICHE_PHRASES[:8])}

Return ONLY valid JSON:
{{
  "slides": [
    {{"role": "hook", "text": "..."}},
    {{"role": "context", "text": "..."}},
    {{"role": "point", "text": "..."}},
    {{"role": "point", "text": "..."}},
    {{"role": "point", "text": "..."}},
    {{"role": "point", "text": "..."}},
    {{"role": "proof", "text": "..."}},
    {{"role": "cta", "text": "..."}}
  ],
  "caption": "short caption under 300 characters",
  "proof_fact": "the single concrete citable fact",
  "subtitle": "short source line for cover slide",
  "metric_preview": "the key number for the cover slide"
}}"""

        try:
            res = self.llm.generate_text(prompt, temperature=0.65, json_mode=True)
            if res:
                parsed = json.loads(res)
                slides = parsed.get("slides", [])
                caption = parsed.get("caption", "").strip()
                proof = parsed.get("proof_fact", "").strip()
                subtitle = parsed.get("subtitle", "").strip()
                metric_preview = parsed.get("metric_preview", "").strip()
                if slides and len(slides) >= 6:
                    config.slides = slides
                    config.post_text = caption
                    config.proof_fact = proof
                    config.carousel_subtitle = subtitle
                    config.carousel_metric = metric_preview
                    log.info(f"Pass 1 carousel draft: {len(slides)} slides, caption len={len(caption)}")
                    return config
        except Exception as e:
            log.warning(f"Pass 1 carousel draft generation failed: {e}")

        return self._fallback_carousel(config, raw_data)

    def _fallback_carousel(self, config: PostConfig, raw_data: dict) -> PostConfig:
        title = raw_data.get("title", "Engineering Systems")
        config.slides = [
            {"role": "hook", "text": f"{title}: The Engineering Fix."},
            {"role": "context", "text": "Most infrastructure teams optimize for the headline instead of system architecture."},
            {"role": "point", "text": "1. Identify thermal bottlenecks in AI datacenter compute allocation."},
            {"role": "point", "text": "2. Track grid carbon intensity at 15-minute telemetry intervals."},
            {"role": "point", "text": "3. Shift heavy workloads dynamically during clean energy peaks."},
            {"role": "point", "text": "4. Automate closed-loop evaporative cooling systems for water efficiency."},
            {"role": "proof", "text": "Measured carbon intensity reduced to 64 gCO2/kWh (60.2% clean power)."},
            {"role": "cta", "text": "Save this 8-slide framework for your next infrastructure review."}
        ]
        config.post_text = f"{title}\n\nSwipe through the 8-slide framework for clean computing systems."
        config.proof_fact = "64 gCO2/kWh"
        config.carousel_subtitle = "Engineering Systems Framework"
        config.carousel_metric = "64 gCO2/kWh"
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
            log.warning(f"Pass 2 turn line extraction failed ({e}) — FALLING BACK to heuristic extraction.")
            sentences = [s.strip() for s in config.post_text.replace('\n', ' ').split('.') if len(s.strip()) >= 30]
            if sentences:
                contrast_words = ["but", "instead", "actually", "not", "unless"]
                candidates = []
                for s in sentences:
                    lower_words = s.lower().split()
                    has_contrast = any(w in lower_words for w in contrast_words)
                    has_number = any(char.isdigit() for char in s)
                    if has_contrast or has_number:
                        candidates.append(s)
                
                if candidates:
                    config.turn_line = min(candidates, key=len) + "."
                else:
                    config.turn_line = sentences[0] + "."

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
