import logging

log = logging.getLogger("ecopulse")

class ReviewEngine:
    def __init__(self, gemini_client):
        self.llm = gemini_client

    def draft_and_review(self, hook: str, thesis: dict) -> str:
        headline = thesis.get("headline", "")
        tweet_body = thesis.get("tweet_body", "")
        topic_tag = thesis.get("topic_tag", "Systems")

        prompt = f'''You are Arunachalam Venkatachalapathy, an ESG & Systems Engineering Specialist.
Write an ULTRA-SHORT, PUNCHY, HIGH-VALUE LinkedIn post caption for this insight.

Topic: {headline}
Core Insight: {tweet_body}
Domain: {topic_tag}

RULES:
1. LENGTH: 3 to 4 short lines MAXIMUM (strictly 30-50 words total).
2. TONE: Thoughtful, professional, high-signal, purposeful. Zero media outrage, zero clickbait.
3. STRUCTURE:
   - Line 1: 1 punchy hook / core truth.
   - Line 2: 1 sentence explaining why this principle matters.
   - Line 3: 1 concise takeaway or golden rule.
   - Line 4: 3 clean hashtags (e.g. #Sustainability #SystemsEngineering #Innovation).

Output ONLY the final short post text.
'''

        post = self.llm.generate_text(prompt, temperature=0.5)
        if post and len(post.split()) < 75:
            return post.strip()
            
        return (
            f"Estimation gives you an illusion of control. Direct telemetry gives you the truth.\n\n"
            f"Whether managing thermal load or Scope 3 emissions, verifiable real-time data is the only foundation for real optimization.\n\n"
            f"Audit-grade telemetry beats spreadsheet assumptions every single time.\n\n"
            f"#{topic_tag.replace(' ', '')} #SystemsEngineering #Sustainability"
        )
