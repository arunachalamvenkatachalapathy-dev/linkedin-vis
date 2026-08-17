import json
import logging

log = logging.getLogger("ecopulse")

class EditorialEngine:
    def __init__(self, gemini_client):
        self.llm = gemini_client

    def generate_thesis(self, raw_data: dict) -> dict:
        if "headline" in raw_data and "metric_left" in raw_data:
            return raw_data
            
        raw_text = raw_data.get("raw_text", "")
        source_name = raw_data.get("source", "Technical Source")
        title = raw_data.get("title", "Untitled Topic")
        
        if not raw_text:
            log.warning("No raw text provided to Editorial Engine.")
            return {}
            
        prompt = (
            "You are a Senior Environmental & Systems Engineering Analyst.\n"
            f"Source: {source_name}\n"
            f"Title: {title}\n"
            f"Context:\n{raw_text[:3500]}\n\n"
            "Distill this information into an executive engineering thesis in valid JSON format with these exact keys:\n"
            "- 'headline': Executive title (maximum 8 words)\n"
            "- 'topic': Short keyword descriptor\n"
            "- 'metric_left': Baseline benchmark or legacy status quo metric\n"
            "- 'metric_right': Next-gen solution metric or breakthrough improvement\n"
            "- 'summary': 2-sentence crisp summary of the technical or operational pivot\n"
            "- 'source': Clean attribution string"
        )

        try:
            res = self.llm.generate_text(prompt, temperature=0.5, json_mode=True)
            if res:
                return json.loads(res)
        except Exception as e:
            log.warning(f"Failed to generate thesis via LLM: {e}")
            
        return {}
