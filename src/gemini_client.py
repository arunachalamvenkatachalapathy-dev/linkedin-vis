import os
import time
import json
import logging
import base64
import requests

log = logging.getLogger("ecopulse")

TEXT_MODELS = [
    "gemini-3.5-flash",
    "gemini-3.7-flash",
    "gemini-flash-latest"
]

IMAGE_MODELS = [
    "gemini-2.5-flash-image",
    "gemini-3.1-flash-image",
    "gemini-3-pro-image"
]

class GeminiClient:
    def __init__(self):
        self.api_key = (
            os.environ.get("GEMINI_API_KEY", "").strip() or 
            os.environ.get("GOOGLE_API_KEY", "").strip()
        )
        if not self.api_key:
            log.warning("GEMINI_API_KEY is not set. LLM API calls will fail.")

    def generate_text(self, prompt: str, temperature: float = 0.6, json_mode: bool = False, max_retries: int = 5) -> str:
        if not self.api_key:
            log.error("Cannot generate text: GEMINI_API_KEY is missing.")
            return ""

        last_error = None
        for model in TEXT_MODELS:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={self.api_key}"
            headers = {"Content-Type": "application/json"}
            
            payload = {
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {
                    "temperature": temperature,
                }
            }
            if json_mode:
                payload["generationConfig"]["responseMimeType"] = "application/json"

            for attempt in range(1, max_retries + 1):
                try:
                    resp = requests.post(url, headers=headers, json=payload, timeout=30)
                    if resp.status_code == 200:
                        data = resp.json()
                        candidates = data.get("candidates", [])
                        if candidates and "content" in candidates[0]:
                            parts = candidates[0]["content"].get("parts", [])
                            if parts:
                                return parts[0].get("text", "").strip()
                        return ""
                    
                    if resp.status_code in [429, 500, 502, 503, 504]:
                        import random
                        wait_time = min(60, 5 * (2.0 ** (attempt - 1))) + random.uniform(1, 5)
                        log.warning(f"Model {model} HTTP {resp.status_code}. Retrying in {wait_time:.1f}s (attempt {attempt}/{max_retries})...")
                        time.sleep(wait_time)
                        continue
                    
                    log.warning(f"Model {model} returned HTTP {resp.status_code}. Switching model...")
                    break

                except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
                    import random
                    wait_time = min(60, 5 * (2.0 ** (attempt - 1))) + random.uniform(1, 5)
                    log.warning(f"Timeout/Connection error on {model}: {e}. Retrying in {wait_time:.1f}s...")
                    time.sleep(wait_time)
                    last_error = e
                except Exception as e:
                    log.warning(f"Error on {model}: {e}")
                    last_error = e
                    break

        log.error(f"All Gemini models failed. Last error: {last_error}")
        return ""

    def generate_image(self, prompt: str, max_retries: int = 2) -> bytes:
        if not self.api_key:
            return b""

        for model in IMAGE_MODELS:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={self.api_key}"
            headers = {"Content-Type": "application/json"}
            payload = {
                "contents": [{
                    "parts": [{"text": prompt}]
                }],
                "generationConfig": {
                    "responseModalities": ["IMAGE"]
                }
            }

            for attempt in range(1, max_retries + 1):
                try:
                    resp = requests.post(url, headers=headers, json=payload, timeout=45)
                    if resp.status_code == 200:
                        data = resp.json()
                        candidates = data.get("candidates", [])
                        if candidates:
                            parts = candidates[0].get("content", {}).get("parts", [])
                            for p in parts:
                                if "inlineData" in p:
                                    b64_str = p["inlineData"].get("data", "")
                                    if b64_str:
                                        log.info(f"✅ Generated native image via Gemini {model}")
                                        return base64.b64decode(b64_str)
                    elif resp.status_code in [429, 503]:
                        log.warning(f"Gemini image model {model} returned HTTP {resp.status_code} (attempt {attempt}). Retrying...")
                        time.sleep(attempt * 2)
                    else:
                        log.warning(f"Gemini image model {model} returned HTTP {resp.status_code}")
                        break
                except Exception as e:
                    log.warning(f"Gemini image attempt on {model} failed: {e}")
                    time.sleep(2)

        return b""
