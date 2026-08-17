import json
import logging

log = logging.getLogger("ecopulse")

class EditorialEngine:
    def __init__(self, gemini_client):
        self.llm = gemini_client

    def generate_thesis(self, raw_data: dict) -> dict:
        raw_text = raw_data.get("raw_text", "")
        source_name = raw_data.get("source", "Industry Insight")
        title = raw_data.get("title", "Untitled Story")
        
        if not raw_text:
            log.warning("No raw text provided to Editorial Engine.")
            return {}
            
        prompt = f"""You are a world-class technology journalist and viral LinkedIn strategist.
Analyze the following story and decide on the best angle, narrative structure, and visual asset to maximize executive engagement and discussion.

Source: {source_name}
Title: {title}
Context:
{raw_text[:4000]}

DECIDE ON THE FOLLOWING:
1. Archetype: Pick ONE of ['teardown', 'contrarian', 'deep_dive', 'narrative', 'cheat_sheet'] that best fits this story.
2. Category: A sharp 2-3 word uppercase label (e.g. 'INCIDENT ANALYSIS', 'AI BREAKTHROUGH', 'SYSTEMS DESIGN', 'SUSTAINABILITY PIVOT', 'DEV INSIGHT').
3. Headline: High-impact title for the visual slide (max 8 words).
4. Visual Layout: Pick ONE of ['hero_stat', 'comparison', 'three_pillars', 'terminal'] based on the story type:
   - 'terminal': for outages, bugs, code, CLI, or developer architecture stories.
   - 'hero_stat': for breakthrough metrics, massive efficiency leaps, or shocking numbers.
   - 'three_pillars': for multi-step breakdowns, key takeaways, or architectural pillars.
   - 'comparison': for before-vs-after, myth-vs-reality, or legacy-vs-nextgen.
5. Visual Theme: Pick ONE of ['emerald', 'cyan', 'violet', 'amber'].

Return ONLY valid JSON matching this schema:
{{
  "category": "CATEGORY STRING",
  "archetype": "teardown | contrarian | deep_dive | narrative | cheat_sheet",
  "headline": "Punchy 6-8 Word Headline",
  "core_insight": "2-sentence synthesis of why this matters to leaders and builders.",
  "visual": {{
    "layout": "hero_stat | comparison | three_pillars | terminal",
    "theme": "emerald | cyan | violet | amber",
    "badge": "BADGE TEXT (e.g. 'POST-MORTEM', 'AI RESEARCH', 'DEVOPS')",
    "subtitle": "SUBTITLE (e.g. 'INCIDENT ANALYSIS • AUG 2026')",
    "hero_stat": {{
      "big_number": "e.g. '3.5 Hrs' or '40% PUE' or '100x'",
      "label": "Short label for stat",
      "context": "1-sentence context for the number"
    }},
    "comparison": {{
      "left_label": "e.g. 'OFFICIAL STATUS' or 'LEGACY APPROACH'",
      "left_text": "e.g. 'Status green while queue was blocked'",
      "right_label": "e.g. 'ACTUAL USER REALITY' or 'ENGINEERING FIX'",
      "right_text": "e.g. 'Merge queue frozen across teams'"
    }},
    "three_pillars": [
      {{"tag": "01 ROOT CAUSE", "title": "Pillar 1 Title", "desc": "Pillar 1 brief description"}},
      {{"tag": "02 HIDDEN GAP", "title": "Pillar 2 Title", "desc": "Pillar 2 brief description"}},
      {{"tag": "03 THE LESSON", "title": "Pillar 3 Title", "desc": "Pillar 3 brief description"}}
    ],
    "terminal": {{
      "title": "bash — terminal",
      "command": "e.g. git push origin main",
      "output": "e.g. RPC failed: HTTP 504 gateway timeout",
      "note": "Key takeaway from the command/incident"
    }}
  }}
}}
"""

        try:
            res = self.llm.generate_text(prompt, temperature=0.5, json_mode=True)
            if res:
                return json.loads(res)
        except Exception as e:
            log.warning(f"Failed to generate dynamic thesis via LLM: {e}")
            
        return {
            "category": "ENGINEERING BRIEFING",
            "archetype": "teardown",
            "headline": title[:50],
            "core_insight": raw_text[:200],
            "visual": {
                "layout": "comparison",
                "theme": "emerald",
                "badge": "TECH BRIEFING",
                "subtitle": "SYSTEMS & ENGINEERING",
                "comparison": {
                    "left_label": "CONVENTIONAL ASSUMPTION",
                    "left_text": "Standard operational baseline",
                    "right_label": "ENGINEERING REALITY",
                    "right_text": "Observed friction and next-gen solution"
                }
            }
        }
