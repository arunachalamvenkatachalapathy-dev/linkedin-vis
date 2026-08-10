import os
import logging
from pathlib import Path

log = logging.getLogger("ecopulse")

class ImageDirector:
    def __init__(self, gemini_client):
        self.llm = gemini_client

    def generate_image(self, thesis: dict, out_path: str = "state/latest_slide.png") -> str:
        headline = thesis.get("headline", "")
        summary = thesis.get("summary", "")
        
        # Strictly documentary style, no stock graphics or AI art aesthetics.
        prompt = (
            f"A high-resolution, Reuters/Financial Times documentary-style photojournalism shot.\n"
            f"Subject: {headline}. Context: {summary}.\n"
            f"Style: Cinematic lighting, sharp focus on industrial or engineering elements, realistic, professional.\n"
            f"No floating icons, no clip-art, no 3D rendered charts, no text overlays, no blue gradient backgrounds."
        )

        log.info(f"Generating documentary image via Gemini Imagen 3: {prompt[:100]}...")
        
        try:
            img_bytes = self.llm.generate_image(prompt)
            if img_bytes:
                os.makedirs(os.path.dirname(out_path) or '.', exist_ok=True)
                with open(out_path, "wb") as f:
                    f.write(img_bytes)
                log.info(f"✅ Successfully saved Image Director output to {out_path}")
                return out_path
        except Exception as e:
            log.warning(f"Failed to generate image via Gemini API: {e}")
            
        return ""
