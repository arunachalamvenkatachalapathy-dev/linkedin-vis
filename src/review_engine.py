"""
Review Engine — Quality Gate Evaluator

Runs 6 quality checks before a post/image pair is published:
1. Specificity check — at least one concrete number, name, or fact
2. Hook strength — score 1–10, reject below threshold
3. Repetition check — cross-reference combination tracker
4. Cliché filter — detect burned-out phrases
5. Turn-line check — verify one quotable standalone sentence exists
6. Image-text match — verify image style aligns with post Turn line

Returns pass/fail with scores and failure reasons.
On failure, the orchestrator retries with adjusted parameters.
"""

import re
import logging

log = logging.getLogger("ecopulse")

# Burned-out phrases and patterns (Section 13)
CLICHE_PATTERNS = [
    r"in today'?s fast[- ]paced world",
    r"let that sink in",
    r"here'?s the thing:?",
    r"i'?m not going to lie",
    r"not going to lie",
    r"game[- ]?changer",
    r"paradigm shift",
    r"synerg",
    r"repost if you agree",
    r"tag someone who needs this",
    r"🚀🔥💯",
    r"💯🔥🚀",
    r"agree\?$",
    r"^thoughts\?$",
    r"i'?m excited to share",
    r"in today'?s world",
    r"i recently",
    r"i wanted to share",
    r"let me know in the comments",
]

# Emoji-as-bullet patterns
EMOJI_BULLET_PATTERN = re.compile(r"^[☑✅➡️📌🔹▪️•◉◆●]", re.MULTILINE)

# Excessive emoji (more than 1 per 100 words)
def _count_emojis(text: str) -> int:
    emoji_pattern = re.compile(
        "[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF\U0001F680-\U0001F6FF"
        "\U0001F1E0-\U0001F1FF\U00002702-\U000027B0\U0001FA00-\U0001FAFF"
        "\U00002600-\U000026FF\U0000FE00-\U0000FE0F]+", re.UNICODE
    )
    return len(emoji_pattern.findall(text))


