import json
import logging

log = logging.getLogger("ecopulse")

class EditorialEngine:
    def __init__(self, gemini_client):
        self.llm = gemini_client

    def generate_thesis(self, raw_data: dict) -> dict:
        """Distills raw transcript or fallback data into a structured thesis."""
        # If it's already structured from fallback
        if "headline" in raw_data and "metric_left" in raw_data:
            return raw_data
            
        raw_text = raw_data.get("raw_text", "")
        source_name = raw_data.get("source", "Unknown Source")
        title = raw_data.get("title", "Untitled")
        
        if not raw_text:
            log.warning("No raw text provided to Editorial Engine.")
            return {}
            
        prompt = (
            f"You are a Senior Environmental Engineering Analyst. Read the following YouTube video transcript and distill it into a structured technical thesis.\n"
            f"DO NOT invent or predict facts. ONLY extract real, hard facts, numerical metrics, and operational realities actually spoken in this transcript.\n\n"
            f"Video Title: {title}\n"
            f"Transcript (Truncated): {raw_text}\n\n"
            f"Return valid JSON with keys:\n"
            f"- 'headline': Executive title (max 8 words)\n"
            f"- 'topic': Short topic key\n"
            f"- 'metric_left': Baseline metric found in the transcript (e.g. 'Legacy Method: 22% Efficiency')\n"
            f"- 'metric_right': Advanced metric found in the transcript (e.g. 'New Technology: 33.9% Efficiency')\n"
            f"- 'summary': 2-sentence technical summary of the core engineering pivot spoken in the video.\n"
            f"- 'source': 'YouTube Transcript: {title}'"
        )

        try:
            res = self.llm.generate_text(prompt, json_mode=True)
            if res:
                return json.loads(res)
        except Exception as e:
            log.warning(f"Failed to generate thesis: {e}")
            
        return {}
