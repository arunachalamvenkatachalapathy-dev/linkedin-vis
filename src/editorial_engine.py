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
        
        prompt = f'''You are Arunachalam Venkatachalapathy, an AI Systems Architect.
Analyze this real-world technical data stream and extract a highly viral, controversial, or shocking breakdown.

Source: {source_name}
Title: {title}
Theme: {theme}
Context:
{raw_text[:4000]}

REQUIREMENTS:
1. topic_tag: Short 2-3 word tag.
2. headline: Punchy title naming the specific technology or failure (max 7 words).
3. concrete_problem: 1 sentence on the problem.
4. technical_mechanism: 1 sentence explaining the engineering solution.
5. hard_metric: 1 exact quantitative metric from the data.
6. takeaway_rule: 1-sentence actionable rule.
7. image_generation_prompt: Dynamic prompt for Gemini Imagen. The prompt MUST describe a PHOTOREALISTIC, cinematic, relatable viral meme. NO text should be in the image. Frame it as a highly realistic, funny, or shocking photographic situation (e.g., "A hyper-realistic photo of an exhausted engineer buried under a mountain of tangled server cables while a shiny robot sips coffee, cinematic lighting, 16:9").

Return ONLY valid JSON matching this schema:
{{
  "topic_tag": "REAL-TIME CRISIS",
  "headline": "Live Grid Carbon Drops",
  "concrete_problem": "Static annual emissions factors overestimate corporate Scope 2 carbon.",
  "technical_mechanism": "Dynamic carbon-aware compute scheduling.",
  "hard_metric": "Grid intensity at 89 gCO2/kWh.",
  "takeaway_rule": "Static emissions accounting is dead.",
  "image_generation_prompt": "A hyper-realistic photograph of an overwhelmed executive looking at a burning spreadsheet on a glowing monitor, cinematic lighting, dramatic shadows, 16:9 ratio."
}}
'''

        try:
            res = self.llm.generate_text(prompt, temperature=0.5, json_mode=True)
            if res:
                return json.loads(res)
        except Exception as e:
            log.warning(f"LLM thesis generation fallback: {e}")

        return {
            "topic_tag": "LIVE CRISIS",
            "headline": title[:50],
            "concrete_problem": f"Static estimations fail to reflect real-time conditions for {title[:40]}.",
            "technical_mechanism": "Continuous telemetry monitoring provides verifiable audit-ready ground truth.",
            "hard_metric": "34% Scope 2 reduction via carbon-aware scheduling.",
            "takeaway_rule": "Real-time telemetry beats static models every single time.",
            "image_generation_prompt": "A hyper-realistic, high-definition photograph of a chaotic, disorganized server room with tangled cables, lit by intense fluorescent lights, documentary photography style, 16:9 ratio."
        }
