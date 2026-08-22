import os
import logging
from datetime import datetime
from jinja2 import Template
from playwright.sync_api import sync_playwright

log = logging.getLogger("ecopulse")

class ImageDirector:
    def __init__(self, gemini_client=None):
        self.llm = gemini_client

    def generate_image(self, thesis: dict, out_path: str = "state/latest_image.png") -> str:
        """
        Renders a dynamic, pattern-breaking visual based on the chosen visual_type.
        """
        visual_type = thesis.get("visual_type", "alien_qa")
        topic_tag = thesis.get("topic_tag", "GALACTIC AUDIT REPORT")
        headline = thesis.get("headline", "Production System Architecture")
        takeaway_rule = thesis.get("takeaway_rule", "Static accounting is dead. Real-time telemetry is mandatory.")
        
        # Dialogue fields
        human_question = thesis.get("human_question", "Can we just claim net-zero with static estimates?")
        alien_answer = thesis.get("alien_answer", "Politely speaking, physics does not accept static estimates. Real-time telemetry is mandatory.")
        
        # Telemetry fields
        metric_1_label = thesis.get("metric_1_label", "LIVE GRID INTENSITY")
        metric_1_val = thesis.get("metric_1_val", "93 gCO2/kWh")
        metric_1_sub = thesis.get("metric_1_sub", "Actual live sensor intensity")
        metric_2_label = thesis.get("metric_2_label", "CLEAN ENERGY SHARE")
        metric_2_val = thesis.get("metric_2_val", "63.0%")
        metric_2_sub = thesis.get("metric_2_sub", "Renewables + Nuclear")
        metric_3_label = thesis.get("metric_3_label", "ATMOSPHERIC CO2")
        metric_3_val = thesis.get("metric_3_val", "427.8 ppm")
        metric_3_sub = thesis.get("metric_3_sub", "NOAA Global Baseline")
        timestamp_str = datetime.utcnow().strftime("%d %b %Y · %H:%M UTC")

        # Whiteboard & Code fields
        flow_steps = thesis.get("flow_steps", [])
        left_caption = thesis.get("left_caption", "")
        right_caption = thesis.get("right_caption", "")
        baseline_stat = thesis.get("baseline_stat", "210 gCO2/kWh Flat")
        target_stat = thesis.get("target_stat", "93 gCO2/kWh Live")

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
                takeaway_rule=takeaway_rule,
                human_question=human_question,
                alien_answer=alien_answer,
                metric_1_label=metric_1_label,
                metric_1_val=metric_1_val,
                metric_1_sub=metric_1_sub,
                metric_2_label=metric_2_label,
                metric_2_val=metric_2_val,
                metric_2_sub=metric_2_sub,
                metric_3_label=metric_3_label,
                metric_3_val=metric_3_val,
                metric_3_sub=metric_3_sub,
                timestamp_str=timestamp_str,
                flow_steps=flow_steps,
                left_caption=left_caption,
                right_caption=right_caption,
                baseline_stat=baseline_stat,
                target_stat=target_stat
            )

            os.makedirs(os.path.dirname(out_path) or '.', exist_ok=True)
            log.info(f"🎨 Rendering Dynamic Visual [{visual_type.upper()}]: {headline}")

            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page(
                    viewport={"width": 1200, "height": 675},
                    device_scale_factor=2
                )
                page.set_content(rendered_html, wait_until="domcontentloaded")
                page.screenshot(path=out_path, type="png")
                browser.close()

            log.info(f"✅ Generated Dynamic Visual at {out_path} ({os.path.getsize(out_path)} bytes)")
            return out_path

        except Exception as e:
            log.error(f"Dynamic visual rendering failed: {e}")

        return ""
