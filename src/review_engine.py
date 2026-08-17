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
            f"You are a Senior Technology & Sustainability Analyst writing for senior engineering executives.\n"
            f"Hook: {hook}\n"
            f"Baseline: {thesis.get('metric_left')}\n"
            f"Solution: {thesis.get('metric_right')}\n"
            f"Context: {thesis.get('summary')}\n\n"
            "Write a high-engagement LinkedIn post adhering to these strict rules:\n"
            "1. Start directly with the given Hook.\n"
            "2. Keep every paragraph 1 to 2 short sentences with blank line breaks.\n"
            "3. Format structure:\n"
            "   - Opening hook (1-2 sentences)\n"
            "   - Core operational reality (1-2 sentences)\n"
            "   - 🛠️ THE ENGINEERING PIVOT: OPERATIONAL BREAKDOWN\n"
            "   - 1️⃣ Baseline Benchmark: (state baseline)\n"
            "   - 2️⃣ Advanced Solution: (state advanced solution)\n"
            "   - 3️⃣ Audit & Telemetry Assurance: (state compliance or measurement rigor)\n"
            "   - 💡 KEY TAKEAWAY FOR INFRASTRUCTURE & ESG LEADERS\n"
            "   - Key takeaway paragraph (1-2 sentences)\n"
            "   - 🤔 Question for the network:\n"
            "   - One sharp technical discussion question\n"
            "   - Let's discuss below. 👇\n"
            "   - #Sustainability #Engineering #CleanTech #ESG #Technology"
        )

        post = self.llm.generate_text(prompt, temperature=0.6)
        if not post or any(bad in post.lower() for bad in FORBIDDEN_PHRASES):
            return self._fallback_draft(hook, thesis)
            
        return self._format_post(post)

    def _fallback_draft(self, hook: str, thesis: dict) -> str:
        post = (
            f"{hook}\n\n"
            f"Here is the engineering reality: {thesis.get('summary')}\n\n"
            f"🛠️ THE ENGINEERING PIVOT: OPERATIONAL BREAKDOWN\n\n"
            f"1️⃣ Baseline Benchmark: {thesis.get('metric_left')}.\n\n"
            f"2️⃣ Advanced Solution: {thesis.get('metric_right')}.\n\n"
            f"3️⃣ Compliance & Audit Assurance: Direct telemetry verification under global standards replaces unverified spend multipliers.\n\n"
            f"💡 KEY TAKEAWAY FOR INFRASTRUCTURE & ESG LEADERS\n\n"
            f"As operational density increases, legacy architectures hit physical ceilings. Future resilience belongs to closed-loop, audit-verified engineering.\n\n"
            f"🤔 Question for the network:\n\n"
            f"How is your organization evaluating direct telemetry versus spend-based factor estimates this quarter?\n\n"
            f"Let's discuss below. 👇\n\n"
            f"#Sustainability #Engineering #CleanTech #ESG #EcoPulse"
        )
        return self._format_post(post)

    def _format_post(self, text: str) -> str:
        text = text.replace("THE ENGINEERING PIVOT: OPERATIONAL BREAKDOWN", self.to_unicode_bold("THE ENGINEERING PIVOT: OPERATIONAL BREAKDOWN"))
        text = text.replace("KEY TAKEAWAY FOR INFRASTRUCTURE & ESG LEADERS", self.to_unicode_bold("KEY TAKEAWAY FOR INFRASTRUCTURE & ESG LEADERS"))
        text = text.replace("Question for the network:", self.to_unicode_bold("Question for the network:"))
        return text
