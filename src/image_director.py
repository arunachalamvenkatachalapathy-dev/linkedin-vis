"""
Image Director — Multi-Style Visual Generator

Supports 5 image styles matched to post framing:
  1. text_on_card     — Bold quote card (HTML template, 1080×1080)
  2. data_visual      — Clean stat card with comparison (HTML template, 1080×1080)
  3. diagram_framework — Vertical step flow (HTML template, 1080×1350)
  4. editorial_illustration — Abstract art via Gemini native image gen (1080×1080)
  5. before_after_split — Two-panel contrast (HTML template, 1080×1080)

All HTML templates render via Playwright at 2x device scale for crisp output.
Image prompts are driven by the Turn line, not the whole post.
"""

import os
import json
import re
import logging
from datetime import datetime, timezone
from pathlib import Path
from jinja2 import Template

log = logging.getLogger("ecopulse")

TEMPLATES_DIR = Path(__file__).parent / "templates"

# Aspect ratio configs
ASPECT_1x1 = {"width": 1080, "height": 1080}
ASPECT_4x5 = {"width": 1080, "height": 1350}

STYLE_ASPECTS = {
    "text_on_card":           ASPECT_1x1,
    "data_visual":            ASPECT_1x1,
    "diagram_framework":      ASPECT_4x5,
    "editorial_illustration": ASPECT_1x1,
    "before_after_split":     ASPECT_1x1,
}


