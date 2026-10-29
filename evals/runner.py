import asyncio
import json
import time
from pathlib import Path

from pydantic import BaseModel

from config import Settings
from evals.judges import judge_search_relevance, judge_topic_coverage
from evals.metrics import (
    citation_accuracy,
    report_quality_score,
    scrape_success_rate,
    token_efficiency,
    topic_coverage_from_judgement,
)
from logging_config import get_logger, setup_logging
from services.llm_client import LLMClient

logger = get_logger("eval_runner")


class EvalCase(BaseModel):
    id: str
    query: str
    expected_topics: list[str]
    expected_min_sources: int = 3
    max_allowed_time_seconds: int = 120
    difficulty: str = "medium"


class EvalResult(BaseModel):
    case_id: str
    passed: bool
    metrics: dict[str, float]
    duration_seconds: float
    error: str | None = None


class EvalRunner:

    def __init__(self, settings: Settings):
        self.settings = settings
        self.llm = LLMClient(settings)

    async def run_case(self, case: EvalCase, mode: str) -> EvalResult:
        from api.session_store import SessionStore
        from orchestration import get_orchestrator

        start = time.time()
        store = SessionStore()
        session_id = store.create(case.query, mode)
        session = store.get(session_id)
        event_queue = store.get_event_queue(session_id)

        orchestrator = get_orchestrator(
            mode=mode,
            llm_client=self.llm,
            settings=self.settings,
            event_queue=event_queue,
        )

        try:
            report = await orchestrator.run(session)
            duration = time.time() - start

            metrics = {
                "report_quality": report_quality_score({})
                if not report.critique_score
                else report.critique_score / 10.0,
                "token_efficiency": token_efficiency(
                    report.total_tokens_used, self.settings.max_tokens_per_session
                ),
            }

            passed = all(v >= 0.6 for v in metrics.values())
            return EvalResult(
                case_id=case.id,
                passed=passed,
                metrics=metrics,
                duration_seconds=round(duration, 2),
            )

        except Exception as e:
            return EvalResult(
                case_id=case.id,
                passed=False,
                metrics={},
                duration_seconds=round(time.time() - start, 2),
                error=str(e),
            )

    async def run_all(self, mode: str, cases_path: str | None = None) -> list[EvalResult]:
        path = cases_path or str(
            Path(__file__).parent / "datasets" / "research_queries.json"
        )

        with open(path) as f:
            raw_cases = json.load(f)

        cases = [EvalCase(**c) for c in raw_cases]
        results = []

        for case in cases:
            logger.info("running_eval", case_id=case.id, mode=mode)
            result = await self.run_case(case, mode)
            results.append(result)
            status = "PASS" if result.passed else "FAIL"
            logger.info(
                "eval_complete",
                case_id=case.id,
                status=status,
                duration=result.duration_seconds,
            )

        passed = sum(1 for r in results if r.passed)
        logger.info("eval_summary", total=len(results), passed=passed, failed=len(results) - passed)

        return results
