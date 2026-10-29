from pydantic import BaseModel, Field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from models.query import ResearchQuery
from models.report import FinalReport


class SessionStatus(str, Enum):
    CREATED = "created"
    VALIDATING = "validating"
    CLARIFYING = "clarifying"
    WAITING_FOR_ANSWERS = "waiting_for_answers"
    PLANNING = "planning"
    SEARCHING = "searching"
    SCRAPING = "scraping"
    ANALYZING = "analyzing"
    WRITING = "writing"
    CRITIQUING = "critiquing"
    REVISING = "revising"
    PUBLISHING = "publishing"
    COMPLETED = "completed"
    FAILED = "failed"


class SessionEvent(BaseModel):
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    event_type: str
    message: str
    data: dict[str, Any] = Field(default_factory=dict)


class AgentCallRecord(BaseModel):
    agent_name: str
    started_at: datetime
    completed_at: datetime | None = None
    input_tokens: int = 0
    output_tokens: int = 0
    model: str = ""
    success: bool = True
    error: str | None = None
    duration_seconds: float = 0.0


class ResearchSession(BaseModel):
    session_id: str
    query: ResearchQuery
    status: SessionStatus = SessionStatus.CREATED
    orchestration_mode: str
    events: list[SessionEvent] = Field(default_factory=list)
    agent_calls: list[AgentCallRecord] = Field(default_factory=list)
    total_tokens: int = 0
    started_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: datetime | None = None
    report: FinalReport | None = None
