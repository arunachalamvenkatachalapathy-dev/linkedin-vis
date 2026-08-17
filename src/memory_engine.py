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

    def save_history(self, record: dict):
        record["date"] = datetime.now(timezone.utc).isoformat()
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
