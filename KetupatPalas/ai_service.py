from __future__ import annotations

import json
from typing import Any, Dict, List

from openai import OpenAI

from analytics import build_prompt_payload


class AIService:
    def __init__(self, api_key: str, base_url: str, model: str) -> None:
        self.api_key = api_key
        self.base_url = base_url
        self.model = model

    # ─────────────────────────────────────────────
    # FALLBACK (SAFE ALWAYS WORK)
    # ─────────────────────────────────────────────
    def _fallback(self, payload: Dict[str, Any], error: str | None = None) -> Dict[str, Any]:
        return {
            "source": "rule-based fallback",
            "error": error,
            "data_summary": payload,
            "suggestions": [
                {
                    "title": "Monitor hospital workload",
                    "explanation": "Continue monitoring waiting time, staff workload, and patient demand.",
                    "priority": "Medium",
                },
                {
                    "title": "Review staffing levels",
                    "explanation": "Check doctor and nurse availability if waiting time increases.",
                    "priority": "High",
                },
                {
                    "title": "Prepare additional capacity",
                    "explanation": "Prepare extra beds or temporary staff if demand rises.",
                    "priority": "Medium",
                },
            ],
        }

    # ─────────────────────────────────────────────
    # MAIN AI FUNCTION
    # ─────────────────────────────────────────────
    def generate_suggestions(self, simulation_summary: Dict[str, Any] | None = None) -> Dict[str, Any]:

        # 👉 USE LIVE SIMULATION DATA (IMPORTANT)
        payload = simulation_summary or build_prompt_payload()

        if not self.api_key:
            return self._fallback(payload, "Missing API key")

        # 🔥 SHORT PROMPT (prevents token issue)
        summary = {
            "patients": payload.get("patients"),
            "doctors": payload.get("doctors"),
            "nurses": payload.get("nurses"),
            "wait": payload.get("current_waiting_time"),
            "cost_change": payload.get("cost_change"),
            "status": payload.get("interpretation"),
        }

        prompt = f"""
You are a hospital resource assistant.

Write exactly 3 recommendations.

Use STRICT format:

Title: ...
Explanation: ...
Priority: High/Medium/Low

Title: ...
Explanation: ...
Priority: High/Medium/Low

Title: ...
Explanation: ...
Priority: High/Medium/Low

Data:
{json.dumps(summary)}
"""

        try:
            client = OpenAI(
                api_key=self.api_key,
                base_url=self.base_url,
            )

            response = client.chat.completions.create(
                model=self.model,
                temperature=0.3,
                max_tokens=1000,
                messages=[
                    {"role": "user", "content": prompt}
                ],
            )

            content = response.choices[0].message.content

            if not content:
                raise ValueError("AI returned empty content")

            suggestions = self._parse_text(content)

            if len(suggestions) == 0:
                raise ValueError("No valid suggestions parsed")

            # ensure 3 suggestions
            while len(suggestions) < 3:
                suggestions.append({
                    "title": "Monitor system performance",
                    "explanation": "Continue tracking waiting time and workload.",
                    "priority": "Medium",
                })

            return {
                "source": "ilmu-api",
                "data_summary": payload,
                "suggestions": suggestions[:3],
            }

        except Exception as exc:
            print("[AI SERVICE ERROR]", exc)
            return self._fallback(payload, str(exc))

    # ─────────────────────────────────────────────
    # PARSER (TEXT → JSON SAFE)
    # ─────────────────────────────────────────────
    def _parse_text(self, content: str) -> List[Dict[str, str]]:
        suggestions: List[Dict[str, str]] = []

        blocks = content.strip().split("\n\n")

        for block in blocks:
            item = {
                "title": "",
                "explanation": "",
                "priority": "Medium",
            }

            for line in block.splitlines():
                line = line.strip()

                if line.lower().startswith("title:"):
                    item["title"] = line.split(":", 1)[1].strip()

                elif line.lower().startswith("explanation:"):
                    item["explanation"] = line.split(":", 1)[1].strip()

                elif line.lower().startswith("priority:"):
                    p = line.split(":", 1)[1].strip()
                    if p in ["High", "Medium", "Low"]:
                        item["priority"] = p

            if item["title"] or item["explanation"]:
                if not item["title"]:
                    item["title"] = "Review hospital resources"

                if not item["explanation"]:
                    item["explanation"] = "Monitor workload and adjust resources if needed."

                suggestions.append(item)

        return suggestions