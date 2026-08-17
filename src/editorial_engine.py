import json
import logging
from datetime import datetime

log = logging.getLogger("ecopulse")

class EditorialEngine:
    def __init__(self, gemini_client):
        self.llm = gemini_client

    def generate_thesis(self, raw_data: dict) -> dict:
        raw_text = raw_data.get("raw_text", "")
        source_name = raw_data.get("source", "Technical Insight")
        title = raw_data.get("title", "Systems Analysis")
        
        if not raw_text:
            log.warning("No raw text provided to Editorial Engine.")
            return {}
            
        prompt = f'''You are a top-tier Principal Engineer and Sustainability Strategist.
Distill this technical development into a purposeful, high-value, actionable insight that teaches readers a real principle or mental model.

DO NOT write sensational media reporting, outrage, or gossip.
Focus on: Why this matters, what the engineering principle is, and how professionals can apply it.

Source: {source_name}
Title: {title}
Context:
{raw_text[:4000]}

REQUIREMENTS:
1. card_type: Pick 'tweet' (for strong single-idea takeaways) or 'memo' (for 3-point tactical principles).
2. topic_tag: A short 1-2 word professional domain (e.g. 'Systems', 'CleanTech', 'ESG Telemetry', 'AI Infra', 'Architecture').
3. headline: Clean, professional title (max 7 words).
4. tweet_body: 2 to 3 crisp, purposeful sentences explaining the principle.
5. quote_box: A clean summary box with 'badge' (e.g. 'CORE PRINCIPLE' or 'METRIC'), 'source', 'title', and 'desc'.
6. memo_points: 2 to 3 practical bullet takeaways with 'label' and 'text'.
7. takeaway_box: 1-sentence golden rule.

Return ONLY valid JSON matching this schema:
{{
  "card_type": "tweet",
  "topic_tag": "Systems",
  "headline": "Telemetry Beats Estimation",
  "tweet_body": "Calculated estimates look clean on paper, but direct telemetry exposes the truth.\n\nWhether tracking datacenter thermal load or Scope 3 carbon intensity, audit-grade sensors change the entire engineering equation.",
  "quote_box": {{
    "badge": "KEY PRINCIPLE",
    "source": "Infrastructure Review",
    "title": "Hardware Telemetry > Top-Down Models",
    "desc": "Real-time sensor data uncovers 30%+ efficiency gaps invisible in spreadsheet models."
  }},
  "memo_points": [
    {{"label": "The Gap", "text": "Top-down estimates hide micro-inefficiencies and silent baseline drift."}},
    {{"label": "The Standard", "text": "Continuous telemetry provides verifiable, audit-ready operational data."}}
  ],
  "takeaway_box": "If you can't measure it with direct sensors, you can't reliably optimize it."
}}
'''

        try:
            res = self.llm.generate_text(prompt, temperature=0.5, json_mode=True)
            if res:
                return json.loads(res)
        except Exception as e:
            log.warning(f"Failed to generate purposeful thesis via LLM: {e}")
            
        return {
            "card_type": "tweet",
            "topic_tag": "Systems Design",
            "headline": title[:50],
            "tweet_body": f"The key engineering principle behind {title[:60]}:\n\nDirect hardware telemetry and audit-grade measurements always outperform unverified assumptions.",
            "quote_box": {
                "badge": "KEY PRINCIPLE",
                "source": source_name,
                "title": title[:40],
                "desc": raw_text[:120]
            },
            "memo_points": [
                {"label": "Observation", "text": raw_text[:100]},
                {"label": "Action", "text": "Prioritize direct operational telemetry over theoretical estimates."}
            ],
            "takeaway_box": "Direct telemetry and audit-ready data beat unverified assumptions every time."
        }
