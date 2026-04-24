from __future__ import annotations

import json
from typing import Any, Dict, List

from openai import OpenAI

from analytics import build_prompt_payload


SYSTEM_PROMPT = """
You are an assistant for a Smart Hospital Resources Management dashboard.
Return STRICT JSON only with this shape:
{
  "suggestions": [
    {
      "title": "short action sentence",
      "explanation": "1-2 sentences explaining why",
      "priority": "High|Medium|Low"
    }
  ]
}
Rules:
- Give exactly 3 suggestions.
- Focus only on feature #1: AI Recommendations.
- Make the recommendations practical for hospital resource management.
- Base your answer only on the provided data summary.
- Keep the title under 60 characters.
- Keep explanations easy to understand.
""".strip()


class AIService:
    def __init__(self, api_key: str, base_url: str, model: str) -> None:
        self.api_key = api_key
        self.base_url = base_url
        self.model = model

    def generate_suggestions(self) -> Dict[str, Any]:
        payload = build_prompt_payload()

        if not self.api_key:
            return {
                'source': 'rule-based fallback',
                'data_summary': payload,
                'suggestions': payload['rule_based_suggestions'],
            }

        try:
            client = OpenAI(api_key=self.api_key, base_url=self.base_url)
            response = client.chat.completions.create(
                model=self.model,
                response_format={'type': 'json_object'},
                temperature=0.3,
                messages=[
                    {'role': 'system', 'content': SYSTEM_PROMPT},
                    {
                        'role': 'user',
                        'content': (
                            'Use this hospital summary to generate 3 smart recommendations:\n'
                            + json.dumps(payload, ensure_ascii=False)
                        ),
                    },
                ],
            )
            content = response.choices[0].message.content or '{}'
            parsed = json.loads(content)
            suggestions = parsed.get('suggestions', [])

            if not isinstance(suggestions, list) or len(suggestions) == 0:
                raise ValueError('AI returned invalid suggestions payload.')

            return {
                'source': 'ilmu-api',
                'data_summary': payload,
                'suggestions': suggestions[:3],
            }
        except Exception as exc:  # noqa: BLE001
            return {
                'source': 'rule-based fallback',
                'error': str(exc),
                'data_summary': payload,
                'suggestions': payload['rule_based_suggestions'],
            }
