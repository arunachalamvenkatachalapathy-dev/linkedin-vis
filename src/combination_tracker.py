"""
Combination Tracker — Rolling Variety Enforcement

Manages state/used_post_combinations.json to track the last N posts' component
selections and enforce variety rules:
  - Hard: no exact (hook_type + body_structure) combo repeat within last 5 posts
  - Hard: no same hook_type or cta_type as immediately previous post
  - Soft: no single framing >30% in trailing 2-week window
"""

import os
import json
import random
import logging
from datetime import datetime, timezone, timedelta

from src.post_config import (
    PostConfig, HOOK_TYPES, FRAMINGS, BODY_STRUCTURES, CTA_TYPES,
    IMAGE_STYLES, LENGTH_PRESETS,
    SOURCE_FRAMING_HINTS, FRAMING_IMAGE_HINTS, FRAMING_LENGTH_HINTS,
)

log = logging.getLogger("ecopulse")

MAX_HISTORY = 15
HARD_COMBO_WINDOW = 5   # no exact (hook+body) repeat in last N
TWO_WEEK_DAYS = 14


class CombinationTracker:
    def __init__(self, state_dir: str = "state"):
        self.state_dir = state_dir
        self.log_path = os.path.join(state_dir, "used_post_combinations.json")
        self.history = self._load()

    def _load(self) -> list:
        if os.path.exists(self.log_path):
            try:
                with open(self.log_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                log.warning(f"Failed to load combination history: {e}")
        return []

    def _save(self):
        os.makedirs(self.state_dir, exist_ok=True)
        with open(self.log_path, "w", encoding="utf-8") as f:
            json.dump(self.history[-MAX_HISTORY:], f, indent=2)

    # ── Variety constraint checks ────────────────────────────────────────

    def _last_n(self, n: int) -> list:
        return self.history[-n:] if len(self.history) >= n else self.history

    def _is_hook_body_repeat(self, hook_type: str, body_structure: str) -> bool:
        """Hard rule: no exact (hook_type + body_structure) in last HARD_COMBO_WINDOW posts."""
        for entry in self._last_n(HARD_COMBO_WINDOW):
            if entry.get("hook_type") == hook_type and entry.get("body_structure") == body_structure:
                return True
        return False

    def _is_immediate_repeat(self, field: str, value: str) -> bool:
        """Hard rule: field value must differ from the immediately previous post."""
        if not self.history:
            return False
        return self.history[-1].get(field) == value

    def _framing_over_threshold(self, framing: str, threshold: float = 0.30) -> bool:
        """Soft rule: no framing >threshold in trailing 2-week window."""
        cutoff = (datetime.now(timezone.utc) - timedelta(days=TWO_WEEK_DAYS)).isoformat()
        recent = [e for e in self.history if e.get("date", "") >= cutoff]
        if len(recent) < 3:
            return False
        count = sum(1 for e in recent if e.get("framing") == framing)
        return (count / len(recent)) > threshold

    # ── Component selection ──────────────────────────────────────────────

    def select_components(self, source_type: str = "default") -> PostConfig:
        """
        Picks one option from each menu, respecting variety constraints.
        Uses source-type heuristics for framing/image/length suggestions.
        """
        config = PostConfig(source_type=source_type)

        # 1. Select framing (source-type heuristic + variety)
        preferred_framings = list(SOURCE_FRAMING_HINTS.get(source_type, SOURCE_FRAMING_HINTS["default"]))
        
        # WEEKLY SERIES SLOT (Section 12)
        # Bias toward `data_breakdown` once per rolling 7 days.
        cutoff_7d = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
        recent_7d = [e for e in self.history if e.get("date", "") >= cutoff_7d]
        if not any(e.get("framing") == "data_breakdown" for e in recent_7d):
            preferred_framings.insert(0, "data_breakdown")

        config.framing = self._pick_with_constraints(
            preferred_framings + FRAMINGS,
            reject_fn=lambda f: self._framing_over_threshold(f) or self._is_immediate_repeat("framing", f),
            fallback=random.choice(FRAMINGS)
        )

        # 2. Select hook_type (avoid immediate repeat)
        config.hook_type = self._pick_with_constraints(
            random.sample(HOOK_TYPES, len(HOOK_TYPES)),
            reject_fn=lambda h: self._is_immediate_repeat("hook_type", h),
            fallback=random.choice(HOOK_TYPES)
        )

        # 3. Select body_structure (avoid hook+body combo repeat)
        config.body_structure = self._pick_with_constraints(
            random.sample(BODY_STRUCTURES, len(BODY_STRUCTURES)),
            reject_fn=lambda b: self._is_hook_body_repeat(config.hook_type, b),
            fallback=random.choice(BODY_STRUCTURES)
        )

        # 4. Select CTA (avoid immediate repeat)
        config.cta_type = self._pick_with_constraints(
            random.sample(CTA_TYPES, len(CTA_TYPES)),
            reject_fn=lambda c: self._is_immediate_repeat("cta_type", c),
            fallback=random.choice(CTA_TYPES)
        )

        # 5. Select image_style (framing heuristic + avoid immediate repeat)
        preferred_images = FRAMING_IMAGE_HINTS.get(config.framing, IMAGE_STYLES)
        config.image_style = self._pick_with_constraints(
            preferred_images + IMAGE_STYLES,
            reject_fn=lambda i: self._is_immediate_repeat("image_style", i),
            fallback=random.choice(IMAGE_STYLES)
        )

        # 6. Select length_preset (framing heuristic)
        preferred_lengths = FRAMING_LENGTH_HINTS.get(config.framing, ["standard"])
        config.length_preset = random.choice(preferred_lengths)

        log.info(
            f"📋 Selected components: hook={config.hook_type}, frame={config.framing}, "
            f"body={config.body_structure}, length={config.length_preset}, "
            f"cta={config.cta_type}, image={config.image_style}"
        )
        return config

    def _pick_with_constraints(self, candidates: list, reject_fn, fallback: str) -> str:
        """Pick the first candidate that passes reject_fn, else return fallback."""
        seen = set()
        for c in candidates:
            if c in seen:
                continue
            seen.add(c)
            if not reject_fn(c):
                return c
        return fallback

    # ── Logging ──────────────────────────────────────────────────────────

    def log_combination(self, config: PostConfig):
        """Append this post's component selection to the rolling history."""
        entry = config.combo_summary()
        entry["date"] = datetime.now(timezone.utc).isoformat()
        entry["post_id"] = config.post_id
        self.history.append(entry)
        self._save()
        log.info(f"📝 Logged combination: {config.combination_key()}")
