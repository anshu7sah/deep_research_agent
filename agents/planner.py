from agents.base import BaseAgent
from models.search import SearchPlan

SYSTEM_PROMPT = """You are a research planning specialist. Given a research query \
(possibly with additional context from clarification), produce a comprehensive search strategy.

For each search query you generate:
1. Write a specific, well-formed search string (as you would type into a search engine)
2. Explain why this particular search is important for answering the question
3. Assign a priority: 1=critical (must have), 2=important, 3=supplementary

Strategy guidelines:
- Lead with 1-2 broad overview queries to establish baseline understanding
- Follow with specific sub-topic queries for depth
- Include at least one query seeking contrasting or critical viewpoints
- Include a query targeting recent developments (add current year if relevant)
- Vary query phrasing to maximize result diversity

Generate exactly {num_searches} search queries. Order them by priority."""


class PlannerAgent(BaseAgent):
    name = "Planner"
    output_type = SearchPlan

    def _build_messages(self, **kwargs) -> list[dict]:
        query: str = kwargs["query"]
        context: str = kwargs.get("context", "")

        user_content = f"Research query: {query}"
        if context:
            user_content += f"\n\nAdditional context from user clarification:\n{context}"

        return [
            {
                "role": "system",
                "content": SYSTEM_PROMPT.format(num_searches=self.settings.max_searches),
            },
            {"role": "user", "content": user_content},
        ]
