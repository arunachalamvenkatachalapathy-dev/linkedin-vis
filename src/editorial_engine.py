import json
import logging

log = logging.getLogger("ecopulse")

class EditorialEngine:
    def __init__(self, gemini_client):
        self.llm = gemini_client

    def generate_thesis(self, raw_data: dict) -> dict:
        raw_text = raw_data.get("raw_text", "")
        source_name = raw_data.get("source", "Telemetry Stream")
        title = raw_data.get("title", "Real-Time Telemetry Analysis")
        theme = raw_data.get("theme", "ESG & CleanTech Telemetry")
        
        prompt = f"""You are a Lead AI Architect and Systems Auditor.
Analyze this real-world technical development and create an ultra-viral, smart, satirical "HUMAN vs ALIEN" dialogue meme.

Source: {source_name}
Title: {title}
Theme: {theme}
Context:
{raw_text[:4000]}

REQUIREMENTS:
1. topic_tag: Short 2-3 word technical badge (e.g. 'SCOPE 2 REALITY', 'AGENT PROD CRASH', 'GRID TELEMETRY').
2. headline: Punchy title naming the technology (max 7 words).
3. concrete_problem: 1 sentence on the problem.
4. technical_mechanism: 1 sentence on the solution.
5. hard_metric: 1 quantitative metric from the context.
6. takeaway_rule: 1-sentence golden rule for the bottom bar.
7. human_question: A satirical, slightly naive, or hypocritical question an Earthling Executive or Developer would ask (max 28 words). Make it funny, relatable, and authentic to tech/ESG industry tropes.
8. alien_answer: A calm, polite, but brutally factual, data-driven response from an Alien Systems Architect citing the real numbers and the real engineering fix (max 32 words).

Return ONLY valid JSON matching this schema:
{{
  "topic_tag": "REAL-TIME GRID TELEMETRY",
  "headline": "Live Grid Carbon Drops to 89 gCO2/kWh",
  "concrete_problem": "Static annual emission factors hide real-time clean windows.",
  "technical_mechanism": "Dynamic carbon-aware workload scheduling shifts batch compute to clean hours.",
  "hard_metric": "89 gCO2/kWh grid carbon intensity",
  "takeaway_rule": "Static emissions accounting is dead. Real-time telemetry is mandatory.",
  "human_question": "We bought 10,000 vintage tree offsets in 2012, so running our heavy GPU clusters at peak coal hours is 100% green... right?",
  "alien_answer": "Politely speaking, the grid emits 93 gCO2/kWh right now. Trees do not absorb midnight coal spikes. Dynamic workload scheduling does."
}}
"""

        try:
            res = self.llm.generate_text(prompt, temperature=0.5, json_mode=True)
            if res:
                parsed = json.loads(res)
                return parsed
        except Exception as e:
            log.warning(f"EditorialEngine JSON generation fallback: {e}")

        return {
            "topic_tag": "GALACTIC AUDIT",
            "headline": title[:50],
            "concrete_problem": f"Static estimations fail for {title[:40]}.",
            "technical_mechanism": "Dynamic telemetry provides verifiable ground truth.",
            "hard_metric": "93 gCO2/kWh grid carbon intensity",
            "takeaway_rule": "Real-time telemetry beats static models every single time.",
            "human_question": "If we just buy enough unverified offset credits, can we claim our 24/7 AI compute is net zero?",
            "alien_answer": "With all due respect, physics cannot be bribed. Your grid is burning coal. Schedule workloads when renewable energy actually peaks."
        }
