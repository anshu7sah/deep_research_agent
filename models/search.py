from pydantic import BaseModel, Field


class SearchQuery(BaseModel):
    query: str = Field(description="The exact search string to submit")
    reason: str = Field(description="Why this search matters for the research")
    priority: int = Field(
        default=1, ge=1, le=3,
        description="1=critical, 2=important, 3=supplementary",
    )


class SearchPlan(BaseModel):
    strategy_summary: str = Field(
        description="Brief explanation of the overall search approach"
    )
    searches: list[SearchQuery] = Field(
        description="Ordered list of searches to perform"
    )


class SearchResult(BaseModel):
    query: str
    title: str
    url: str
    snippet: str
    position: int


class ScrapedContent(BaseModel):
    url: str
    title: str
    content: str
    word_count: int
    scrape_method: str
    success: bool
    error: str | None = None
