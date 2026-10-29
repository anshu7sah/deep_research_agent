from pydantic import BaseModel, Field


class SourceSummary(BaseModel):
    url: str
    title: str
    key_points: list[str]


class AnalysisFindings(BaseModel):
    key_findings: list[str] = Field(
        description="Main findings supported by the sources"
    )
    themes: list[str] = Field(
        description="Recurring themes across sources"
    )
    contradictions: list[str] = Field(
        description="Points where sources disagree"
    )
    knowledge_gaps: list[str] = Field(
        description="Important aspects not covered by the sources"
    )
    source_quality_assessment: str = Field(
        description="Overall assessment of source reliability and diversity"
    )
    source_summaries: list[SourceSummary] = Field(default_factory=list)
