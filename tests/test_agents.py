import pytest

from agents.clarifier import ClarifierAgent
from agents.critic import CriticAgent
from agents.planner import PlannerAgent
from agents.writer import WriterAgent
from models.query import ClarificationResult
from models.report import CritiqueResult, ReportDraft
from models.search import SearchPlan


@pytest.mark.asyncio
async def test_clarifier_agent(mock_llm_client, settings):
    agent = ClarifierAgent(mock_llm_client, settings)
    result = await agent.execute(query="Compare React vs Vue.js")
    assert isinstance(result, ClarificationResult)
    assert not result.needs_clarification


@pytest.mark.asyncio
async def test_planner_agent(mock_llm_client, settings):
    agent = PlannerAgent(mock_llm_client, settings)
    result = await agent.execute(query="Test query", context="")
    assert isinstance(result, SearchPlan)
    assert len(result.searches) > 0


@pytest.mark.asyncio
async def test_writer_agent(mock_llm_client, settings):
    agent = WriterAgent(mock_llm_client, settings)
    result = await agent.execute(
        query="Test query",
        findings={
            "key_findings": ["Finding 1"],
            "themes": ["Theme 1"],
            "contradictions": [],
            "knowledge_gaps": [],
            "source_quality_assessment": "Good",
            "source_summaries": [],
        },
    )
    assert isinstance(result, ReportDraft)
    assert result.title == "Test Report"


@pytest.mark.asyncio
async def test_critic_agent(mock_llm_client, settings):
    agent = CriticAgent(mock_llm_client, settings)
    result = await agent.execute(
        query="Test query", report_markdown="# Test\n\nContent here."
    )
    assert isinstance(result, CritiqueResult)
    assert not result.needs_revision
    assert result.overall_score > 0


@pytest.mark.asyncio
async def test_writer_revision(mock_llm_client, settings):
    agent = WriterAgent(mock_llm_client, settings)
    result = await agent.revise(
        draft_markdown="# Old Report\n\nOld content.",
        critique={
            "accuracy_score": 6,
            "completeness_score": 5,
            "structure_score": 7,
            "clarity_score": 6,
            "citation_score": 5,
            "weaknesses": ["Too short"],
            "suggestions": ["Add more detail"],
        },
    )
    assert isinstance(result, ReportDraft)
