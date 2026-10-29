import asyncio
from abc import ABC, abstractmethod

from config import Settings
from guardrails.token_budget import TokenBudget
from logging_config import get_logger
from models.report import FinalReport
from models.session import ResearchSession, SessionEvent, SessionStatus
from services.llm_client import LLMClient

logger = get_logger("orchestrator")


class BaseOrchestrator(ABC):

    def __init__(
        self,
        llm_client: LLMClient,
        settings: Settings,
        event_queue: asyncio.Queue,
        clarify_event: asyncio.Event | None = None,
        clarify_answers: dict | None = None,
    ):
        self.llm = llm_client
        self.settings = settings
        self.event_queue = event_queue
        self.clarify_event = clarify_event
        self._clarify_answers = clarify_answers if clarify_answers is not None else {}
        self.budget = TokenBudget(settings.max_tokens_per_session)

    async def emit(self, event_type: str, message: str, **data) -> None:
        event = SessionEvent(event_type=event_type, message=message, data=data)
        await self.event_queue.put(event)

    async def wait_for_clarification(self) -> dict:
        if self.clarify_event is None:
            return {}
        await self.clarify_event.wait()
        return self._clarify_answers

    @abstractmethod
    async def run(self, session: ResearchSession) -> FinalReport:
        pass
