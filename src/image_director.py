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
        img_prompt = thesis.get("image_generation_prompt", "")
        visual_type = thesis.get("visual_type", "realtime_telemetry")
        topic_tag = thesis.get("topic_tag", "REAL-TIME TELEMETRY")
        headline = thesis.get("headline", "Live Environmental Telemetry")
        left_caption = thesis.get("left_caption", "")
        right_caption = thesis.get("right_caption", "")
        takeaway_rule = thesis.get("takeaway_rule", "")
        flow_steps = thesis.get("flow_steps", [])
        baseline_stat = thesis.get("baseline_stat", "1.8L/kWh")
        target_stat = thesis.get("target_stat", "0.0L/kWh")
        
        # Telemetry metrics
        metric_1_label = thesis.get("metric_1_label", "LIVE GRID INTENSITY")
        metric_1_val = thesis.get("metric_1_val", "89 gCO2/kWh")
        metric_1_sub = thesis.get("metric_1_sub", "Actual live sensor intensity")
        metric_2_label = thesis.get("metric_2_label", "COAL GENERATION")
        metric_2_val = thesis.get("metric_2_val", "0.0%")
        metric_2_sub = thesis.get("metric_2_sub", "Zero thermal coal")
        metric_3_label = thesis.get("metric_3_label", "ATMOSPHERIC CO2")
        metric_3_val = thesis.get("metric_3_val", "427.8 ppm")
        metric_3_sub = thesis.get("metric_3_sub", "Global baseline")
        timestamp_str = datetime.utcnow().strftime("%d %b %Y · %H:%M UTC")

        # 1. Quick attempt on Gemini native image
        if self.llm and img_prompt:
            try:
                log.info(f"Checking Gemini Image API for: {headline}...")
                img_bytes = self.llm.generate_image(img_prompt, max_retries=1)
                if img_bytes:
                    os.makedirs(os.path.dirname(out_path) or '.', exist_ok=True)
                    with open(out_path, "wb") as f:
                        f.write(img_bytes)
                    log.info(f"✅ Generated native Gemini visual at {out_path} ({len(img_bytes)} bytes)")
                    return out_path
            except Exception as e:
                log.info(f"Gemini image generation unavailable, using dynamic visual card: {e}")

        # 2. Dynamic Playwright Visual Card
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
                visual_type=visual_type,
                topic_tag=topic_tag,
                headline=headline,
                left_caption=left_caption,
                right_caption=right_caption,
                takeaway_rule=takeaway_rule,
                flow_steps=flow_steps,
                baseline_stat=baseline_stat,
                target_stat=target_stat,
                metric_1_label=metric_1_label,
                metric_1_val=metric_1_val,
                metric_1_sub=metric_1_sub,
                metric_2_label=metric_2_label,
                metric_2_val=metric_2_val,
                metric_2_sub=metric_2_sub,
                metric_3_label=metric_3_label,
                metric_3_val=metric_3_val,
                metric_3_sub=metric_3_sub,
                timestamp_str=timestamp_str
            )

            os.makedirs(os.path.dirname(out_path) or '.', exist_ok=True)
            log.info(f"Rendering Dynamic Visual Card [{visual_type.upper()}]: {headline}")

            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page(
                    viewport={"width": 1200, "height": 675},
                    device_scale_factor=2
                )
                page.set_content(rendered_html, wait_until="domcontentloaded")
                page.screenshot(path=out_path, type="png")
                browser.close()

            log.info(f"✅ Generated dynamic visual at {out_path} ({os.path.getsize(out_path)} bytes)")
            return out_path

        except Exception as e:
            log.error(f"Visual rendering failed: {e}")

        return ""
