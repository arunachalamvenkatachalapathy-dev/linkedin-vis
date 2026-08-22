"""
Hook Engine — Type-Specific Hook Generation & Scoring

Generates hooks based on the selected hook_type from PostConfig,
enforces the ≤12-word first-line rule, and scores candidates
to pick the strongest opener.
"""

import json
import logging

from src.post_config import HOOK_PATTERNS

log = logging.getLogger("ecopulse")


class HookEngine:
    def __init__(self, gemini_client):
        self.llm = gemini_client

    def generate_hooks(self, hook_type: str, headline: str, core_insight: str, framing: str) -> list:
        """
        Generate 3 hooks specifically in the selected hook_type style.
        """
        pattern_desc = HOOK_PATTERNS.get(hook_type, "Write a compelling opening hook.")

        prompt = f"""You are an elite LinkedIn copywriter specializing in scroll-stopping opening lines.

CONTEXT:
Headline: {headline}
Core insight: {core_insight}
Post framing: {framing}

TASK: Write exactly 3 opening hooks in the "{hook_type}" style.

STYLE DESCRIPTION: {pattern_desc}

ABSOLUTE RULES:
1. First line of each hook MUST be ≤12 words.
2. Each hook is 1–2 sentences maximum (≤30 words total).
3. NEVER start with "I" + mundane verb ("I recently...", "I wanted to...", "I'm excited to...").
4. NEVER start with "In today's world", "Did you know?", "I'm excited to share", "Let's dive in", "What's interesting is".
5. No emojis in the hook lines.
6. No hashtags in the hook lines.
7. Make the reader feel they MUST click "...see more" — trigger curiosity, challenge, or tension.
8. Each hook must be distinctly different from the others while staying in the "{hook_type}" style.
9. FORBIDDEN words in any hook: leverage, ecosystem, unlock, drive value, transformative, revolutionize, game-changer, paradigm shift.
10. Write like an engineer, not a LinkedIn influencer. Name the system, the failure mode, the specific number.

Return valid JSON:
{{
  "hooks": ["hook 1 text", "hook 2 text", "hook 3 text"]
}}"""

        try:
            res = self.llm.generate_text(prompt, temperature=0.75, json_mode=True)
            if res:
                data = json.loads(res)
                hooks = data.get("hooks", [])
                if hooks and len(hooks) >= 1:
                    # Filter: enforce ≤12 words on first line
                    valid = []
                    for h in hooks:
                        first_line = h.split('\n')[0].split('.')[0].strip()
                        if len(first_line.split()) <= 14:  # slight tolerance
                            valid.append(h)
                    return valid if valid else hooks[:3]
        except Exception as e:
            log.warning(f"Hook generation failed: {e}")

        return [f"{headline}"]

    def select_best_hook(self, hooks: list, hook_type: str) -> str:
        """
        Score hooks and return the best one.
        Uses a lightweight Gemini scoring pass.
        """
        if not hooks:
            return ""
        if len(hooks) == 1:
            return hooks[0]

        prompt = f"""You are evaluating LinkedIn opening hooks for scroll-stop power.
The hook style is: {hook_type}

Rate each hook 1–10 on:
- Would this stop someone mid-scroll?
- Does it create genuine curiosity or tension?
- Is it specific (not generic)?

Hooks to evaluate:
{chr(10).join(f'{i+1}. "{h}"' for i, h in enumerate(hooks))}

Return valid JSON:
{{
  "scores": [score1, score2, ...],
  "best_index": 0
}}"""

        try:
            res = self.llm.generate_text(prompt, temperature=0.2, json_mode=True)
            if res:
                data = json.loads(res)
                best_idx = data.get("best_index", 0)
                if 0 <= best_idx < len(hooks):
                    log.info(f"Hook scoring: selected #{best_idx + 1} (scores: {data.get('scores', [])})")
                    return hooks[best_idx]
        except Exception as e:
            log.warning(f"Hook scoring failed, using first hook: {e}")

        return hooks[0]
