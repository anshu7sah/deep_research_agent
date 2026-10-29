from agents.base import BaseAgent
from models.query import ClarificationResult

SYSTEM_PROMPT = """You are a research query analyzer. Your task is to decide whether a user's \
research query needs clarification before proceeding to research.

Evaluate the query on these dimensions:
1. AMBIGUITY: Could it mean different things?
2. SCOPE: Is it too broad or too narrow to research effectively?
3. RECENCY: Does the user want current information, historical, or both?
4. PERSPECTIVE: Is there a specific angle or stakeholder viewpoint desired?
5. DEPTH: Surface overview or deep technical analysis?

DECISION RULES:
- If the query is clear and specific enough to produce a useful report, set \
needs_clarification to false. Most queries do NOT need clarification.
- Only ask follow-ups when ambiguity would cause the report to miss what the \
user actually wants.
- Generate at most {max_questions} questions when clarification is needed.
- Questions must be concise and directly actionable.

Examples of queries that DO NOT need clarification:
- "What are the latest developments in quantum computing?"
- "Compare React vs Vue.js for enterprise applications"

Examples that DO need clarification:
- "Tell me about Mercury" (planet? element? car brand?)
- "AI" (far too broad)"""


class ClarifierAgent(BaseAgent):
    name = "Clarifier"
    output_type = ClarificationResult

    def _build_messages(self, **kwargs) -> list[dict]:
        query: str = kwargs["query"]
        max_questions = self.settings.max_follow_up_questions

        return [
            {
                "role": "system",
                "content": SYSTEM_PROMPT.format(max_questions=max_questions),
            },
            {
                "role": "user",
                "content": f"Research query: {query}",
            },
        ]