class ReviewEngine:
    def __init__(self, gemini_client):
        self.llm = gemini_client

    def evaluate(self, post_text: str, turn_line: str, proof_fact: str,
                 hook_type: str, image_style: str,
                 combination_tracker=None, config=None) -> dict:
        """
        Run all 6 quality gates. Returns:
        {
            "passed": bool,
            "scores": {gate_name: score_or_bool},
            "failures": [list of failure reasons],
            "suggestions": [list of fix suggestions]
        }
        """
        failures = []
        suggestions = []
        scores = {}

        # Gate 1: Specificity check
        specificity = self._check_specificity(post_text, proof_fact)
        scores["specificity"] = specificity
        if not specificity:
            failures.append("No concrete number, name, or specific fact found in the post.")
            suggestions.append("Extract a specific data point from the source material.")

        # Gate 2: Hook strength
        hook_score = self._check_hook_strength(post_text)
        scores["hook_strength"] = hook_score
        if hook_score < 6:
            failures.append(f"Hook strength score {hook_score}/10 — below threshold of 6.")
            suggestions.append("Try a different hook_type or sharpen the opening line.")

        # Gate 3: Repetition check
        if combination_tracker and config:
            rep_ok = self._check_repetition(combination_tracker, config)
            scores["repetition_check"] = rep_ok
            if not rep_ok:
                failures.append("Component combination too similar to recent posts.")
                suggestions.append("Change hook_type or body_structure.")

        # Gate 4: Cliché filter
        cliches_found = self._check_cliches(post_text)
        scores["cliche_filter"] = len(cliches_found) == 0
        if cliches_found:
            failures.append(f"Cliché phrases detected: {', '.join(cliches_found)}")
            suggestions.append("Rewrite to remove generic phrases.")

        # Gate 5: Turn-line check
        has_turn = self._check_turn_line(turn_line, post_text)
        scores["turn_line"] = has_turn
        if not has_turn:
            failures.append("No quotable standalone Turn line found.")
            suggestions.append("Run Pass 2 again or manually craft a Turn line.")

        # Gate 6: Image-text alignment
        img_match = self._check_image_alignment(image_style, turn_line, post_text)
        scores["image_text_match"] = img_match
        if not img_match:
            failures.append(f"Image style '{image_style}' may not align with the post content.")
            suggestions.append("Consider a different image_style.")

        passed = len(failures) == 0
        level = "✅ PASSED" if passed else f"❌ FAILED ({len(failures)} gates)"
        log.info(f"Quality Gate {level}: {scores}")

        return {
            "passed": passed,
            "scores": scores,
            "failures": failures,
            "suggestions": suggestions,
        }

    # ── Individual gate implementations ──────────────────────────────────

    def _check_specificity(self, post_text: str, proof_fact: str) -> bool:
        """Gate 1: At least one concrete number, named source, or specific fact."""
        if proof_fact and len(proof_fact) > 10:
            return True
        # Check for numbers in the post
        numbers = re.findall(r'\b\d+[\.\,]?\d*\s*(?:%|gCO2|ppm|kWh|MW|GW|billion|million|trillion)?\b', post_text)
        if len(numbers) >= 1:
            return True
        # Check for named entities (capitalized multi-word sequences)
        named = re.findall(r'[A-Z][a-z]+(?:\s[A-Z][a-z]+)+', post_text)
        return len(named) >= 1

    def _check_hook_strength(self, post_text: str) -> int:
        """Gate 2: Score the opening 1–2 lines for scroll-stop power."""
        lines = [l.strip() for l in post_text.strip().split('\n') if l.strip()]
        if not lines:
            return 0

        first_line = lines[0]
        score = 5  # baseline

        # Bonus: short and punchy
        word_count = len(first_line.split())
        if word_count <= 12:
            score += 2
        elif word_count <= 8:
            score += 3

        # Penalty: starts with "I" + mundane verb
        if re.match(r'^I\s+(recently|wanted|am|was|have|had|just)\b', first_line, re.IGNORECASE):
            score -= 3

        # Penalty: generic opener
        lower = first_line.lower()
        for cliche in ["in today's", "did you know", "i'm excited"]:
            if cliche in lower:
                score -= 3

        # Bonus: contains a number
        if re.search(r'\d+', first_line):
            score += 1

        # Bonus: contains a question
        if '?' in first_line:
            score += 1

        return max(1, min(10, score))

    def _check_repetition(self, combination_tracker, config) -> bool:
        """Gate 3: Cross-reference with combination tracker."""
        # Check if hook+body combo was used in last 5
        if combination_tracker._is_hook_body_repeat(config.hook_type, config.body_structure):
            return False
        # Check immediate repeats
        if combination_tracker._is_immediate_repeat("hook_type", config.hook_type):
            return False
        if combination_tracker._is_immediate_repeat("cta_type", config.cta_type):
            return False
        return True

    def _check_cliches(self, post_text: str) -> list:
        """Gate 4: Detect burned-out engagement-bait phrases."""
        found = []
        lower = post_text.lower()
        for pattern in CLICHE_PATTERNS:
            if re.search(pattern, lower, re.IGNORECASE | re.MULTILINE):
                found.append(pattern.replace(r"'?", "'").replace(r"[- ]?", " "))

        # Check emoji-as-bullet abuse
        emoji_bullets = EMOJI_BULLET_PATTERN.findall(post_text)
        if len(emoji_bullets) >= 3:
            found.append("emoji-as-bullet pattern (3+ lines starting with emoji)")

        # Check excessive emoji density
        word_count = len(post_text.split())
        emoji_count = _count_emojis(post_text)
        if word_count > 0 and emoji_count > (word_count / 100) + 1:
            found.append(f"excessive emoji density ({emoji_count} emojis in {word_count} words)")

        # Check hashtag wall (>3)
        hashtags = re.findall(r'#\w+', post_text)
        if len(hashtags) > 3:
            found.append(f"hashtag wall ({len(hashtags)} hashtags, max 3)")

        return found

    def _check_turn_line(self, turn_line: str, post_text: str) -> bool:
        """Gate 5: Verify a quotable Turn line exists."""
        if not turn_line or len(turn_line) < 15:
            return False
        # The turn line should be substantive, not generic
        generic_turns = ["follow me", "let me know", "agree?", "thoughts?"]
        lower = turn_line.lower()
        for g in generic_turns:
            if g in lower:
                return False
        return True

    def _check_image_alignment(self, image_style: str, turn_line: str, post_text: str) -> bool:
        """Gate 6: Basic alignment check between image style and content."""
        # Simple heuristic checks — a full Gemini pass would be too expensive here
        if not image_style or not post_text:
            return True  # pass by default if missing

        lower_post = post_text.lower()

        # data_visual should have numbers
        if image_style == "data_visual":
            has_numbers = bool(re.search(r'\d+', post_text))
            if not has_numbers:
                return False

        # before_after_split should have contrast language
        if image_style == "before_after_split":
            contrast_words = ["before", "after", "old", "new", "was", "now", "from", "to", "instead"]
            has_contrast = any(w in lower_post for w in contrast_words)
            if not has_contrast:
                return False

        return True
