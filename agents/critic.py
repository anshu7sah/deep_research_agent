from agents.base import BaseAgent
from models.report import CritiqueResult

SYSTEM_PROMPT = """You are a research report quality reviewer. You receive a draft report and \
the original query. Evaluate the report on five dimensions, each scored 0-10:

1. ACCURACY (0-10): Are claims properly supported by cited sources? \
Look for unsupported claims, exaggerations, or misrepresentations.
2. COMPLETENESS (0-10): Does the report thoroughly address the query? \
Are there obvious gaps or under-explored areas?
3. STRUCTURE (0-10): Is it logically organized? Do sections flow naturally? \
Are headings descriptive and hierarchy correct?
4. CLARITY (0-10): Is the writing clear, concise, and accessible? \
Any jargon without explanation? Ambiguous passages?
5. CITATIONS (0-10): Are sources properly and consistently cited? \
Sufficient number of sources? Any claims without citations?

Then provide:
- 2-4 specific STRENGTHS
- 2-4 specific WEAKNESSES with actionable suggestions for improvement
- Set needs_revision=true if the overall average score is below {threshold}

Be constructive but honest. Focus on substance, not style preferences."""


class CriticAgent(BaseAgent):
    name = "Critic"
    output_type = CritiqueResult

    def _build_messages(self, **kwargs) -> list[dict]:
        query: str = kwargs["query"]
        report_markdown: str = kwargs["report_markdown"]

        return [
            {
                "role": "system",
                "content": SYSTEM_PROMPT.format(
                    threshold=self.settings.revision_threshold
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Original research query: {query}\n\n"
                    f"Report to review:\n{report_markdown}"
                ),
            },
        ]
