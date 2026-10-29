import asyncio
import json
import time

from config import Settings
from guardrails.input_guard import InputGuard
from guardrails.output_guard import OutputGuard
from logging_config import get_logger
from models.analysis import AnalysisFindings
from models.query import ClarificationResult
from models.report import CritiqueResult, FinalReport, ReportDraft
from models.search import SearchPlan
from models.session import ResearchSession, SessionStatus
from orchestration.base import BaseOrchestrator
from tools.scrape_tool import ScrapeTool
from tools.search_tool import SearchTool
from tools.tool_registry import ToolRegistry

logger = get_logger("llm_orchestrator")

MAX_ITERATIONS = 25
MAX_CONSECUTIVE_FAILURES = 3
MAX_SEARCH_CALLS = 10
MAX_SCRAPE_CALLS = 15

ORCHESTRATOR_SYSTEM_PROMPT = """You are a deep research orchestrator. Your mission is to conduct \
thorough research on the user's query and produce a comprehensive report.

You have these tools:

- clarify_query: Assess if the query needs follow-up questions. Call this FIRST.
- plan_searches: Create a search strategy with multiple search queries.
- search_web: Search DuckDuckGo for a single query. Returns titles, URLs, snippets.
- scrape_url: Extract full content from a web page URL. Use on promising search results.
- analyze_content: Synthesize findings from all scraped content into structured analysis.
- write_report: Write a comprehensive markdown research report from analysis findings.
- critique_report: Review report quality and score it on 5 dimensions.
- revise_report: Improve a report based on critique feedback.
- report_status: Send a status update message to the user's UI.

WORKFLOW GUIDANCE (adapt as you see fit):
1. Start by calling report_status to inform the user you're beginning
2. Assess whether the query needs clarification (clarify_query)
3. Plan your search strategy (plan_searches)
4. Execute searches (search_web for each planned query)
5. Scrape the most promising URLs from search results (scrape_url)
6. Analyze all collected content (analyze_content)
7. Write a comprehensive report (write_report)
8. Critique the report (critique_report); revise if score is below 7/10
9. After you're satisfied with the report, return the final markdown as your last message \
(with NO tool call). This signals the research is complete.

RULES:
- Always call report_status before each major phase so the user sees progress
- You may search again after analysis if you discover knowledge gaps
- You MUST eventually produce a final report — do not loop indefinitely
- If a tool fails, try an alternative approach rather than stopping
- Keep the report comprehensive with inline [Source Title](URL) citations"""


