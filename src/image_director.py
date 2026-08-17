import os
import logging
import random
from datetime import datetime
from jinja2 import Template
from playwright.sync_api import sync_playwright

log = logging.getLogger("ecopulse")

class ImageDirector:
    def __init__(self, gemini_client=None):
        self.llm = gemini_client

    def generate_image(self, thesis: dict, out_path: str = "state/latest_image.png") -> str:
        """
        Renders an ultra-clean, realistic Tweet / X or Apple Notes Screenshot Card.
        """
        card_type = thesis.get("card_type", "tweet")
        topic_tag = thesis.get("topic_tag", "Engineering")
        headline = thesis.get("headline", "Systems Analysis")
        tweet_body = thesis.get("tweet_body", "")
        quote_box = thesis.get("quote_box", None)
        memo_points = thesis.get("memo_points", [])
        takeaway_box = thesis.get("takeaway_box", "")

        # Randomize views & engagement metrics for authentic realism
        views_k = random.randint(85, 320)
        likes_k = f"{random.randint(1, 4)}.{random.randint(1, 9)}K"
        retweets = random.randint(80, 420)
        comments = random.randint(30, 150)
        bookmarks = random.randint(120, 650)
        now = datetime.now()
        timestamp_str = f"{now.strftime('%I:%M %p')} · {now.strftime('%b %d, %Y')}"

        template_path = os.path.join(os.path.dirname(__file__), "templates", "social_screenshot.html")
        css_path = os.path.join(os.path.dirname(__file__), "templates", "social_screenshot.css")

        try:
            with open(template_path, "r", encoding="utf-8") as f:
                html_template = f.read()
            with open(css_path, "r", encoding="utf-8") as f:
                css_content = f.read()

            html_with_css = html_template.replace("/* INLINE_STYLES */", css_content)
            template = Template(html_with_css)
            rendered_html = template.render(
                card_type=card_type,
                author_name="Arunachalam Venkatachalapathy",
                author_handle="arunachalamvenv",
                author_initials="AV",
                topic_tag=topic_tag,
                headline=headline,
                tweet_body=tweet_body.replace('\n', '<br>'),
                quote_box=quote_box,
                memo_points=memo_points,
                takeaway_box=takeaway_box,
                timestamp_str=timestamp_str,
                views_count=f"{views_k}.4K",
                likes_count=likes_k,
                retweets_count=str(retweets),
                comments_count=str(comments),
                bookmarks_count=str(bookmarks)
            )

            os.makedirs(os.path.dirname(out_path) or '.', exist_ok=True)

            log.info(f"Rendering Social Screenshot Card [{card_type.upper()}]: {headline}")
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page(
                    viewport={"width": 1200, "height": 675},
                    device_scale_factor=2  # High-DPI Retina sharpness
                )
                page.set_content(rendered_html, wait_until="domcontentloaded")
                page.screenshot(path=out_path, type="png")
                browser.close()

            log.info(f"✅ Successfully generated realistic screenshot card at {out_path} ({os.path.getsize(out_path)} bytes)")
            return out_path

        except Exception as e:
            log.warning(f"Screenshot card generation failed: {e}")

        return ""
