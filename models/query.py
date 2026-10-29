from pydantic import BaseModel, Field


class FollowUpQuestion(BaseModel):
    question: str = Field(description="The question to ask the user")
    purpose: str = Field(description="Why this question improves the research")


class ClarificationResult(BaseModel):
    needs_clarification: bool = Field(
        description="Whether the query would benefit from follow-up questions"
    )
    reasoning: str = Field(
        description="Explanation of why clarification is or is not needed"
    )
    questions: list[FollowUpQuestion] = Field(
        default_factory=list,
        description="Follow-up questions (empty if needs_clarification is false)",
    )


class ResearchQuery(BaseModel):
    original_query: str
    clarification_answers: dict[str, str] = Field(default_factory=dict)
    enhanced_query: str = Field(default="")

    @property
    def effective_query(self) -> str:
        return self.enhanced_query or self.original_query
