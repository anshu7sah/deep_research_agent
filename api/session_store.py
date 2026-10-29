import asyncio
from uuid import uuid4

from models.query import ResearchQuery
from models.session import ResearchSession, SessionEvent


class SessionStore:

    def __init__(self):
        self._sessions: dict[str, ResearchSession] = {}
        self._event_queues: dict[str, asyncio.Queue] = {}
        self._clarify_events: dict[str, asyncio.Event] = {}
        self._clarify_answers: dict[str, dict] = {}

    def create(self, query: str, mode: str) -> str:
        session_id = uuid4().hex[:12]
        session = ResearchSession(
            session_id=session_id,
            query=ResearchQuery(original_query=query),
            orchestration_mode=mode,
        )
        self._sessions[session_id] = session
        self._event_queues[session_id] = asyncio.Queue()
        self._clarify_events[session_id] = asyncio.Event()
        self._clarify_answers[session_id] = {}
        return session_id

    def get(self, session_id: str) -> ResearchSession | None:
        return self._sessions.get(session_id)

    def get_event_queue(self, session_id: str) -> asyncio.Queue:
        return self._event_queues[session_id]

    def get_clarify_event(self, session_id: str) -> asyncio.Event:
        return self._clarify_events[session_id]

    def get_clarify_answers_ref(self, session_id: str) -> dict:
        return self._clarify_answers[session_id]

    def submit_clarification(self, session_id: str, answers: dict) -> None:
        self._clarify_answers[session_id].update(answers)
        self._clarify_events[session_id].set()

    async def emit_event(self, session_id: str, event: SessionEvent) -> None:
        queue = self._event_queues.get(session_id)
        if queue:
            await queue.put(event)