class ImageDirector:
    def __init__(self, gemini_client=None):
        self.llm = gemini_client

    def generate_image(self, image_style: str, turn_line: str,
                       thesis_data: dict, raw_data: dict,
                       out_path: str = "state/latest_image.png") -> str:
        """
        Generate the visual for the selected image_style.
        The Turn line drives the visual message, not the whole post.
        """
        log.info(f"🎨 Generating [{image_style.upper()}] visual for: '{turn_line[:60]}...'")

        if image_style == "text_on_card":
            return self._render_text_on_card(turn_line, thesis_data, out_path)
        elif image_style == "data_visual":
            return self._render_data_visual(turn_line, thesis_data, raw_data, out_path)
        elif image_style == "diagram_framework":
            return self._render_diagram_framework(turn_line, thesis_data, raw_data, out_path)
        elif image_style == "editorial_illustration":
            return self._render_editorial_illustration(turn_line, thesis_data, out_path)
        elif image_style == "before_after_split":
            return self._render_before_after_split(turn_line, thesis_data, raw_data, out_path)
        else:
            log.warning(f"Unknown image style '{image_style}', falling back to text_on_card")
            return self._render_text_on_card(turn_line, thesis_data, out_path)

    # ── 1. Text-on-Card ──────────────────────────────────────────────────

    def _render_text_on_card(self, turn_line: str, thesis_data: dict, out_path: str) -> str:
        headline = thesis_data.get("headline", "")
        badge = self._extract_badge(headline)

        return self._render_html_template(
            "text_on_card",
            {"turn_line": turn_line, "badge": badge,
             "date_str": self._date_str()},
            ASPECT_1x1, out_path
        )

    # ── 2. Data Visual ───────────────────────────────────────────────────

    def _render_data_visual(self, turn_line: str, thesis_data: dict,
                            raw_data: dict, out_path: str) -> str:
        # Extract metrics from thesis or raw data
        headline = thesis_data.get("headline", raw_data.get("title", ""))
        metric_val = self._extract_number(turn_line) or thesis_data.get("hard_metric", "—")
        metric_label = thesis_data.get("topic_tag", "KEY METRIC")

        # Try to extract comparison data
        context = turn_line
        baseline_val = raw_data.get("metric_1_val", thesis_data.get("baseline_stat", "—"))
        baseline_sub = raw_data.get("metric_1_sub", "Baseline")
        target_val = raw_data.get("metric_2_val", thesis_data.get("target_stat", "—"))
        target_sub = raw_data.get("metric_2_sub", "Measured")

        return self._render_html_template(
            "data_visual",
            {"headline": headline, "metric_val": metric_val, "metric_label": metric_label,
             "context": context, "badge": "DATA BREAKDOWN",
             "baseline_val": baseline_val, "baseline_sub": baseline_sub,
             "target_val": target_val, "target_sub": target_sub,
             "source": raw_data.get("source", ""), "date_str": self._date_str()},
            ASPECT_1x1, out_path
        )

    # ── 3. Diagram/Framework ────────────────────────────────────────────

    def _render_diagram_framework(self, turn_line: str, thesis_data: dict,
                                  raw_data: dict, out_path: str) -> str:
        headline = thesis_data.get("headline", raw_data.get("title", ""))
        takeaway = turn_line

        # Generate steps via Gemini if not already present
        steps = self._generate_framework_steps(headline, raw_data.get("raw_text", ""))

        return self._render_html_template(
            "diagram_framework",
            {"headline": headline, "steps": steps, "takeaway": takeaway,
             "badge": "FRAMEWORK", "date_str": self._date_str()},
            ASPECT_4x5, out_path
        )

    def _generate_framework_steps(self, headline: str, context: str) -> list:
        """Generate 3-4 framework steps via Gemini."""
        if not self.llm:
            return [
                {"title": "Identify", "desc": "Recognize the core pattern."},
                {"title": "Analyze", "desc": "Break down the components."},
                {"title": "Execute", "desc": "Implement the solution."},
            ]

        prompt = f"""Extract 3-4 sequential steps from this content to create a framework diagram.
Each step needs a short title (2-4 words) and a description (1 sentence, max 15 words).

Topic: {headline}
Context: {context[:1500]}

Return valid JSON:
{{
  "steps": [
    {{"title": "Step Title", "desc": "Short description"}},
    ...
  ]
}}"""

        try:
            res = self.llm.generate_text(prompt, temperature=0.3, json_mode=True)
            if res:
                data = json.loads(res)
                steps = data.get("steps", [])
                if steps and len(steps) >= 2:
                    return steps[:4]
        except Exception as e:
            log.warning(f"Framework steps generation failed: {e}")

        return [
            {"title": "Identify", "desc": "Recognize the core pattern."},
            {"title": "Analyze", "desc": "Break down the mechanism."},
            {"title": "Execute", "desc": "Implement the engineering fix."},
        ]

    # ── 4. Editorial Illustration (Gemini Native Image Gen) ──────────────

    def _render_editorial_illustration(self, turn_line: str, thesis_data: dict,
                                       out_path: str) -> str:
        headline = thesis_data.get("headline", "")

        prompt = (
            f"Create an abstract, metaphorical editorial illustration for a LinkedIn post. "
            f"Core message to encode visually: '{turn_line}'. "
            f"Topic: {headline}. "
            f"Style: Modern, minimal, editorial illustration with muted professional color palette. "
            f"Abstract shapes and visual metaphors — NOT literal depiction. "
            f"Constraints: No generic stock-photo tropes (no handshakes, lightbulbs, puzzle pieces, "
            f"generic diverse-team-in-meeting). No text rendered in the image. "
            f"High contrast, clean composition, mobile-first legibility. "
            f"Square 1:1 aspect ratio."
        )

        if self.llm:
            img_bytes = self.llm.generate_image(prompt)
            if img_bytes and len(img_bytes) > 1000:
                os.makedirs(os.path.dirname(out_path) or '.', exist_ok=True)
                with open(out_path, "wb") as f:
                    f.write(img_bytes)
                log.info(f"✅ Generated editorial illustration: {out_path}")
                return out_path

        # Fallback to text_on_card if image gen fails
        log.warning("Editorial illustration failed, falling back to text_on_card")
        return self._render_text_on_card(turn_line, thesis_data, out_path)

    # ── 5. Before/After Split ────────────────────────────────────────────

    def _render_before_after_split(self, turn_line: str, thesis_data: dict,
                                   raw_data: dict, out_path: str) -> str:
        headline = thesis_data.get("headline", raw_data.get("title", ""))

        # Generate before/after content via Gemini
        ba_data = self._generate_before_after(headline, raw_data.get("raw_text", ""), turn_line)

        return self._render_html_template(
            "before_after_split",
            {"headline": headline,
             "before_title": ba_data.get("before_title", "Legacy Approach"),
             "before_body": ba_data.get("before_body", ""),
             "before_stat": ba_data.get("before_stat", ""),
             "after_title": ba_data.get("after_title", "Modern Solution"),
             "after_body": ba_data.get("after_body", ""),
             "after_stat": ba_data.get("after_stat", ""),
             "takeaway": turn_line, "badge": "BEFORE → AFTER",
             "date_str": self._date_str()},
            ASPECT_1x1, out_path
        )

    def _generate_before_after(self, headline: str, context: str, turn_line: str) -> dict:
        """Generate before/after comparison content via Gemini."""
        if not self.llm:
            return {
                "before_title": "Legacy Method", "before_body": "Traditional approach with known limitations.",
                "before_stat": "—",
                "after_title": "Modern Solution", "after_body": "Engineering breakthrough that changes the calculus.",
                "after_stat": "—"
            }

        prompt = f"""Create a Before vs After comparison for a visual infographic.

Topic: {headline}
Context: {context[:1500]}
Key insight: {turn_line}

Return valid JSON:
{{
  "before_title": "2-3 word title for the old/legacy approach",
  "before_body": "1-2 sentence description of the problem (max 25 words)",
  "before_stat": "One key stat for the old approach",
  "after_title": "2-3 word title for the new/modern approach",
  "after_body": "1-2 sentence description of the solution (max 25 words)",
  "after_stat": "One key stat for the new approach"
}}"""

        try:
            res = self.llm.generate_text(prompt, temperature=0.3, json_mode=True)
            if res:
                return json.loads(res)
        except Exception as e:
            log.warning(f"Before/after generation failed: {e}")

        return {
            "before_title": "Legacy Method", "before_body": "Traditional approach.",
            "before_stat": "—",
            "after_title": "Modern Solution", "after_body": "New engineering approach.",
            "after_stat": "—"
        }

    # ── Shared HTML rendering via Playwright ─────────────────────────────

    def _render_html_template(self, template_name: str, context: dict,
                              aspect: dict, out_path: str) -> str:
        try:
            from playwright.sync_api import sync_playwright

            html_path = TEMPLATES_DIR / f"{template_name}.html"
            css_path = TEMPLATES_DIR / f"{template_name}.css"

            with open(html_path, "r", encoding="utf-8") as f:
                html_content = f.read()
            with open(css_path, "r", encoding="utf-8") as f:
                css_content = f.read()

            html_with_css = html_content.replace("/* INLINE_STYLES */", css_content)
            template = Template(html_with_css)
            rendered = template.render(**context)

            os.makedirs(os.path.dirname(out_path) or '.', exist_ok=True)

            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page(
                    viewport={"width": aspect["width"], "height": aspect["height"]},
                    device_scale_factor=2
                )
                page.set_content(rendered, wait_until="domcontentloaded")
                page.screenshot(path=out_path, type="png")
                browser.close()

            log.info(f"✅ Rendered [{template_name}] at {aspect['width']}×{aspect['height']}: {out_path} ({os.path.getsize(out_path)} bytes)")
            return out_path

        except Exception as e:
            log.error(f"Template rendering failed [{template_name}]: {e}")
            return ""

    # ── Utility methods ──────────────────────────────────────────────────

    @staticmethod
    def _date_str() -> str:
        return datetime.now(timezone.utc).strftime("%d %b %Y")

    @staticmethod
    def _extract_badge(headline: str) -> str:
        """Extract a short 2-3 word badge from headline."""
        words = headline.split()[:3]
        return " ".join(words).upper() if words else "INSIGHT"

    @staticmethod
    def _extract_number(text: str) -> str:
        """Extract the first prominent number from text."""
        match = re.search(r'\b(\d+[\.\,]?\d*\s*(?:%|gCO2/kWh|ppm|kWh|MW|GW|x|billion|million)?)\b', text)
        return match.group(1).strip() if match else ""
