import pytest
from pydantic import ValidationError

from models.common import TokenUsage, ValidationResult
from models.query import ClarificationResult, FollowUpQuestion, ResearchQuery
from models.report import CritiqueResult, FinalReport, ReportDraft
from models.search import ScrapedContent, SearchPlan, SearchQuery, SearchResult
from models.session import SessionStatus


def test_token_usage_total():
    usage = TokenUsage(input_tokens=100, output_tokens=50)
    assert usage.total == 150


def test_research_query_effective_query_default():
    q = ResearchQuery(original_query="test query")
    assert q.effective_query == "test query"


def test_research_query_effective_query_enhanced():
    q = ResearchQuery(original_query="test", enhanced_query="enhanced test")
    assert q.effective_query == "enhanced test"


def test_clarification_result_no_questions():
    result = ClarificationResult(
        needs_clarification=False, reasoning="Clear", questions=[]
    )
    assert not result.needs_clarification
    assert result.questions == []


def test_clarification_result_with_questions():
    result = ClarificationResult(
        needs_clarification=True,
        reasoning="Ambiguous",
        questions=[FollowUpQuestion(question="Which one?", purpose="Clarity")],
    )
    assert len(result.questions) == 1


def test_search_query_priority_validation():
    sq = SearchQuery(query="test", reason="reason", priority=1)
    assert sq.priority == 1

    with pytest.raises(ValidationError):
        SearchQuery(query="test", reason="reason", priority=0)

    with pytest.raises(ValidationError):
        SearchQuery(query="test", reason="reason", priority=4)


def test_critique_overall_score():
    critique = CritiqueResult(
        accuracy_score=8.0,
        completeness_score=7.0,
        structure_score=9.0,
        clarity_score=8.0,
        citation_score=8.0,
        strengths=["Good"],
        weaknesses=["Bad"],
        suggestions=["Fix"],
        needs_revision=False,
    )
    assert critique.overall_score == 8.0


def test_session_status_values():
    assert SessionStatus.CREATED == "created"
    assert SessionStatus.COMPLETED == "completed"
    assert SessionStatus.FAILED == "failed"


def test_scraped_content_success():
    sc = ScrapedContent(
        url="https://example.com",
        title="Test",
        content="Content here",
        word_count=2,
        scrape_method="trafilatura",
        success=True,
    )
    assert sc.success
    assert sc.error is None


def test_scraped_content_failure():
    sc = ScrapedContent(
        url="https://example.com",
        title="",
        content="",
        word_count=0,
        scrape_method="failed",
        success=False,
        error="Connection timeout",
    )
    assert not sc.success
    assert sc.error == "Connection timeout"
