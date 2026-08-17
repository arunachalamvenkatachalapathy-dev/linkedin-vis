import json
import logging

log = logging.getLogger("ecopulse")

class HookEngine:
    def __init__(self, gemini_client):
        self.llm = gemini_client

    def generate_hooks(self, thesis: dict) -> list:
        archetype = thesis.get("archetype", "deep_dive")
        headline = thesis.get("headline", "")
        core_insight = thesis.get("core_insight", "")

        prompt = f"""You are an elite LinkedIn copywriter.
Write 3 viral, high-CTR opening hooks for a post about:
Headline: {headline}
Archetype: {archetype}
Core Insight: {core_insight}

HOOK RULES:
1. Must be 1 to 2 punchy sentences (maximum 30 words).
2. It will appear before the LinkedIn '...see more' fold, so it MUST trigger irresistible curiosity, challenge common wisdom, or present high-stakes tension.
3. Tailor the hook to the archetype:
   - 'teardown': Focus on an unexpected failure, hidden blind spot, or outage.
   - 'contrarian': Challenge a widely accepted best practice or myth.
   - 'deep_dive': Reveal a non-obvious technical breakthrough or mechanism.
   - 'narrative': Start in the middle of a high-friction decision or discovery.
   - 'cheat_sheet': Promise a concise, high-density tactical breakdown.
4. NEVER start with 'In today's world', 'Did you know?', or 'I'm excited to share'.
5. No emojis or hashtags in the hook lines.

Return valid JSON with key 'hooks' containing a list of 3 distinct hook strings.
"""

        try:
            res = self.llm.generate_text(prompt, temperature=0.7, json_mode=True)
            if res:
                data = json.loads(res)
                hooks = data.get("hooks", [])
                if hooks:
                    return hooks
        except Exception as e:
            log.warning(f"Hook generation failed: {e}")
            
        return [f"{headline}: {core_insight}"]

    def select_best_hook(self, hooks: list) -> str:
        if hooks:
            return hooks[0]
        return ""
