import os
import logging
import urllib.request
import urllib.parse
import time
from datetime import datetime

log = logging.getLogger("ecopulse")

class ImageDirector:
    def __init__(self, gemini_client=None):
        self.llm = gemini_client

    def generate_image(self, thesis: dict, out_path: str = "state/latest_image.png") -> str:
        img_prompt = thesis.get("image_generation_prompt", "")
        if not img_prompt:
            headline = thesis.get("headline", "AI Systems Architecture")
            img_prompt = f"A photorealistic, cinematic documentary photo of a software engineer in an industrial server room, dramatic lighting, high detail, 16:9, regarding {headline}"

        os.makedirs(os.path.dirname(out_path) or '.', exist_ok=True)

        # 1. Primary: High-Resolution Photorealistic AI Image via Pollinations AI (Flux Model)
        encoded_prompt = urllib.parse.quote(img_prompt.replace("\n", " ").strip())
        try:
            log.info(f"🎨 Generating photorealistic viral visual via Flux Engine...")
            seed = int(time.time())
            url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=1200&height=675&model=flux&seed={seed}&nologo=true"
            
            req = urllib.request.Request(url, headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            })
            with urllib.request.urlopen(req, timeout=45) as resp:
                img_bytes = resp.read()
                if len(img_bytes) > 5000:
                    with open(out_path, "wb") as f:
                        f.write(img_bytes)
                    log.info(f"✅ Generated photorealistic Flux visual at {out_path} ({len(img_bytes)} bytes)")
                    return out_path
        except Exception as e:
            log.warning(f"Pollinations Flux generation failed: {e}. Trying Turbo model fallback...")

        # 2. Secondary: Pollinations Turbo fallback
        try:
            url_turbo = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=1200&height=675&model=turbo&nologo=true"
            req = urllib.request.Request(url_turbo, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=30) as resp:
                img_bytes = resp.read()
                if len(img_bytes) > 5000:
                    with open(out_path, "wb") as f:
                        f.write(img_bytes)
                    log.info(f"✅ Generated Turbo visual at {out_path} ({len(img_bytes)} bytes)")
                    return out_path
        except Exception as e:
            log.warning(f"Pollinations Turbo fallback failed: {e}")

        # 3. Tertiary: Gemini Native Image API
        if self.llm:
            try:
                log.info("Trying Gemini native image model...")
                img_bytes = self.llm.generate_image(img_prompt, max_retries=1)
                if img_bytes and len(img_bytes) > 5000:
                    with open(out_path, "wb") as f:
                        f.write(img_bytes)
                    log.info(f"✅ Generated Gemini visual at {out_path} ({len(img_bytes)} bytes)")
                    return out_path
            except Exception as e:
                log.warning(f"Gemini image generation skipped: {e}")

        log.error("All image generation strategies failed.")
        return ""
