from models.common import TokenUsage
from logging_config import get_logger

logger = get_logger("token_budget")


class TokenBudget:

    def __init__(self, max_tokens: int):
        self.max_tokens = max_tokens
        self._used = 0

    def can_spend(self, estimated_tokens: int) -> bool:
        return self._used + estimated_tokens <= self.max_tokens

    def record(self, usage: TokenUsage) -> None:
        self._used += usage.total
        logger.debug(
            "tokens_recorded",
            added=usage.total,
            used=self._used,
            remaining=self.remaining,
        )

    @property
    def remaining(self) -> int:
        return max(0, self.max_tokens - self._used)

    @property
    def used(self) -> int:
        return self._used

    @property
    def utilization(self) -> float:
        return self._used / self.max_tokens if self.max_tokens > 0 else 0.0

    @property
    def is_budget_low(self) -> bool:
        return self.utilization >= 0.8

    @property
    def is_exhausted(self) -> bool:
        return self._used >= self.max_tokens
