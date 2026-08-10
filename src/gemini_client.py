import os
import requests
import json
import logging

log = logging.getLogger("ecopulse")

class GeminiClient:
    def __init__(self):
        self.api_key = os.environ.get("GEMINI_API_KEY", "").strip() or os.environ.get("GOOGLE_API_KEY", "").strip()
        if not self.api_key:
            log.warning("GEMINI_API_KEY is not set. API calls will fail.")

    def generate_text(self, prompt: str, temperature: float = 0.5, json_mode: bool = False) -> str:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.6-flash:generateContent?key={self.api_key}"
        headers = {"Content-Type": "application/json"}
        
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": temperature,
            }
        }
        
        if json_mode:
            payload["generationConfig"]["responseMimeType"] = "application/json"

        resp = requests.post(url, headers=headers, json=payload, timeout=30)
        resp.raise_for_status()
        
        data = resp.json()
        candidates = data.get("candidates", [])
        if candidates and "content" in candidates[0]:
            parts = candidates[0]["content"].get("parts", [])
            if parts:
                return parts[0].get("text", "")
        return ""

    def generate_image(self, prompt: str) -> bytes:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/imagen-3.0-generate-001:predict?key={self.api_key}"
        headers = {"Content-Type": "application/json"}
        payload = {
            "instances": [{"prompt": prompt}],
            "parameters": {"sampleCount": 1, "aspectRatio": "16:9"}
        }

        resp = requests.post(url, headers=headers, json=payload, timeout=90)
        resp.raise_for_status()
        
        predictions = resp.json().get("predictions", [])
        if predictions and "bytesBase64Encoded" in predictions[0]:
            import base64
            b64_str = predictions[0]["bytesBase64Encoded"]
            return base64.b64decode(b64_str)
        return b""
