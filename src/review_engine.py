import logging

log = logging.getLogger("ecopulse")

class ReviewEngine:
    def __init__(self, gemini_client):
        self.llm = gemini_client

    def draft_and_review(self, hook: str, thesis: dict) -> str:
        """
        Drafts an ultra-short, specific, high-signal LinkedIn post (under 45 words).
        """
        headline = thesis.get("headline", "")
        problem = thesis.get("concrete_problem", "")
        mechanism = thesis.get("technical_mechanism", "")
        metric = thesis.get("hard_metric", "")
        rule = thesis.get("takeaway_rule", "")
        topic_tag = thesis.get("topic_tag", "AIEngineering")

        prompt = f"""You are Arunachalam Venkatachalapathy, an AI Agent & Forward Deployment Engineer.
Write an ULTRA-SHORT, PUNCHY, HIGH-SIGNAL LinkedIn post for this engineering takeaway.

Headline: {headline}
The Concrete Problem: {problem}
The Technical Fix: {mechanism}
The Hard Metric: {metric}
The Golden Rule: {rule}

RULES:
1. STRICT LENGTH: 35 to 48 words total.
2. FORMAT:
   - Line 1: Bold statement or hook with specific noun ({headline}).
   - Line 2: The concrete problem & why raw prompt loops fail.
   - Line 3: The architectural fix + metric.
   - Line 4: The 1-sentence FDE rule.
   - Line 5: 3 hashtags (e.g., #AIAgents #ForwardDeployment #SystemsArchitecture).
3. Zero fluff, zero generic platitudes.

Output ONLY the final post text.
"""

        post = self.llm.generate_text(prompt, temperature=0.4)
        if post and 25 < len(post.split()) < 65:
            return post.strip()
            
        return (
            f"Autonomous LLM loops fail the moment they touch enterprise ERPs.\n\n"
            f"Unconstrained tool calls cause schema crashes and runaway token bills. The fix: replace autonomous loops with deterministic DAG state machines and strict Pydantic gates.\n\n"
            f"{metric} Production agents require strict boundaries, not infinite freedom.\n\n"
            f"#AIAgents #ForwardDeployment #SystemsEngineering"
        )
