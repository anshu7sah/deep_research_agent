from pydantic import BaseModel, Field


class TokenUsage(BaseModel):
    input_tokens: int = 0
    output_tokens: int = 0

    @property
    def total(self) -> int:
        return self.input_tokens + self.output_tokens


class LLMResponse(BaseModel):
    content: str | None = None
    tool_calls: list[dict] | None = None
    usage: TokenUsage
    model: str
    duration_seconds: float


class ValidationResult(BaseModel):
    is_valid: bool
    violations: list[str] = Field(default_factory=list)
    severity: str = "info"
