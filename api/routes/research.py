import asyncio
import io

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from api.dependencies import get_llm_client, get_settings, get_store
from api.session_store import SessionStore
from config import Settings
from orchestration import get_orchestrator
from services.llm_client import LLMClient

router = APIRouter(prefix="/research")


class StartRequest(BaseModel):
    query: str
    mode: str = "code"


class ClarifyRequest(BaseModel):
    answers: dict[str, str]


class EmailRequest(BaseModel):
    to: str


@router.post("")
async def start_research(
    req: StartRequest,
    store: SessionStore = Depends(get_store),
    llm: LLMClient = Depends(get_llm_client),
    settings: Settings = Depends(get_settings),
):
    if req.mode not in ("code", "llm"):
        raise HTTPException(400, "Mode must be 'code' or 'llm'")

    session_id = store.create(req.query, req.mode)
    session = store.get(session_id)

    event_queue = store.get_event_queue(session_id)
    clarify_event = store.get_clarify_event(session_id)
    clarify_answers = store.get_clarify_answers_ref(session_id)

    orchestrator = get_orchestrator(
        mode=req.mode,
        llm_client=llm,
        settings=settings,
        event_queue=event_queue,
        clarify_event=clarify_event,
        clarify_answers=clarify_answers,
    )

    asyncio.create_task(_run_research(orchestrator, session))

    return {"session_id": session_id}


async def _run_research(orchestrator, session):
    try:
        await orchestrator.run(session)
    except Exception as e:
        await orchestrator.emit("error", str(e), recoverable=False)


@router.get("/{session_id}/stream")
async def stream_events(
    session_id: str,
    store: SessionStore = Depends(get_store),
):
    session = store.get(session_id)
    if not session:
        raise HTTPException(404, "Session not found")

    queue = store.get_event_queue(session_id)

    async def event_generator():
        while True:
            event = await queue.get()
            yield f"event: {event.event_type}\ndata: {event.model_dump_json()}\n\n"
            if event.event_type in ("complete", "error"):
                break

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post("/{session_id}/clarify")
async def submit_clarification(
    session_id: str,
    req: ClarifyRequest,
    store: SessionStore = Depends(get_store),
):
    session = store.get(session_id)
    if not session:
        raise HTTPException(404, "Session not found")

    store.submit_clarification(session_id, req.answers)
    return {"status": "ok"}


@router.get("/{session_id}")
async def get_session(
    session_id: str,
    store: SessionStore = Depends(get_store),
):
    session = store.get(session_id)
    if not session:
        raise HTTPException(404, "Session not found")
    return session.model_dump()


@router.get("/{session_id}/report/md")
async def download_markdown(
    session_id: str,
    store: SessionStore = Depends(get_store),
):
    session = store.get(session_id)
    if not session or not session.report:
        raise HTTPException(404, "Report not found")

    content = session.report.markdown.encode("utf-8")
    return StreamingResponse(
        io.BytesIO(content),
        media_type="text/markdown",
        headers={"Content-Disposition": f"attachment; filename=report_{session_id}.md"},
    )


@router.get("/{session_id}/report/pdf")
async def download_pdf(
    session_id: str,
    store: SessionStore = Depends(get_store),
    settings: Settings = Depends(get_settings),
):
    session = store.get(session_id)
    if not session or not session.report:
        raise HTTPException(404, "Report not found")

    from services.pdf_service import generate_pdf

    pdf_bytes = generate_pdf(session.report.markdown)

    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=report_{session_id}.pdf"},
    )


@router.post("/{session_id}/email")
async def email_report(
    session_id: str,
    req: EmailRequest,
    store: SessionStore = Depends(get_store),
    settings: Settings = Depends(get_settings),
):
    session = store.get(session_id)
    if not session or not session.report:
        raise HTTPException(404, "Report not found")

    if not settings.email_enabled:
        raise HTTPException(400, "Email is not configured")

    from services.email_service import send_report_email

    send_report_email(
        settings=settings,
        to_address=req.to,
        subject=f"Research Report: {session.report.title}",
        markdown=session.report.markdown,
    )
    return {"status": "sent"}
