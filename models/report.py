from pydantic import BaseModel, Field


class ReportDraft(BaseModel):
    title: str
    summary: str = Field(description="2-3 sentence executive summary")
    markdown: str = Field(description="Full report in markdown format")
    sources_cited: list[str] = Field(default_factory=list)
    word_count: int = 0


class CritiqueResult(BaseModel):
    accuracy_score: float = Field(ge=0, le=10)
    completeness_score: float = Field(ge=0, le=10)
    structure_score: float = Field(ge=0, le=10)
    clarity_score: float = Field(ge=0, le=10)
    citation_score: float = Field(ge=0, le=10)
    strengths: list[str]
    weaknesses: list[str]
    suggestions: list[str]
    needs_revision: bool

    @property
    def overall_score(self) -> float:
        scores = [
            self.accuracy_score,
            self.completeness_score,
            self.structure_score,
            self.clarity_score,
            self.citation_score,
        ]
        return sum(scores) / len(scores)


class FinalReport(BaseModel):
    title: str
    summary: str
    markdown: str
    sources: list[str]
    critique_score: float | None = None
    total_tokens_used: int = 0
    total_duration_seconds: float = 0.0
    num_sources_scraped: int = 0
    orchestration_mode: str = ""
