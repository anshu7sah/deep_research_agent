from agents.base import BaseAgent
from models.report import ReportDraft

WRITE_PROMPT = """You are a senior research writer. Given structured analysis findings and the \
original query, produce a comprehensive, well-structured markdown report.

REPORT STRUCTURE:
1. Title: descriptive, specific to the research topic
2. Executive Summary: 2-3 sentences capturing the main takeaway
3. Body Sections: 3-6 sections with descriptive headings, organized by theme
4. Each section must cite sources inline using [Source Title](URL) format
5. Conclusion: Key takeaways and implications
6. Sources: Numbered list of all sources cited

QUALITY STANDARDS:
- Minimum 1500 words
- Every factual claim must have an inline citation
- Balanced coverage — do not over-represent one source
- Professional, accessible tone (intelligent layperson audience)
- Use markdown formatting: headers, bold, lists, blockquotes where appropriate
- Address knowledge gaps honestly rather than speculating"""

REVISE_PROMPT = """You are revising a research report based on critique feedback. You receive:
1. The current draft (markdown)
2. A structured critique with scores and specific suggestions

Address each suggestion from the critique. Preserve what the critique identified as strengths. \
Return the complete revised report."""


class WriterAgent(BaseAgent):
    name = "Writer"
    output_type = ReportDraft

    @property
    def _model(self) -> str:
        return self.settings.writing_model

    def _build_messages(self, **kwargs) -> list[dict]:
        query: str = kwargs["query"]
        findings: dict = kwargs["findings"]

        return [
            {"role": "system", "content": WRITE_PROMPT},
            {
                "role": "user",
                "content": (
                    f"Research query: {query}\n\n"
                    f"Analysis findings:\n"
                    f"Key findings: {findings.get('key_findings', [])}\n"
                    f"Themes: {findings.get('themes', [])}\n"
                    f"Contradictions: {findings.get('contradictions', [])}\n"
                    f"Knowledge gaps: {findings.get('knowledge_gaps', [])}\n"
                    f"Source quality: {findings.get('source_quality_assessment', '')}\n"
                    f"Source summaries: {findings.get('source_summaries', [])}"
                ),
            },
        ]

    async def execute(self, **kwargs) -> ReportDraft:
        record_model = self.model
        self.model = self._model
        try:
            return await super().execute(**kwargs)
        finally:
            self.model = record_model

    def _build_revision_messages(self, draft_markdown: str, critique: dict) -> list[dict]:
        return [
            {"role": "system", "content": REVISE_PROMPT},
            {
                "role": "user",
                "content": (
                    f"Current draft:\n{draft_markdown}\n\n"
                    f"Critique scores:\n"
                    f"- Accuracy: {critique.get('accuracy_score', 0)}/10\n"
                    f"- Completeness: {critique.get('completeness_score', 0)}/10\n"
                    f"- Structure: {critique.get('structure_score', 0)}/10\n"
                    f"- Clarity: {critique.get('clarity_score', 0)}/10\n"
                    f"- Citations: {critique.get('citation_score', 0)}/10\n\n"
                    f"Weaknesses: {critique.get('weaknesses', [])}\n"
                    f"Suggestions: {critique.get('suggestions', [])}"
                ),
            },
        ]

    async def revise(self, draft_markdown: str, critique: dict) -> ReportDraft:
        messages = self._build_revision_messages(draft_markdown, critique)
        return await self.llm.complete_structured(
            messages=messages,
            response_model=ReportDraft,
            model=self._model,
        )
