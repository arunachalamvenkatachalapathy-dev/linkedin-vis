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
        archetype = thesis.get("archetype", "deep_dive")
        headline = thesis.get("headline", "")
        core_insight = thesis.get("core_insight", "")
        category = thesis.get("category", "TECH")

        prompt = f"""You are a top-tier LinkedIn creator and technical analyst.
Write an authentic, highly engaging LinkedIn post based on this story:

Hook to start with: {hook}
Archetype: {archetype}
Topic Category: {category}
Headline: {headline}
Core Insight: {core_insight}

WRITING & FORMATTING RULES:
1. START with the exact Hook provided above.
2. NO COOKIE-CUTTER TEMPLATES: Do NOT use hardcoded sections like 'THE ENGINEERING PIVOT' or force ESG terms unless the story is specifically about ESG.
3. Structure organically based on the {archetype} archetype:
   - Paragraphs must be strictly 1-2 short sentences with blank lines between them for maximum mobile readability.
   - Use clean bullet points with relevant Unicode bold labels (e.g. 𝗧𝗵𝗲 𝗥𝗼𝗼𝘁 𝗖𝗮𝘂𝘀𝗲:, 𝗪𝗵𝗮𝘁 𝗪𝗲𝗻𝘁 𝗪𝗿𝗼𝗻𝗴:, 𝗧𝗵𝗲 𝗙𝗶𝘅:, 𝗞𝗲𝘆 𝗧𝗮𝗸𝗲𝗮𝘄𝗮𝘆:).
   - Tell the story with technical authority, sharp contrast, and actionable clarity.
   - End with one provocative, discussion-sparking technical question for the audience.
   - Add 'Let\'s discuss below. 👇' followed by 3-5 relevant, specific hashtags (e.g. #SoftwareEngineering #DevOps #AI #CloudArchitecture).
4. FORBIDDEN WORDS: NEVER use 'delve', 'testament', 'fast-paced world', 'paradigm shift', 'synergy', 'game-changer'.
5. Output pure text.
"""

        post = self.llm.generate_text(prompt, temperature=0.6)
        if not post or any(bad in post.lower() for bad in FORBIDDEN_PHRASES):
            return self._fallback_draft(hook, thesis)
            
        return post

    def _fallback_draft(self, hook: str, thesis: dict) -> str:
        return (
            f"{hook}\n\n"
            f"{thesis.get('core_insight', '')}\n\n"
            f"𝗪𝗵𝗮𝘁 𝗧𝗵𝗶𝘀 𝗠𝗲𝗮𝗻𝘀 𝗳𝗼𝗿 𝗘𝗻𝗴𝗶𝗻𝗲𝗲𝗿𝗶𝗻𝗴 𝗟𝗲𝗮𝗱𝗲𝗿𝘀:\n\n"
            f"1. Visibility beyond shallow pings is essential for reliable operations.\n"
            f"2. Real user-journey telemetry beats green component dashboards every time.\n\n"
            f"🤔 Question for the network:\n"
            f"How is your team ensuring your telemetry matches actual user experience rather than superficial uptime checks?\n\n"
            f"Let's discuss below. 👇\n\n"
            f"#Engineering #Technology #SoftwareArchitecture #Systems"
        )
