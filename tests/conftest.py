import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest

from config import Settings
from models.common import TokenUsage
from services.llm_client import LLMClient


@pytest.fixture
def settings():
    return Settings(
        openai_api_key="test-key",
        default_model="gpt-4o-mini",
        writing_model="gpt-4o",
        orchestrator_model="gpt-4o",
        max_searches=3,
        max_results_per_search=3,
        max_scrape_urls=5,
        max_follow_up_questions=3,
        max_revisions=1,
        max_tokens_per_session=50000,
    )


@pytest.fixture
def mock_llm_client(settings):
    client = MagicMock(spec=LLMClient)
    client.settings = settings
    client.total_usage = TokenUsage(input_tokens=0, output_tokens=0)

    async def mock_complete_structured(messages, response_model, **kwargs):
        return _build_mock_response(response_model)

    async def mock_complete(messages, **kwargs):
        return {
            "content": "mock response",
            "tool_calls": None,
            "usage": TokenUsage(input_tokens=100, output_tokens=50),
            "model": "gpt-4o-mini",
            "duration_seconds": 0.5,
        }

    client.complete_structured = AsyncMock(side_effect=mock_complete_structured)
    client.complete = AsyncMock(side_effect=mock_complete)
    return client


def _build_mock_response(response_model):
    from models.analysis import AnalysisFindings
    from models.query import ClarificationResult
    from models.report import CritiqueResult, ReportDraft
    from models.search import SearchPlan

    if response_model == ClarificationResult:
        return ClarificationResult(
            needs_clarification=False,
            reasoning="Query is clear and specific",
            questions=[],
        )

    if response_model == SearchPlan:
        from models.search import SearchQuery
        return SearchPlan(
            strategy_summary="Test search strategy",
            searches=[
                SearchQuery(query="test query 1", reason="reason 1", priority=1),
                SearchQuery(query="test query 2", reason="reason 2", priority=2),
            ],
        )

    if response_model == AnalysisFindings:
        return AnalysisFindings(
            key_findings=["Finding 1", "Finding 2"],
            themes=["Theme 1"],
            contradictions=[],
            knowledge_gaps=["Gap 1"],
            source_quality_assessment="Good quality sources",
            source_summaries=[],
        )

    if response_model == ReportDraft:
        return ReportDraft(
            title="Test Report",
            summary="A test summary of findings.",
            markdown="# Test Report\n\nThis is a test report with content.\n\n## Section 1\n\nDetails here.",
            sources_cited=["https://example.com"],
            word_count=500,
        )

    if response_model == CritiqueResult:
        return CritiqueResult(
            accuracy_score=8.0,
            completeness_score=7.5,
            structure_score=8.0,
            clarity_score=8.5,
            citation_score=7.0,
            strengths=["Well structured", "Clear writing"],
            weaknesses=["Could use more sources"],
            suggestions=["Add more citations"],
            needs_revision=False,
        )

    raise ValueError(f"No mock for {response_model}")
