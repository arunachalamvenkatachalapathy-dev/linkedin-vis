import logging

log = logging.getLogger("ecopulse")

FORBIDDEN_PHRASES = [
    "in today's world",
    "in today's fast-paced world",
    "recent developments",
    "this highlights",
    "this underscores",
    "as industries evolve",
    "it is important to note",
    "with increasing awareness",
    "delve",
    "testament",
    "game-changer",
    "paradigm shift",
    "synergy",
    "beacon",
    "tapestry"
]

class ReviewEngine:
    def __init__(self, gemini_client):
        self.llm = gemini_client

    def to_unicode_bold(self, text: str) -> str:
        res = []
        for char in text:
            if 'A' <= char <= 'Z':
                res.append(chr(0x1D5D4 + ord(char) - ord('A')))
            elif 'a' <= char <= 'z':
                res.append(chr(0x1D5EE + ord(char) - ord('a')))
            elif '0' <= char <= '9':
                res.append(chr(0x1D7EC + ord(char) - ord('0')))
            else:
                res.append(char)
        return "".join(res)

    def draft_and_review(self, hook: str, thesis: dict) -> str:
        prompt = (
            f"You are a Senior Environmental Engineering & ESG Analyst writing for Financial Times and Reuters.\n"
            f"Hook: {hook}\n"
            f"Baseline Metric: {thesis.get('metric_left')}\n"
            f"Solution Metric: {thesis.get('metric_right')}\n"
            f"Context: {thesis.get('summary')}\n\n"
            f"WRITE A LINKEDIN POST FOLLOWING THESE STRICT RULES:\n"
            f"1. Start exactly with the provided Hook.\n"
            f"2. Paragraphs: Keep every paragraph strictly 1 to 2 short sentences long with clear line breaks.\n"
            f"3. Forbidden Words: NEVER use 'highlights', 'underscores', 'delve', 'testament', 'fast-paced world', 'paradigm shift'.\n"
            f"4. Structure:\n"
            f"   - Opening hook (1-2 sentences)\n"
            f"   - Core operational reality (1-2 sentences)\n"
            f"   - 🛠️ Benchmark comparison (Baseline vs Solution vs Audit Assurance)\n"
            f"   - 💡 Executive takeaway for sustainability and engineering leaders\n"
            f"   - 🤔 One precise technical question for discussion\n"
            f"5. Output plain text without markdown **bold**."
        )

        post = self.llm.generate_text(prompt)
        
        # Self-correction check
        lower_post = post.lower()
        if any(bad in lower_post for bad in FORBIDDEN_PHRASES):
            log.warning("AI buzzwords detected. Formatting fallback.")
            return self._fallback_draft(hook, thesis)
            
        # Apply formatting
        return self._format_post(post)

    def _fallback_draft(self, hook: str, thesis: dict) -> str:
        post = (
            f"{hook}\n\n"
            f"Here is the engineering reality: {thesis.get('summary')}\n\n"
            f"🛠️ THE ENGINEERING PIVOT: OPERATIONAL BREAKDOWN\n\n"
            f"1️⃣ Baseline Benchmark: {thesis.get('metric_left')}.\n\n"
            f"2️⃣ Advanced Solution: {thesis.get('metric_right')}.\n\n"
            f"3️⃣ Compliance & Audit Assurance: Direct telemetry alignment under BRSR Core 9 attributes and CSRD ESRS E1 standards replaces unverified spend multipliers.\n\n"
            f"💡 KEY TAKEAWAY FOR INFRASTRUCTURE & ESG LEADERS\n\n"
            f"As operational density increases, legacy methods hit physical limits. Sustainability leadership belongs to closed-loop, audit-verified engineering.\n\n"
            f"🤔 Question for the network:\n"
            f"How is your engineering team evaluating direct operational telemetry versus spend-based factor estimates this quarter?\n\n"
            f"Let's discuss below. 👇\n\n"
            f"#Sustainability #CleanTech #ESG #EnvironmentalEngineering #EcoPulse"
        )
        return self._format_post(post)

    def _format_post(self, text: str) -> str:
        text = text.replace("THE ENGINEERING PIVOT: OPERATIONAL BREAKDOWN", self.to_unicode_bold("THE ENGINEERING PIVOT: OPERATIONAL BREAKDOWN"))
        text = text.replace("KEY TAKEAWAY FOR INFRASTRUCTURE & ESG LEADERS", self.to_unicode_bold("KEY TAKEAWAY FOR INFRASTRUCTURE & ESG LEADERS"))
        text = text.replace("Question for the network:", self.to_unicode_bold("Question for the network:"))
        return text
