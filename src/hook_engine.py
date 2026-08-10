import json
import logging

log = logging.getLogger("ecopulse")

class HookEngine:
    def __init__(self, gemini_client):
        self.llm = gemini_client

    def generate_hooks(self, thesis: dict) -> list:
        prompt = (
            f"Topic: {thesis.get('headline')}\n"
            f"Context: {thesis.get('summary')}\n\n"
            f"Generate 3 distinct, compelling 1-2 sentence hooks for a LinkedIn post.\n"
            f"Rules:\n"
            f"1. Start directly with a surprising metric, a technical friction point, or a stark contrast.\n"
            f"2. NEVER use generic openings like 'In today's world', 'Everyone is talking about', 'Did you know?'.\n"
            f"3. Do not use hashtags or emojis.\n\n"
            f"Return valid JSON with a key 'hooks' containing a list of 3 strings."
        )

        try:
            res = self.llm.generate_text(prompt, json_mode=True)
            if res:
                data = json.loads(res)
                return data.get("hooks", [])
        except Exception as e:
            log.warning(f"Failed to generate hooks: {e}")
            
        return []

    def select_best_hook(self, hooks: list) -> str:
        # For simplicity, returning the first hook or picking randomly.
        # Can be expanded to use LLM scoring if needed.
        if hooks:
            return hooks[0]
        return ""
