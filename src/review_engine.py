import logging
import re

log = logging.getLogger("ecopulse")

class ReviewEngine:
    def __init__(self, gemini_client):
        self.llm = gemini_client

    def draft_and_review(self, hook: str, thesis: dict) -> str:
        headline = thesis.get("headline", "")
        problem = thesis.get("concrete_problem", "")
        mechanism = thesis.get("technical_mechanism", "")
        metric = thesis.get("hard_metric", "")
        rule = thesis.get("takeaway_rule", "")

        prompt = f'''You are Arunachalam Venkatachalapathy, an AI Agent & Forward Deployment Engineer.
Write an ULTRA-SHORT, AGGRESSIVE, HIGH-FOMO LinkedIn post.
You must make the reader feel like they are missing out on critical insider knowledge if they don't follow you. 
EXPLICITLY tell them to follow you or miss out forever.

Headline: {headline}
Problem: {problem}
Fix: {mechanism}
Metric: {metric}
Rule: {rule}

RULES:
1. STRICT LENGTH: 40 to 60 words total.
2. FORMAT:
   - Line 1: Shocking hook.
   - Line 2: The hard metric & reality check.
   - Line 3: The engineering fix.
   - Line 4: Explicit demand: "Follow me or miss the next insight."
3. Zero fluff, highly aggressive, insider tone.
4. DO NOT use hashtags.

Output ONLY the final post text.
'''

        post = self.llm.generate_text(prompt, temperature=0.6)
        if not post or len(post.split()) < 10:
            post = (
                f"Autonomous LLM loops fail the moment they touch enterprise ERPs "
                f"Unconstrained tool calls cause schema crashes The fix replace autonomous loops with deterministic DAG state machines "
                f"{metric} Follow me now or miss the next critical engineering breakdown"
            )
            
        # Post-process: Remove ALL special characters. Only a-zA-Z0-9 and spaces.
        clean_post = re.sub(r'[^a-zA-Z0-9\s]', '', post)
        clean_post = re.sub(r'\s+', ' ', clean_post).strip()
        
        return clean_post