class LLMOrchestrator(BaseOrchestrator):

    async def run(self, session: ResearchSession) -> FinalReport:
        start_time = time.time()

        # --- Validate input ---
        guard = InputGuard(self.settings, self.llm)
        validation = await guard.validate(session.query.original_query)
        if not validation.is_valid:
            await self.emit("error", validation.violations[0], recoverable=False)
            session.status = SessionStatus.FAILED
            raise ValueError(validation.violations[0])

        # --- Set up tools ---
        registry = self._build_tool_registry(session)

        # --- Run tool-calling loop ---
        messages = [
            {"role": "system", "content": ORCHESTRATOR_SYSTEM_PROMPT},
            {"role": "user", "content": f"Research this topic: {session.query.original_query}"},
        ]

        session.status = SessionStatus.PLANNING
        await self.emit("status", "LLM orchestrator starting research...", status="planning")

        consecutive_failures = 0
        search_call_count = 0
        scrape_call_count = 0
        last_report_markdown = None

        for iteration in range(MAX_ITERATIONS):
            if self.budget.is_exhausted:
                messages.append({
                    "role": "system",
                    "content": "TOKEN BUDGET EXHAUSTED. Return your final report NOW as a plain message.",
                })

            if self.budget.is_budget_low and not self.budget.is_exhausted:
                messages.append({
                    "role": "system",
                    "content": "Token budget is running low. Please finalize your report soon.",
                })

            response = await self.llm.complete(
                messages=messages,
                model=self.settings.orchestrator_model,
                tools=registry.get_openai_tools(),
                temperature=0.7,
            )

            self.budget.record(response["usage"])

            # If no tool calls, the LLM is done — this is the final response
            if not response["tool_calls"]:
                final_content = response["content"] or ""
                if final_content:
                    last_report_markdown = final_content
                break

            # Process each tool call
            messages.append({
                "role": "assistant",
                "content": response["content"],
                "tool_calls": response["tool_calls"],
            })

            for tool_call in response["tool_calls"]:
                func_name = tool_call["function"]["name"]
                try:
                    arguments = json.loads(tool_call["function"]["arguments"])
                except json.JSONDecodeError:
                    arguments = {}

                # Enforce per-tool call limits
                if func_name == "search_web":
                    search_call_count += 1
                    if search_call_count > MAX_SEARCH_CALLS:
                        result = json.dumps({"error": "Search call limit reached"})
                        messages.append({
                            "role": "tool",
                            "tool_call_id": tool_call["id"],
                            "content": result,
                        })
                        continue

                if func_name == "scrape_url":
                    scrape_call_count += 1
                    if scrape_call_count > MAX_SCRAPE_CALLS:
                        result = json.dumps({"error": "Scrape call limit reached"})
                        messages.append({
                            "role": "tool",
                            "tool_call_id": tool_call["id"],
                            "content": result,
                        })
                        continue

                # Execute the tool
                try:
                    result = await registry.execute(func_name, arguments)
                    consecutive_failures = 0

                    # Track report content for extraction
                    if func_name == "write_report":
                        try:
                            parsed = json.loads(result)
                            last_report_markdown = parsed.get("markdown", result)
                        except (json.JSONDecodeError, AttributeError):
                            pass

                except Exception as e:
                    result = json.dumps({"error": str(e)})
                    consecutive_failures += 1
                    logger.warning(
                        "tool_failed",
                        tool=func_name,
                        error=str(e),
                        consecutive=consecutive_failures,
                    )

                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call["id"],
                    "content": result,
                })

            if consecutive_failures >= MAX_CONSECUTIVE_FAILURES:
                messages.append({
                    "role": "system",
                    "content": "Multiple tools have failed. Please finalize with what you have.",
                })
                consecutive_failures = 0

            logger.info("iteration_complete", iteration=iteration + 1)

        # --- Build final report ---
        duration = time.time() - start_time
        markdown = last_report_markdown or "Research could not be completed."

        output_guard = OutputGuard(self.settings)
        output_guard.validate(markdown, [])

        report = FinalReport(
            title="Research Report",
            summary="",
            markdown=markdown,
            sources=[],
            total_tokens_used=self.llm.total_usage.total,
            total_duration_seconds=round(duration, 2),
            orchestration_mode="llm",
        )

        session.report = report
        session.status = SessionStatus.COMPLETED
        await self.emit("complete", "Research complete", report=report.model_dump())

        return report

    def _build_tool_registry(self, session: ResearchSession) -> ToolRegistry:
        registry = ToolRegistry()
        search_tool = SearchTool(rate_limit_delay=self.settings.search_rate_limit_delay)
        scrape_tool = ScrapeTool()

        # --- clarify_query ---
        async def clarify_query(query: str) -> str:
            from agents.clarifier import ClarifierAgent
            agent = ClarifierAgent(self.llm, self.settings)
            result = await agent.execute(query=query)
            if result.needs_clarification and result.questions:
                questions_data = [
                    {"question": q.question, "purpose": q.purpose}
                    for q in result.questions
                ]
                await self.emit("clarify", "Follow-up questions needed", questions=questions_data)
                session.status = SessionStatus.WAITING_FOR_ANSWERS
                answers = await self.wait_for_clarification()
                if answers:
                    session.query.clarification_answers = answers
                    context = "\n".join(f"Q: {q}\nA: {a}" for q, a in answers.items())
                    session.query.enhanced_query = f"{query}\n\nAdditional context:\n{context}"
                    return json.dumps({"clarified": True, "enhanced_query": session.query.enhanced_query})
            return json.dumps({"clarified": False, "reasoning": result.reasoning})

        registry.register(
            clarify_query,
            "Assess if the query needs follow-up questions from the user",
            {
                "type": "object",
                "properties": {"query": {"type": "string", "description": "The research query"}},
                "required": ["query"],
            },
        )

        # --- plan_searches ---
        async def plan_searches(query: str) -> str:
            from agents.planner import PlannerAgent
            agent = PlannerAgent(self.llm, self.settings)
            result = await agent.execute(query=query)
            await self.emit("status", f"Planned {len(result.searches)} searches", status="planning")
            return result.model_dump_json()

        registry.register(
            plan_searches,
            "Create a search strategy with multiple search queries",
            {
                "type": "object",
                "properties": {"query": {"type": "string", "description": "The research query"}},
                "required": ["query"],
            },
        )

        # --- search_web ---
        async def search_web(query: str) -> str:
            results = await search_tool.search(query, max_results=self.settings.max_results_per_search)
            await self.emit("progress", f"Searched: {query}", num_results=len(results))
            return json.dumps([r.model_dump() for r in results], default=str)

        registry.register(
            search_web,
            "Search DuckDuckGo for a query and return titles, URLs, and snippets",
            {
                "type": "object",
                "properties": {"query": {"type": "string", "description": "Search query"}},
                "required": ["query"],
            },
        )

        # --- scrape_url ---
        async def scrape_url(url: str) -> str:
            result = await scrape_tool.scrape(url)
            if result.success:
                truncated = result.content[:5000]
                return json.dumps({"url": url, "title": result.title, "content": truncated})
            return json.dumps({"url": url, "error": result.error or "Scraping failed"})

        registry.register(
            scrape_url,
            "Extract full text content from a web page URL",
            {
                "type": "object",
                "properties": {"url": {"type": "string", "description": "URL to scrape"}},
                "required": ["url"],
            },
        )

        # --- analyze_content ---
        async def analyze_content(query: str, contents: list[dict]) -> str:
            from agents.analyst import AnalystAgent
            agent = AnalystAgent(self.llm, self.settings)
            result = await agent.execute(query=query, scraped_contents=contents)
            await self.emit("status", f"Analysis complete: {len(result.key_findings)} findings", status="analyzing")
            return result.model_dump_json()

        registry.register(
            analyze_content,
            "Synthesize findings from scraped content into structured analysis",
            {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "The research query"},
                    "contents": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "url": {"type": "string"},
                                "title": {"type": "string"},
                                "content": {"type": "string"},
                            },
                        },
                        "description": "Scraped content from web pages",
                    },
                },
                "required": ["query", "contents"],
            },
        )

        # --- write_report ---
        async def write_report(query: str, findings: dict) -> str:
            from agents.writer import WriterAgent
            agent = WriterAgent(self.llm, self.settings)
            result = await agent.execute(query=query, findings=findings)
            await self.emit("status", "Report draft complete", status="writing")
            return result.model_dump_json()

        registry.register(
            write_report,
            "Write a comprehensive markdown research report from analysis findings",
            {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "The research query"},
                    "findings": {"type": "object", "description": "Analysis findings"},
                },
                "required": ["query", "findings"],
            },
        )

        # --- critique_report ---
        async def critique_report(query: str, report_markdown: str) -> str:
            from agents.critic import CriticAgent
            agent = CriticAgent(self.llm, self.settings)
            result = await agent.execute(query=query, report_markdown=report_markdown)
            await self.emit("status", f"Critique score: {result.overall_score:.1f}/10", status="critiquing")
            return result.model_dump_json()

        registry.register(
            critique_report,
            "Review report quality and score it on 5 dimensions (0-10 each)",
            {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "The research query"},
                    "report_markdown": {"type": "string", "description": "The report to review"},
                },
                "required": ["query", "report_markdown"],
            },
        )

        # --- revise_report ---
        async def revise_report(draft_markdown: str, critique: dict) -> str:
            from agents.writer import WriterAgent
            agent = WriterAgent(self.llm, self.settings)
            result = await agent.revise(draft_markdown, critique)
            await self.emit("status", "Report revised", status="revising")
            return result.model_dump_json()

        registry.register(
            revise_report,
            "Improve a report based on critique feedback",
            {
                "type": "object",
                "properties": {
                    "draft_markdown": {"type": "string", "description": "Current report draft"},
                    "critique": {"type": "object", "description": "Critique result with scores and suggestions"},
                },
                "required": ["draft_markdown", "critique"],
            },
        )

        # --- report_status ---
        async def report_status(message: str) -> str:
            await self.emit("status", message)
            return json.dumps({"status": "sent"})

        registry.register(
            report_status,
            "Send a status update message to the user's UI",
            {
                "type": "object",
                "properties": {"message": {"type": "string", "description": "Status message to display"}},
                "required": ["message"],
            },
        )

        return registry
