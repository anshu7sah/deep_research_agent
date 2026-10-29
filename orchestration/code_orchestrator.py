import asyncio
import time

from agents.analyst import AnalystAgent
from agents.clarifier import ClarifierAgent
from agents.critic import CriticAgent
from agents.planner import PlannerAgent
from agents.writer import WriterAgent
from guardrails.input_guard import InputGuard
from guardrails.output_guard import OutputGuard
from logging_config import get_logger
from models.query import ResearchQuery
from models.report import FinalReport
from models.session import ResearchSession, SessionStatus
from orchestration.base import BaseOrchestrator
from tools.scrape_tool import ScrapeTool
from tools.search_tool import SearchTool

logger = get_logger("code_orchestrator")


class CodeOrchestrator(BaseOrchestrator):

    async def run(self, session: ResearchSession) -> FinalReport:
        start_time = time.time()

        # --- Step 1: Validate input ---
        await self.emit("status", "Validating query...", status="validating")
        session.status = SessionStatus.VALIDATING

        guard = InputGuard(self.settings, self.llm)
        validation = await guard.validate(session.query.original_query)
        if not validation.is_valid:
            await self.emit("error", validation.violations[0], recoverable=False)
            session.status = SessionStatus.FAILED
            raise ValueError(validation.violations[0])

        # --- Step 2: Clarify query ---
        await self.emit("status", "Analyzing query...", status="clarifying")
        session.status = SessionStatus.CLARIFYING

        query = session.query
        try:
            clarifier = ClarifierAgent(self.llm, self.settings)
            clarification = await clarifier.execute(query=query.original_query)

            if clarification.needs_clarification and clarification.questions:
                questions_data = [
                    {"question": q.question, "purpose": q.purpose}
                    for q in clarification.questions
                ]
                await self.emit(
                    "clarify",
                    "Follow-up questions needed",
                    questions=questions_data,
                )
                session.status = SessionStatus.WAITING_FOR_ANSWERS

                answers = await self.wait_for_clarification()

                if answers:
                    query.clarification_answers = answers
                    context = "\n".join(
                        f"Q: {q}\nA: {a}" for q, a in answers.items()
                    )
                    query.enhanced_query = (
                        f"{query.original_query}\n\nAdditional context:\n{context}"
                    )
        except Exception as e:
            logger.warning("clarification_failed", error=str(e))

        # --- Step 3: Plan searches ---
        await self.emit("status", "Planning research strategy...", status="planning")
        session.status = SessionStatus.PLANNING

        planner = PlannerAgent(self.llm, self.settings)
        search_plan = await planner.execute(
            query=query.effective_query,
            context="\n".join(
                f"Q: {q}\nA: {a}" for q, a in query.clarification_answers.items()
            ),
        )

        await self.emit(
            "status",
            f"Planned {len(search_plan.searches)} searches",
            strategy=search_plan.strategy_summary,
        )

        # --- Step 4: Execute searches ---
        await self.emit(
            "status",
            f"Searching the web ({len(search_plan.searches)} queries)...",
            status="searching",
        )
        session.status = SessionStatus.SEARCHING

        search_tool = SearchTool(
            rate_limit_delay=self.settings.search_rate_limit_delay
        )

        all_results = []
        for i, sq in enumerate(search_plan.searches):
            results = await search_tool.search(
                sq.query, max_results=self.settings.max_results_per_search
            )
            all_results.extend(results)
            await self.emit(
                "progress",
                f"Searched {i + 1}/{len(search_plan.searches)}: {sq.query}",
                current=i + 1,
                total=len(search_plan.searches),
            )

        # --- Step 5: Deduplicate and scrape ---
        await self.emit("status", "Extracting content from sources...", status="scraping")
        session.status = SessionStatus.SCRAPING

        seen_urls = set()
        unique_results = []
        for r in all_results:
            if r.url not in seen_urls:
                seen_urls.add(r.url)
                unique_results.append(r)

        urls_to_scrape = [r.url for r in unique_results[: self.settings.max_scrape_urls]]

        scrape_tool = ScrapeTool()
        semaphore = asyncio.Semaphore(self.settings.scrape_concurrency)

        async def limited_scrape(url: str):
            async with semaphore:
                return await scrape_tool.scrape(url)

        scraped = await asyncio.gather(
            *[limited_scrape(url) for url in urls_to_scrape],
            return_exceptions=True,
        )

        scraped_contents = []
        scraped_urls = []
        for item in scraped:
            if isinstance(item, Exception):
                continue
            if item.success:
                scraped_contents.append(
                    {"url": item.url, "title": item.title, "content": item.content}
                )
                scraped_urls.append(item.url)

        # Fallback: use search snippets if scraping failed
        if not scraped_contents:
            logger.warning("all_scrapes_failed_using_snippets")
            for r in unique_results[:10]:
                scraped_contents.append(
                    {"url": r.url, "title": r.title, "content": r.snippet}
                )
                scraped_urls.append(r.url)

        await self.emit(
            "status",
            f"Extracted content from {len(scraped_contents)} sources",
            num_sources=len(scraped_contents),
        )

        # --- Step 6: Analyze ---
        await self.emit("status", "Analyzing findings...", status="analyzing")
        session.status = SessionStatus.ANALYZING

        analyst = AnalystAgent(self.llm, self.settings)
        findings = await analyst.execute(
            query=query.effective_query, scraped_contents=scraped_contents
        )

        await self.emit("status", f"Found {len(findings.key_findings)} key findings")

        # --- Step 7: Write report ---
        await self.emit("status", "Writing report...", status="writing")
        session.status = SessionStatus.WRITING

        writer = WriterAgent(self.llm, self.settings)
        draft = await writer.execute(
            query=query.effective_query, findings=findings.model_dump()
        )

        # --- Step 8: Critique and revise loop ---
        critique = None
        if not self.budget.is_budget_low:
            critic = CriticAgent(self.llm, self.settings)

            for revision_num in range(self.settings.max_revisions):
                await self.emit(
                    "status",
                    f"Reviewing report (round {revision_num + 1})...",
                    status="critiquing",
                )
                session.status = SessionStatus.CRITIQUING

                critique = await critic.execute(
                    query=query.effective_query, report_markdown=draft.markdown
                )

                await self.emit(
                    "status",
                    f"Review score: {critique.overall_score:.1f}/10",
                    score=critique.overall_score,
                )

                if not critique.needs_revision:
                    break

                await self.emit("status", "Revising report...", status="revising")
                session.status = SessionStatus.REVISING
                draft = await writer.revise(draft.markdown, critique.model_dump())

        # --- Step 9: Output validation ---
        output_guard = OutputGuard(self.settings)
        output_validation = output_guard.validate(draft.markdown, scraped_urls)
        if output_validation.violations:
            logger.warning("output_issues", violations=output_validation.violations)

        # --- Step 10: Build final report ---
        duration = time.time() - start_time

        report = FinalReport(
            title=draft.title,
            summary=draft.summary,
            markdown=draft.markdown,
            sources=draft.sources_cited or scraped_urls,
            critique_score=critique.overall_score if critique else None,
            total_tokens_used=self.llm.total_usage.total,
            total_duration_seconds=round(duration, 2),
            num_sources_scraped=len(scraped_contents),
            orchestration_mode="code",
        )

        session.report = report
        session.status = SessionStatus.COMPLETED

        await self.emit("complete", "Research complete", report=report.model_dump())

        return report
