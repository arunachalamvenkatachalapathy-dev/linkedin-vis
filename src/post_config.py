"""
Post Composition Configuration — Modular Component Definitions

Defines the selectable enums (hook types, framings, body structures, CTAs,
image styles, length presets) and the PostConfig dataclass that parameterizes
each generation call through the pipeline.

Reference: LinkedIn Viral Post Framework Sections 2–10.
"""

from dataclasses import dataclass, field, asdict
from typing import Optional

# ── Section 13: Cliché Blacklist ─────────────────────────────────────────────

CLICHE_PHRASES = [
    "In today's fast-paced world",
    "In today's world",
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
    "💯🔥🚀",
    "Agree?",
    "Thoughts?",
    "Let me know in the comments",
    "I'm excited to share",
    "I recently",
    "I wanted to share",
]
# ── Section 2: Hook Library ──────────────────────────────────────────────────

HOOK_TYPES = [
    "contrarian",        # State the opposite of common belief
    "confession",        # Admit a mistake / past wrong belief
    "number_shock",      # Lead with a stark, specific stat
    "direct_address",    # Speak straight to a specific reader
    "story_cold_open",   # Drop into a scene, no context
    "question_trap",     # Ask something the reader can't NOT answer
    "pattern_interrupt",  # Short, blunt, un-LinkedIn-like sentence
    "curiosity_gap",     # Promise a payoff without revealing it
]

HOOK_PATTERNS = {
    "contrarian":        "State the opposite of common belief. Shape: 'Everyone says X. After Y, I think that's backwards.'",
    "confession":        "Admit a mistake, bias, or past wrong belief. Shape: 'I was wrong about [topic] for 3 years.'",
    "number_shock":      "Lead with a stark, specific stat. Shape: '97% of [group] do this. It's costing them [X].'",
    "direct_address":    "Speak straight to a specific reader. Shape: 'If you're a [role] reading this before 9 AM—stop.'",
    "story_cold_open":   "Drop into a scene with no context. Shape: 'The email came in at 11:47 PM. Subject line: We need to talk.'",
    "question_trap":     "Ask something the reader can't NOT answer in their head. Shape: 'What if the thing you're optimizing for is the reason you're stuck?'",
    "pattern_interrupt":  "Short, blunt, un-LinkedIn-like sentence. Shape: 'This is going to sound harsh.'",
    "curiosity_gap":     "Promise a payoff without revealing it. Shape: 'There's a reason [outcome] keeps happening. It's not what you think.'",
}

# ── Section 3: Framing Menu ─────────────────────────────────────────────────

FRAMINGS = [
    "narrative",             # "this happened to me"
    "industry_observation",  # "here's a pattern I'm seeing"
    "data_breakdown",        # "here's what the numbers actually say"
    "myth_bust",             # "here's what's wrong with the common take"
    "framework_howto",       # "here's the system I use"
    "prediction",            # "here's where this is headed and why"
    "case_study",            # "here's what happened when [entity] did X"
]

FRAMING_DESCRIPTIONS = {
    "narrative":             "Personal narrative — 'this happened to me'. Best for personal events, lessons, behind-the-scenes stories.",
    "industry_observation":  "Industry observation — 'here's a pattern I'm seeing'. Best for trend commentary, market shifts.",
    "data_breakdown":        "Data breakdown — 'here's what the numbers actually say'. Best for research papers, statistics, metrics.",
    "myth_bust":             "Myth-bust / debunk — 'here's what's wrong with the common take'. Best for contrarian angles.",
    "framework_howto":       "Framework / how-to — 'here's the system I use'. Best for tactical advice, recurring questions.",
    "prediction":            "Prediction / opinion — 'here's where this is headed and why'. Best for forward-looking takes.",
    "case_study":            "Case study — 'here's what happened when [entity] did X'. Best for real-world examples.",
}

# ── Section 4: Body Structure Menu ───────────────────────────────────────────

BODY_STRUCTURES = ["A", "B", "C", "D", "E"]

BODY_STRUCTURE_DESCRIPTIONS = {
    "A": (
        "Problem → Insight → Reframe:\n"
        "1. Name a real, specific pain point (not generic)\n"
        "2. Explain *why* the obvious fix doesn't work\n"
        "3. Offer the non-obvious reframe"
    ),
    "B": (
        "Before → After → Bridge:\n"
        "1. Old state (belief, method, result)\n"
        "2. New state (belief, method, result)\n"
        "3. The one change that bridged them"
    ),
    "C": (
        "List-with-a-twist:\n"
        "1. Short intro line\n"
        "2. 3–5 punchy points (one line each, no fluff, use line breaks not bullets)\n"
        "3. One point that contradicts the pattern of the others"
    ),
    "D": (
        "Story → Lesson → Universal Truth:\n"
        "1. Specific, concrete anecdote (names, numbers, moment)\n"
        "2. What it taught\n"
        "3. Zoom out to a principle anyone can apply"
    ),
    "E": (
        "Data Deep-Dive:\n"
        "1. The number that matters\n"
        "2. Why it's surprising / what people assume instead\n"
        "3. What it means for the reader specifically"
    ),
}

# ── Section 7: CTA Menu ─────────────────────────────────────────────────────

