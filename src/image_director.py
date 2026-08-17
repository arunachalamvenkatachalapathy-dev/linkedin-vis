import os
import logging
from datetime import datetime
from jinja2 import Template

log = logging.getLogger("ecopulse")

class ImageDirector:
    def __init__(self, gemini_client=None):
        self.llm = gemini_client

    def generate_image(self, thesis: dict, out_path: str = "state/latest_image.png") -> str:
        """
        Renders a high-resolution, executive 1200x630 visual slide card using HTML/CSS & Playwright.
        """
        headline = thesis.get("headline", "Executive Compliance Briefing")
        metric_left = thesis.get("metric_left", "Baseline Benchmark: Legacy Practice")
        metric_right = thesis.get("metric_right", "Advanced Solution: Verified Telemetry")
        date_str = datetime.now().strftime("%B %Y")

        template_path = os.path.join(os.path.dirname(__file__), "templates", "slide.html")
        css_path = os.path.join(os.path.dirname(__file__), "templates", "styles.css")

        try:
            with open(template_path, "r", encoding="utf-8") as f:
                html_template = f.read()
            with open(css_path, "r", encoding="utf-8") as f:
                css_content = f.read()

            html_with_css = html_template.replace("/* INLINE_STYLES */", css_content)
            template = Template(html_with_css)
            rendered_html = template.render(
                headline=headline,
                metric_left=metric_left,
                metric_right=metric_right,
                date_str=date_str
            )

            os.makedirs(os.path.dirname(out_path) or '.', exist_ok=True)

            log.info(f"Rendering executive 1200x630 visual slide card via Playwright: {headline}")
            from playwright.sync_api import sync_playwright
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page(viewport={"width": 1200, "height": 630})
                page.set_content(rendered_html, wait_until="domcontentloaded")
                page.screenshot(path=out_path, type="png")
                browser.close()

            log.info(f"✅ Successfully generated visual slide at {out_path} ({os.path.getsize(out_path)} bytes)")
            return out_path

        except Exception as e:
            log.warning(f"Playwright slide generation failed: {e}. Attempting Imagen fallback...")

        if self.llm:
            try:
                img_bytes = self.llm.generate_image(f"Editorial infographic photo: {headline}")
                if img_bytes:
                    with open(out_path, "wb") as f:
                        f.write(img_bytes)
                    return out_path
            except Exception:
                pass

        return ""
