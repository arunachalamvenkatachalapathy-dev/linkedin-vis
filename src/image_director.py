import os
import logging
from datetime import datetime

log = logging.getLogger("ecopulse")

class ImageDirector:
    def __init__(self, gemini_client=None):
        self.llm = gemini_client

    def generate_image(self, thesis: dict, out_path: str = "state/latest_image.png") -> str:
        img_prompt = thesis.get("image_generation_prompt", "")
        
        # Native Image Generation
        if self.llm and img_prompt:
            try:
                log.info(f"Generating photorealistic meme via Gemini Image API...")
                img_bytes = self.llm.generate_image(img_prompt, max_retries=2)
                if img_bytes:
                    os.makedirs(os.path.dirname(out_path) or '.', exist_ok=True)
                    with open(out_path, "wb") as f:
                        f.write(img_bytes)
                    log.info(f"✅ Generated photorealistic visual at {out_path} ({len(img_bytes)} bytes)")
                    return out_path
            except Exception as e:
                log.error(f"Gemini image generation failed: {e}")

        log.warning("No image generated (API limit or missing prompt). Playwright fallback is disabled.")
        return ""
