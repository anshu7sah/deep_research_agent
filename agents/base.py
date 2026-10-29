from abc import ABC, abstractmethod
from datetime import datetime, timezone

from pydantic import BaseModel

from config import Settings
from logging_config import get_logger
from models.session import AgentCallRecord
from services.llm_client import LLMClient


class BaseAgent(ABC):
    name: str = "BaseAgent"
    model: str | None = None
    output_type: type[BaseModel] | None = None

    def __init__(self, llm_client: LLMClient, settings: Settings):
        self.llm = llm_client
        self.settings = settings
        self.logger = get_logger(self.name)

    async def execute(self, **kwargs) -> BaseModel:
        record = AgentCallRecord(
            agent_name=self.name,
            started_at=datetime.now(timezone.utc),
            model=self.model or self.settings.default_model,
        )

        try:
            messages = self._build_messages(**kwargs)
            result = await self.llm.complete_structured(
                messages=messages,
                response_model=self.output_type,
                model=self.model or self.settings.default_model,
            )
            record.success = True
            self.logger.info("agent_complete", agent=self.name)
            return result

        except Exception as e:
            record.success = False
            record.error = str(e)
            self.logger.error("agent_failed", agent=self.name, error=str(e))
            raise

        finally:
            record.completed_at = datetime.now(timezone.utc)
            record.duration_seconds = (
                record.completed_at - record.started_at
            ).total_seconds()

    @abstractmethod
    def _build_messages(self, **kwargs) -> list[dict]:
        pass
