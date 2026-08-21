import os
import logging
from jinja2 import Template
from playwright.sync_api import sync_playwright

log = logging.getLogger("ecopulse")

class ImageDirector:
    def __init__(self, gemini_client=None):
        self.llm = gemini_client

    def generate_image(self, thesis: dict, out_path: str = "state/latest_image.png") -> str:
        """
        Renders a large-text, high-contrast Human vs Alien satirical dialogue meme infographic.
        """
        topic_tag = thesis.get("topic_tag", "GALACTIC AUDIT REPORT")
        human_question = thesis.get("human_question", "Can we just claim net-zero with static estimates?")
        alien_answer = thesis.get("alien_answer", "Politely speaking, physics does not accept static estimates. Real-time telemetry is mandatory.")
        takeaway_rule = thesis.get("takeaway_rule", "Static accounting is dead. Real-time telemetry is mandatory.")

        try:
            template_path = os.path.join(os.path.dirname(__file__), "templates", "meme_board.html")
            css_path = os.path.join(os.path.dirname(__file__), "templates", "meme_board.css")

            with open(template_path, "r", encoding="utf-8") as f:
                html_template = f.read()
            with open(css_path, "r", encoding="utf-8") as f:
                css_content = f.read()

            html_with_css = html_template.replace("/* INLINE_STYLES */", css_content)
            template = Template(html_with_css)
            rendered_html = template.render(
                topic_tag=topic_tag,
                human_question=human_question,
                alien_answer=alien_answer,
                takeaway_rule=takeaway_rule
            )

            os.makedirs(os.path.dirname(out_path) or '.', exist_ok=True)
            log.info(f"👽 Rendering Large-Text Alien vs Human Meme Infographic: {topic_tag}")

            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page(
                    viewport={"width": 1200, "height": 675},
                    device_scale_factor=2
                )
                page.set_content(rendered_html, wait_until="domcontentloaded")
                page.screenshot(path=out_path, type="png")
                browser.close()

            log.info(f"✅ Generated Alien Meme Infographic at {out_path} ({os.path.getsize(out_path)} bytes)")
            return out_path

        except Exception as e:
            log.error(f"Alien meme infographic rendering failed: {e}")

        return ""
