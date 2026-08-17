import json
import logging

log = logging.getLogger("ecopulse")

class HookEngine:
    def __init__(self, gemini_client):
        self.llm = gemini_client

    def generate_hooks(self, thesis: dict) -> list:
        prompt = (
            f"Headline: {thesis.get('headline')}\n"
            f"Context: {thesis.get('summary')}\n"
            f"Baseline: {thesis.get('metric_left')}\n"
            f"Solution: {thesis.get('metric_right')}\n\n"
            "Generate 3 distinct, high-impact 1-2 sentence LinkedIn opening hooks.\n"
            "Rules:\n"
            "1. Start directly with a shocking metric, friction point, or engineering contrast.\n"
            "2. NEVER use generic clichés like 'In today's world', 'Everyone is talking about', 'Did you know?'.\n"
            "3. No hashtags or emojis in the hook.\n"
            "Return valid JSON with key 'hooks' containing a list of 3 strings."
        )

        try:
            res = self.llm.generate_text(prompt, temperature=0.7, json_mode=True)
            if res:
                data = json.loads(res)
                return data.get("hooks", [])
        except Exception as e:
            log.warning(f"Failed to generate hooks via LLM: {e}")
            
        return [f"{thesis.get('headline', '')}: {thesis.get('summary', '')}"]

    def select_best_hook(self, hooks: list) -> str:
        if hooks:
            return hooks[0]
        return ""
