import os
import logging
from datetime import datetime

log = logging.getLogger("ecopulse")

class ImageDirector:
    def __init__(self, gemini_client=None):
        self.llm = gemini_client

    def generate_image(self, thesis: dict, out_path: str = "state/latest_image.png") -> str:
        headline = thesis.get("headline", "")
        core_insight = thesis.get("core_insight", "")
        category = thesis.get("category", "TECH")

        image_prompt = (
            f"A high-resolution, photorealistic documentary photograph illustrating: {headline}. "
            f"Context: {core_insight}. "
            f"Style: Authentic natural lighting, professional Reuters/Financial Times editorial photography, sharp focus, natural color grading, 16:9 widescreen composition. "
            f"Strictly NO neon glows, NO dark cyber aesthetics, NO floating generic 3D icons, NO cartoon graphics, NO text overlays."
        )

        log.info(f"Requesting authentic Gemini AI image: {headline}...")
        
        if self.llm:
            try:
                img_bytes = self.llm.generate_image(image_prompt)
                if img_bytes:
                    os.makedirs(os.path.dirname(out_path) or '.', exist_ok=True)
                    with open(out_path, "wb") as f:
                        f.write(img_bytes)
                    log.info(f"✅ Successfully saved authentic Gemini AI image to {out_path} ({len(img_bytes)} bytes)")
                    return out_path
            except Exception as e:
                log.warning(f"Gemini image generation attempt failed: {e}")

        # Fallback to a clean editorial visual if quota is temporarily capped
        try:
            template_path = os.path.join(os.path.dirname(__file__), "templates", "dynamic_slide.html")
            css_path = os.path.join(os.path.dirname(__file__), "templates", "dynamic_styles.css")

            if os.path.exists(template_path) and os.path.exists(css_path):
                from jinja2 import Template
                from playwright.sync_api import sync_playwright

                with open(template_path, "r", encoding="utf-8") as f:
                    html_template = f.read()
                with open(css_path, "r", encoding="utf-8") as f:
                    css_content = f.read()

                html_with_css = html_template.replace("/* INLINE_STYLES */", css_content)
                template = Template(html_with_css)
                rendered_html = template.render(
                    layout="three_pillars",
                    theme="cyan",
                    badge=category,
                    subtitle="EXECUTIVE BRIEFING",
                    headline=headline,
                    three_pillars=[
                        {"tag": "01 OVERVIEW", "title": "Core Context", "desc": core_insight[:120]},
                        {"tag": "02 IMPLICATION", "title": "Operational Reality", "desc": "Strategic shifts require audit-verified telemetry."},
                        {"tag": "03 TAKEAWAY", "title": "Next Step", "desc": "Evaluate direct systems telemetry this quarter."}
                    ],
                    footer_left=category,
                    date_str=datetime.now().strftime("%B %Y")
                )

                os.makedirs(os.path.dirname(out_path) or '.', exist_ok=True)
                with sync_playwright() as p:
                    browser = p.chromium.launch(headless=True)
                    page = browser.new_page(viewport={"width": 1200, "height": 630})
                    page.set_content(rendered_html, wait_until="domcontentloaded")
                    page.screenshot(path=out_path, type="png")
                    browser.close()

                log.info(f"✅ Saved clean fallback visual to {out_path}")
                return out_path
        except Exception as e:
            log.warning(f"Fallback visual generation skipped: {e}")

        return ""
