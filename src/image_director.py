import os
import logging

log = logging.getLogger("ecopulse")

class ImageDirector:
    def __init__(self, gemini_client):
        self.llm = gemini_client

    def generate_image(self, thesis: dict, out_path: str = "state/latest_image.png") -> str:
        headline = thesis.get("headline", "")
        summary = thesis.get("summary", "")
        
        prompt = (
            f"A high-resolution, Reuters/Financial Times documentary-style photojournalism shot.\n"
            f"Subject: {headline}. Context: {summary}.\n"
            f"Style: Cinematic lighting, sharp focus on industrial, technological, or environmental elements, realistic, professional.\n"
            f"No floating icons, no clip-art, no 3D cartoon charts, no text overlays."
        )

        log.info(f"Generating documentary visual via Gemini Imagen 3: {headline}...")
        try:
            img_bytes = self.llm.generate_image(prompt)
            if img_bytes:
                os.makedirs(os.path.dirname(out_path) or '.', exist_ok=True)
                with open(out_path, "wb") as f:
                    f.write(img_bytes)
                log.info(f"✅ Successfully saved visual to {out_path}")
                return out_path
        except Exception as e:
            log.warning(f"Image generation skipped/failed: {e}")
            
        return ""
