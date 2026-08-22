"""
Memory Engine — State Management & History Tracking

Manages state/posted_log.json to track published posts and prevent duplicates.
Extended to persist PostConfig fields (hook_type, framing, body_structure, etc.)
alongside existing fields to enable variety analysis.
"""

import os
import json
import logging
from datetime import datetime, timezone

log = logging.getLogger("ecopulse")


class MemoryEngine:
    def __init__(self, state_dir: str = "state"):
        self.state_dir = state_dir
        self.log_path = os.path.join(state_dir, "posted_log.json")
        self.history = self._load_history()

    def _load_history(self) -> list:
        if os.path.exists(self.log_path):
            try:
                with open(self.log_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                log.error(f"Error loading posted history: {e}")
        return []

    def save_history(self, record: dict, post_config=None):
        """
        Save a post record to history.
        If post_config is provided, its component selections are merged into the record.
        """
        record["date"] = datetime.now(timezone.utc).isoformat()

        # Merge PostConfig fields if available
        if post_config:
            record["hook_type"] = post_config.hook_type
            record["framing"] = post_config.framing
            record["body_structure"] = post_config.body_structure
            record["cta_type"] = post_config.cta_type
            record["image_style"] = post_config.image_style
            record["length_preset"] = post_config.length_preset
            record["turn_line"] = post_config.turn_line
            record["proof_fact"] = post_config.proof_fact

        self.history.append(record)
        os.makedirs(self.state_dir, exist_ok=True)
        with open(self.log_path, "w", encoding="utf-8") as f:
            json.dump(self.history, f, indent=2)

    def is_duplicate(self, identifier: str) -> bool:
        if not identifier:
            return False
        clean_id = identifier.strip().lower()
        for entry in self.history:
            if (entry.get("id") or "").strip().lower() == clean_id:
                return True
            if (entry.get("topic") or "").strip().lower() == clean_id:
                return True
            if (entry.get("headline") or "").strip().lower() == clean_id:
                return True
        return False
