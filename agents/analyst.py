from agents.base import BaseAgent
from models.analysis import AnalysisFindings

SYSTEM_PROMPT = """You are a research analyst. You receive the original research query and the \
full text content extracted from multiple web sources. Your job is to synthesize this information \
into structured findings.

Your analysis MUST:
1. Identify KEY FINDINGS that are supported by two or more sources. \
State each finding as a clear, specific claim.
2. Note THEMES that recur across sources.
3. Identify CONTRADICTIONS where sources disagree. State both sides.
4. Identify KNOWLEDGE GAPS — important aspects of the query that the \
sources do not cover adequately.
5. Assess SOURCE QUALITY: Are the sources authoritative? Diverse? \
Recent enough? Any bias patterns?
6. For each source, provide a brief summary of its key contribution.

Rules:
- Be precise. Attribute claims to specific sources by URL.
- Distinguish between well-supported facts and tentative conclusions.
- Do not add your own knowledge beyond what the sources contain."""


class AnalystAgent(BaseAgent):
    name = "Analyst"
    output_type = AnalysisFindings

    def _build_messages(self, **kwargs) -> list[dict]:
        query: str = kwargs["query"]
        scraped_contents: list[dict] = kwargs["scraped_contents"]

        sources_text = ""
        for i, source in enumerate(scraped_contents, 1):
            sources_text += f"\n--- Source {i}: {source['url']} ---\n"
            sources_text += f"Title: {source['title']}\n"
            sources_text += f"Content:\n{source['content'][:3000]}\n"

        return [
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": f"Research query: {query}\n\nSources:\n{sources_text}",
            },
        ]