CTA_TYPES = [
    "soft_mirror",    # "Curious if others in [industry] are seeing the same thing."
    "specific_ask",   # "What's the one metric you'd add to this list?"
    "value_forward",  # "I broke down the full framework here → [link/comment]"
    "silent",         # No explicit ask — let the Turn line do the work
    "save_bait",      # "Bookmarking this for the next time [situation] comes up."
]

CTA_DESCRIPTIONS = {
    "soft_mirror":   "Soft mirror — 'Curious if others in [industry] are seeing the same thing.'",
    "specific_ask":  "Specific ask — 'What's the one metric you'd add to this list?'",
    "value_forward": "Value-forward — 'I broke down the full framework here → [link/comment]' (only if genuinely offering something)",
    "silent":        "Silent CTA — no explicit ask, let the Turn line do the work (best for high-authority/narrative posts)",
    "save_bait":     "Save-bait — 'Bookmarking this for the next time [situation] comes up.' (only when content is genuinely reference-worthy)",
}

# ── Section 8: Length Presets ────────────────────────────────────────────────

LENGTH_PRESETS = {
    "punch":    {"min_words": 50,  "max_words": 90,  "best_for": "Contrarian takes, single-insight posts"},
    "standard": {"min_words": 150, "max_words": 250, "best_for": "Most posts — narrative or framework"},
    "deep":     {"min_words": 300, "max_words": 450, "best_for": "Data breakdowns, case studies, multi-point frameworks"},
}

# ── Section 10: Image Style Menu ────────────────────────────────────────────

IMAGE_STYLES = [
    "text_on_card",           # Bold single statement or stat, quote card style
    "data_visual",            # Clean chart/graph rendering
    "diagram_framework",      # Simple flow or 3-4 step visual
    "editorial_illustration",  # Abstract/metaphorical illustration via Gemini native image gen
    "before_after_split",     # Two-panel visual contrast
]

VISUAL_VARIANTS = ["variant_a", "variant_b", "variant_c"]

IMAGE_STYLE_DESCRIPTIONS = {
    "text_on_card":           "Bold single statement or stat, high contrast, minimal — treat as a 'quote card'. Best for punch/data posts using the Turn line itself.",
    "data_visual":            "Clean chart/graph rendering the one key number — no decorative chart junk. Best for data breakdown framing.",
    "diagram_framework":      "Simple flow or 3–4 step visual — labeled, not decorative. Best for framework/how-to framing.",
    "editorial_illustration":  "Abstract or metaphorical illustration matching the story's emotional beat, not literal depiction. Best for narrative/story framing.",
    "before_after_split":     "Two-panel visual contrast. Best for Before→After body structure.",
}

# ── Source-type to framing heuristics ────────────────────────────────────────

SOURCE_FRAMING_HINTS = {
    "arxiv":             ["data_breakdown", "prediction", "myth_bust"],
    "devto":             ["framework_howto", "narrative", "case_study"],
    "realtime_grid":     ["data_breakdown", "industry_observation"],
    "realtime_climate":  ["data_breakdown", "industry_observation", "prediction"],
    "hn":                ["industry_observation", "myth_bust", "narrative"],
    "default":           ["data_breakdown", "industry_observation", "framework_howto"],
}

# Framing → suggested image styles
FRAMING_IMAGE_HINTS = {
    "narrative":             ["editorial_illustration", "text_on_card"],
    "industry_observation":  ["text_on_card", "data_visual"],
    "data_breakdown":        ["data_visual", "text_on_card"],
    "myth_bust":             ["text_on_card", "before_after_split"],
    "framework_howto":       ["diagram_framework", "text_on_card"],
    "prediction":            ["editorial_illustration", "text_on_card"],
    "case_study":            ["before_after_split", "data_visual"],
}

# Framing → suggested length presets
FRAMING_LENGTH_HINTS = {
    "narrative":             ["standard", "deep"],
    "industry_observation":  ["standard", "punch"],
    "data_breakdown":        ["deep", "standard"],
    "myth_bust":             ["standard", "punch"],
    "framework_howto":       ["deep", "standard"],
    "prediction":            ["standard", "punch"],
    "case_study":            ["deep", "standard"],
}


# ── PostConfig Dataclass ────────────────────────────────────────────────────

@dataclass
class PostConfig:
    """Configuration for a single post generation run."""
    post_id: str = ""
    source_ref: str = ""
    source_type: str = ""

    # Selected components (one from each menu)
    hook_type: str = "contrarian"
    framing: str = "data_breakdown"
    body_structure: str = "A"
    length_preset: str = "standard"
    cta_type: str = "soft_mirror"
    image_style: str = "text_on_card"
    visual_variant: str = "variant_a"

    # Extracted during generation
    proof_fact: str = ""
    turn_line: str = ""

    # Generated content
    post_text: str = ""
    image_path: str = ""

    def to_dict(self) -> dict:
        return asdict(self)

    def combination_key(self) -> str:
        """Returns a string key representing the component combination."""
        return f"{self.hook_type}|{self.body_structure}|{self.framing}|{self.cta_type}|{self.image_style}|{self.visual_variant}"

    def combo_summary(self) -> dict:
        """Returns the fields tracked for variety enforcement."""
        return {
            "hook_type": self.hook_type,
            "framing": self.framing,
            "body_structure": self.body_structure,
            "cta_type": self.cta_type,
            "image_style": self.image_style,
            "visual_variant": self.visual_variant,
            "length_preset": self.length_preset,
        }
