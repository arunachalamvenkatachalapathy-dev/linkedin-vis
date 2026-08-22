"""
Memory Engine - Anti-Repetition System v2.0

5-Layer Foolproof Anti-Repetition:
  1. Exact ID deduplication
  2. Real-time source daily cooldown (strips hourly suffix, blocks same telemetry source for full day)
  3. Source-type daily block (realtime_grid / realtime_climate once per day only)
  4. Fuzzy headline prefix match (last 7 posts)
  5. Semantic keyword fingerprint overlap (7-day rolling window, 60% overlap = block)
  BONUS: Pillar gap enforcement (same pillar needs 2-post gap)
"""

import os
import re
import json
import logging
from datetime import datetime, timezone, timedelta

log = logging.getLogger("ecopulse")

TOPIC_FINGERPRINT_WINDOW_DAYS = 7
SOURCE_TYPE_SAME_DAY_BLOCK = True
PILLAR_GAP_POSTS = 2
HEADLINE_SIMILARITY_WINDOW = 7


class MemoryEngine:
    def __init__(self, state_dir="state"):
        self.state_dir = state_dir
        self.log_path = os.path.join(state_dir, "posted_log.json")
        self.history = self._load_history()

    def _load_history(self):
        if os.path.exists(self.log_path):
            try:
                with open(self.log_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                log.error(f"Error loading posted history: {e}")
        return []

    def save_history(self, record, post_config=None):
        record["date"] = datetime.now(timezone.utc).isoformat()
        if post_config:
            record["hook_type"] = post_config.hook_type
            record["framing"] = post_config.framing
            record["body_structure"] = post_config.body_structure
            record["cta_type"] = post_config.cta_type
            record["image_style"] = post_config.image_style
            record["length_preset"] = post_config.length_preset
            record["turn_line"] = post_config.turn_line
            record["proof_fact"] = post_config.proof_fact
            record["pillar"] = getattr(post_config, "pillar", "")
            record["source_type"] = getattr(post_config, "source_type", "")
            record["topic_fingerprint"] = self._extract_fingerprint(
                record.get("headline", "") + " " + record.get("turn_line", "")
            )
        self.history.append(record)
        os.makedirs(self.state_dir, exist_ok=True)
        with open(self.log_path, "w", encoding="utf-8") as f:
            json.dump(self.history, f, indent=2)

    # Layer 1: Exact ID + daily realtime cooldown
    def is_duplicate(self, identifier):
        if not identifier:
            return False
        clean_id = identifier.strip().lower()
        normalized_id = self._normalize_realtime_id(clean_id)
        for entry in self.history:
            entry_id = (entry.get("id") or "").strip().lower()
            entry_norm = self._normalize_realtime_id(entry_id)
            if entry_id == clean_id:
                log.warning(f"BLOCK (exact ID): {clean_id}")
                return True
            if normalized_id and entry_norm == normalized_id:
                log.warning(f"BLOCK (daily realtime cooldown - same source posted today): {normalized_id}")
                return True
        return False

    def _normalize_realtime_id(self, id_str):
        """live_grid_carbon_2026_08_22_10 -> live_grid_carbon_2026_08_22"""
        import re as _re
        match = _re.match(r"(live_\w+_\d{4}_\d{2}_\d{2})(?:_\d+)?$", id_str)
        return match.group(1) if match else ""

    # Layer 2: Semantic fingerprint
    def _extract_fingerprint(self, text):
        import re as _re
        stopwords = {
            "the","a","an","and","or","of","in","to","for","is","are","at","by",
            "with","this","that","from","we","our","your","their","its","has",
            "have","been","it","on","as","up","but","not","can","do","be","will",
            "more","than","also","which","when","how","what","why","who","all"
        }
        words = _re.findall(r"[a-z]{4,}", text.lower())
        keywords = sorted(set(w for w in words if w not in stopwords))[:8]
        return "|".join(keywords)

    def is_topic_repeated(self, headline, turn_line=""):
        cutoff = (datetime.now(timezone.utc) - timedelta(days=TOPIC_FINGERPRINT_WINDOW_DAYS)).isoformat()
        recent = [e for e in self.history if e.get("date", "") >= cutoff]
        new_fp = self._extract_fingerprint(headline + " " + turn_line)
        new_words = set(new_fp.split("|"))
        if len(new_words) < 2:
            return False
        for entry in recent:
            existing_fp = entry.get("topic_fingerprint", "")
            if not existing_fp:
                existing_fp = self._extract_fingerprint(
                    (entry.get("headline") or "") + " " + (entry.get("turn_line") or "")
                )
            existing_words = set(existing_fp.split("|"))
            overlap = new_words & existing_words
            ratio = len(overlap) / max(len(new_words), 1)
            if ratio >= 0.6:
                log.warning(f"BLOCK (semantic {ratio:.0%} overlap): '{headline[:50]}' ~ recent post. Keys: {overlap}")
                return True
        return False

    # Layer 3: Source-type daily block
    def is_source_type_used_today(self, source_type):
        if not SOURCE_TYPE_SAME_DAY_BLOCK:
            return False
        if source_type not in {"realtime_grid", "realtime_climate"}:
            return False
        today = datetime.now(timezone.utc).date().isoformat()
        for entry in self.history:
            if (entry.get("date") or "")[:10] == today and entry.get("source_type") == source_type:
                log.warning(f"BLOCK (source_type daily): '{source_type}' already used today. Falling back to ArXiv.")
                return True
        return False

    # Layer 4: Headline prefix fuzzy match
    def is_headline_similar(self, headline, window=HEADLINE_SIMILARITY_WINDOW):
        if not headline or len(headline) < 15:
            return False
        prefix = headline.strip().lower()[:30]
        recent = self.history[-window:] if len(self.history) >= window else self.history
        for entry in recent:
            existing = (entry.get("headline") or "").strip().lower()
            if existing[:30] == prefix:
                log.warning(f"BLOCK (headline prefix): '{headline[:40]}'")
                return True
        return False

    # Layer 5: Pillar gap
    def is_pillar_too_recent(self, pillar):
        if not pillar:
            return False
        recent = self.history[-PILLAR_GAP_POSTS:] if len(self.history) >= PILLAR_GAP_POSTS else self.history
        for entry in recent:
            if (entry.get("pillar") or "").strip() == pillar.strip():
                log.warning(f"BLOCK (pillar gap): '{pillar[:40]}' in last {PILLAR_GAP_POSTS} posts")
                return True
        return False

    # Master gate
    def is_any_repetition(self, item, source_type=""):
        item_id = item.get("id", "")
        headline = item.get("title", "") or item.get("headline", "")
        pillar = item.get("pillar", "")

        if self.is_duplicate(item_id):
            return True
        if source_type and self.is_source_type_used_today(source_type):
            return True
        if self.is_headline_similar(headline):
            return True
        if self.is_pillar_too_recent(pillar):
            return True
        if self.is_topic_repeated(headline):
            return True
        return False
