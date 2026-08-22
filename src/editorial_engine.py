import json
import logging
import random
from datetime import datetime

log = logging.getLogger("ecopulse")

class EditorialEngine:
    def __init__(self, gemini_client):
        self.llm = gemini_client

    def generate_thesis(self, raw_data: dict) -> dict:
        raw_text = raw_data.get("raw_text", "")
        source_name = raw_data.get("source", "Telemetry Stream")
        title = raw_data.get("title", "Real-Time Systems Analysis")
        theme = raw_data.get("theme", "ESG & CleanTech Telemetry")
        is_realtime = raw_data.get("is_realtime", False)
        
        prompt = f"""You are a Lead AI Architect and Systems Auditor.
Analyze this real-world technical data stream and extract structured insights for a high-impact, non-repetitive visual infographic.

Source: {source_name}
Title: {title}
Theme: {theme}
Is Real-Time Data: {is_realtime}
Context:
{raw_text[:4000]}

REQUIREMENTS:
1. visual_type: Choose dynamically among:
   - 'alien_qa' (Satirical Earthling question vs polite brutal Alien answer)
   - 'realtime_telemetry' (If real-time sensor/grid metrics exist)
   - 'whiteboard_flow' (3-step technical DAG architecture)
   - 'code_reality_split' (Lab prototype vs Enterprise production reality check)
   - 'provocation_quote' (Hard shocking contrarian fact with before/after stats)
2. topic_tag: Short 2-3 word technical badge (e.g. 'GRID CARBON REALITY', 'FDE STATE MACHINE', 'SCOPE 2 AUDIT').
3. headline: Punchy title naming the specific technology or breakthrough (max 7 words).
4. concrete_problem: 1 sentence on the problem.
5. technical_mechanism: 1 sentence on the solution.
6. hard_metric: 1 quantitative metric from the context.
7. takeaway_rule: 1-sentence golden rule for the bottom bar.
8. human_question: Satirical naive question from a human tech lead (max 25 words).
9. alien_answer: Polite, calm, data-backed answer from an alien systems auditor (max 30 words).
10. metric_1_label, metric_1_val, metric_1_sub: Primary metric.
11. metric_2_label, metric_2_val, metric_2_sub: Secondary metric.
12. metric_3_label, metric_3_val, metric_3_sub: Tertiary metric.
13. flow_steps: 3 steps with 'title' and 'desc'.
14. baseline_stat & target_stat: Before vs After stats.

Return ONLY valid JSON matching this schema:
{{
  "visual_type": "alien_qa",
  "topic_tag": "REAL-TIME GRID AUDIT",
  "headline": "Live Grid Carbon Drops to 93 gCO2/kWh",
  "concrete_problem": "Static annual factors overstate enterprise Scope 2 footprint.",
  "technical_mechanism": "Dynamic carbon-aware workload scheduling shifts batch compute.",
  "hard_metric": "93 gCO2/kWh grid carbon intensity",
  "takeaway_rule": "Static emissions accounting is dead. Real-time telemetry is mandatory.",
  "human_question": "We bought vintage tree offsets from 2012 so running our GPU cluster during peak coal hours is green right?",
  "alien_answer": "Politely speaking the grid emits 93 gCO2/kWh right now. Trees do not absorb midnight coal spikes. Dynamic workload scheduling does.",
  "metric_1_label": "GRID CARBON INTENSITY",
  "metric_1_val": "93 gCO2/kWh",
  "metric_1_sub": "Live Sensor Reading",
  "metric_2_label": "CLEAN ENERGY SHARE",
  "metric_2_val": "63.0%",
  "metric_2_sub": "Wind + Solar + Nuclear",
  "metric_3_label": "ATMOSPHERIC CO2",
  "metric_3_val": "427.8 ppm",
  "metric_3_sub": "NOAA Global Baseline",
  "baseline_stat": "Annual Avg: 210 gCO2",
  "target_stat": "Live Telemetry: 93 gCO2",
  "flow_steps": [
    {{"title": "Grid Telemetry Ingest", "desc": "Poll 5-minute carbon intensity signals from national grid APIs."}},
    {{"title": "Carbon-Aware Scheduler", "desc": "Queue heavy batch compute workloads until clean energy exceeds 60%."}},
    {{"title": "Audit Proof Generation", "desc": "Output immutable CSRD and BRSR assurance proofs."}}
  ]
}}
"""

        try:
            res = self.llm.generate_text(prompt, temperature=0.4, json_mode=True)
            if res:
                parsed = json.loads(res)
                if is_realtime and parsed.get("visual_type") in ["realtime_telemetry", "alien_qa"]:
                    if "metric_1_val" in raw_data:
                        parsed["metric_1_label"] = raw_data.get("metric_1_label", parsed.get("metric_1_label"))
                        parsed["metric_1_val"] = raw_data.get("metric_1_val", parsed.get("metric_1_val"))
                        parsed["metric_1_sub"] = raw_data.get("metric_1_sub", parsed.get("metric_1_sub"))
                        parsed["metric_2_label"] = raw_data.get("metric_2_label", parsed.get("metric_2_label"))
                        parsed["metric_2_val"] = raw_data.get("metric_2_val", parsed.get("metric_2_val"))
                        parsed["metric_2_sub"] = raw_data.get("metric_2_sub", parsed.get("metric_2_sub"))
                        parsed["metric_3_label"] = raw_data.get("metric_3_label", parsed.get("metric_3_label"))
                        parsed["metric_3_val"] = raw_data.get("metric_3_val", parsed.get("metric_3_val"))
                        parsed["metric_3_sub"] = raw_data.get("metric_3_sub", parsed.get("metric_3_sub"))
                return parsed
        except Exception as e:
            log.warning(f"EditorialEngine JSON generation fallback: {e}")

        # Randomize visual type if fallback occurs
        fallback_types = ["alien_qa", "realtime_telemetry", "whiteboard_flow", "code_reality_split", "provocation_quote"]
        chosen_type = "realtime_telemetry" if is_realtime else random.choice(fallback_types)

        return {
            "visual_type": chosen_type,
            "topic_tag": "GALACTIC AUDIT",
            "headline": title[:50],
            "concrete_problem": f"Static estimations fail for {title[:40]}.",
            "technical_mechanism": "Dynamic telemetry provides verifiable ground truth.",
            "hard_metric": "93 gCO2/kWh grid carbon intensity",
            "takeaway_rule": "Real-time telemetry beats static models every single time.",
            "human_question": "If we buy enough unverified offset credits can we claim our 24/7 AI compute is net zero?",
            "alien_answer": "With all due respect physics cannot be bribed. Schedule compute when renewable energy actually peaks.",
            "metric_1_label": raw_data.get("metric_1_label", "GRID INTENSITY"),
            "metric_1_val": raw_data.get("metric_1_val", "93 gCO2/kWh"),
            "metric_1_sub": raw_data.get("metric_1_sub", "Live Sensor Reading"),
            "metric_2_label": raw_data.get("metric_2_label", "CLEAN ENERGY"),
            "metric_2_val": raw_data.get("metric_2_val", "63.0%"),
            "metric_2_sub": raw_data.get("metric_2_sub", "Wind + Solar + Hydro"),
            "metric_3_label": raw_data.get("metric_3_label", "ATMOSPHERIC CO2"),
            "metric_3_val": raw_data.get("metric_3_val", "427.8 ppm"),
            "metric_3_sub": raw_data.get("metric_3_sub", "NOAA Baseline Telemetry"),
            "baseline_stat": "210 gCO2/kWh Flat",
            "target_stat": "93 gCO2/kWh Live",
            "flow_steps": [
                {"title": "Telemetry Ingestion", "desc": "Ingest live API feeds from grid operators."},
                {"title": "Dynamic Scheduling", "desc": "Shift high-compute jobs to peak clean hours."},
                {"title": "Assurance Logging", "desc": "Produce audit-ready proofs for Scope 2 compliance."}
            ]
        }
