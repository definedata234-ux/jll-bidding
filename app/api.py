"""
FastAPI surface for the JLL Bid Copilot prototype.

Run with:  uvicorn app.api:app --reload --port 8000
Docs at:   http://127.0.0.1:8000/docs

This is a thin HTTP wrapper around the same orchestrator/store objects the
CLI uses — both share the exact same business logic and storage, so the
two interfaces stay consistent (and you could resume a CLI session from
the API, or vice versa, using the same opportunity_id).

Enterprise-rigor additions over the original Stage 3 cut: structured
request/error logging, rate limiting, security headers, and a consistent
JSON error envelope instead of ad hoc HTTPException details.
"""
from __future__ import annotations

import time
import uuid

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ValidationError
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address

from app import config
from app.approvals import decide_approval
from app.logging_config import get_logger
from app.orchestrator import BidCopilotOrchestrator, OrchestratorError
from app.state import ConversationStore, OpportunityNotFound, OpportunityStore

logger = get_logger(__name__)

limiter = Limiter(key_func=get_remote_address, default_limits=["60/minute"])

app = FastAPI(
    title="JLL Bid & Leasing Copilot API",
    description="Internal prototype API — mocked data only, no real integrations.",
    version="0.2.0",
)
app.state.limiter = limiter
app.add_middleware(SlowAPIMiddleware)

# Static web UI assets (HTML/CSS/JS) — mounted under /static, kept distinct
# from the API's own paths (e.g. /opportunities) so neither can shadow the
# other. The "/" route below explicitly serves the chat UI's index.html.
app.mount("/static", StaticFiles(directory=str(config.APP_DIR / "static")), name="static")

opportunity_store = OpportunityStore()
conversation_store = ConversationStore()

_orchestrator: BidCopilotOrchestrator | None = None


def get_orchestrator() -> BidCopilotOrchestrator:
    global _orchestrator
    if _orchestrator is None:
        try:
            _orchestrator = BidCopilotOrchestrator(opportunity_store, conversation_store)
        except OrchestratorError as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc
    return _orchestrator


# ---------------------------------------------------------------------------
# Middleware: request logging + security headers
# ---------------------------------------------------------------------------

@app.middleware("http")
async def log_requests(request: Request, call_next):
    request_id = uuid.uuid4().hex[:12]
    started = time.monotonic()
    logger.info("http_request_start", request_id=request_id, method=request.method, path=request.url.path)
    try:
        response = await call_next(request)
    except Exception:
        logger.exception("http_request_unhandled_error", request_id=request_id, path=request.url.path)
        raise
    duration_ms = round((time.monotonic() - started) * 1000, 1)
    logger.info(
        "http_request_end",
        request_id=request_id,
        method=request.method,
        path=request.url.path,
        status_code=response.status_code,
        duration_ms=duration_ms,
    )
    response.headers["X-Request-ID"] = request_id
    return response


@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
    return response


# ---------------------------------------------------------------------------
# Centralized error handling — consistent JSON envelope, no leaked internals
# ---------------------------------------------------------------------------

def _error_body(code: str, message: str, details=None) -> dict:
    body = {"error": {"code": code, "message": message}}
    if details is not None:
        body["error"]["details"] = details
    return body


@app.exception_handler(OpportunityNotFound)
async def handle_opportunity_not_found(request: Request, exc: OpportunityNotFound):
    return JSONResponse(status_code=404, content=_error_body("opportunity_not_found", str(exc)))


@app.exception_handler(ValueError)
async def handle_value_error(request: Request, exc: ValueError):
    return JSONResponse(status_code=400, content=_error_body("bad_request", str(exc)))


@app.exception_handler(ValidationError)
async def handle_pydantic_validation_error(request: Request, exc: ValidationError):
    return JSONResponse(status_code=422, content=_error_body("validation_error", "Invalid data.", exc.errors()))


@app.exception_handler(RequestValidationError)
async def handle_request_validation_error(request: Request, exc: RequestValidationError):
    return JSONResponse(status_code=422, content=_error_body("validation_error", "Invalid request body.", exc.errors()))


app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


@app.exception_handler(Exception)
async def handle_unexpected_error(request: Request, exc: Exception):
    logger.exception("unhandled_exception", path=request.url.path)
    return JSONResponse(status_code=500, content=_error_body("internal_error", "An unexpected error occurred."))


# ---------------------------------------------------------------------------
# Request/response models
# ---------------------------------------------------------------------------

class CreateOpportunityRequest(BaseModel):
    client_name: str


class ChatRequest(BaseModel):
    message: str


class ApprovalDecisionRequest(BaseModel):
    decision: str  # "approve" | "reject"
    reviewer: str = "api-user"


def _simplify_history(messages: list[dict]) -> list[dict]:
    """Collapse raw Claude/DeepSeek message history (with tool_use/tool_result
    blocks) into a simple {role, text} list for display in the web UI. Tool
    calls are rendered as short system-style notes rather than raw JSON,
    since the chat panel is for humans, not for debugging the tool loop."""
    simplified = []
    for msg in messages:
        content = msg["content"]
        role = msg["role"]
        if isinstance(content, str):
            simplified.append({"role": role, "text": content})
            continue
        text_parts = []
        tool_notes = []
        for block in content:
            btype = block.get("type")
            if btype == "text":
                text_parts.append(block["text"])
            elif btype == "tool_use":
                tool_notes.append(f"calling {block['name']}")
        if text_parts:
            simplified.append({"role": role, "text": "".join(text_parts)})
        if tool_notes:
            simplified.append({"role": "system", "text": "; ".join(tool_notes)})
    return simplified


@app.get("/", include_in_schema=False)
def serve_ui():
    return FileResponse(str(config.APP_DIR / "static" / "index.html"))


@app.get("/healthz")
def healthz():
    return {
        "status": "ok",
        "llm_ready": bool(config.active_llm_key()),
        "llm_provider": config.active_llm_label(),
    }


@app.post("/opportunities")
def create_opportunity(req: CreateOpportunityRequest):
    record = opportunity_store.create(req.client_name)
    logger.info("opportunity_created", opportunity_id=record["opportunity_id"], client_name=req.client_name)
    return record


@app.get("/opportunities")
def list_opportunities():
    return {"opportunity_ids": opportunity_store.list_ids()}


@app.get("/opportunities/{opportunity_id}")
def get_opportunity(opportunity_id: str):
    return opportunity_store.get(opportunity_id)


@app.get("/opportunities/{opportunity_id}/events")
def get_events(opportunity_id: str):
    record = opportunity_store.get(opportunity_id)
    return {"pipeline_events": record["pipeline_events"]}


@app.get("/opportunities/{opportunity_id}/approvals")
def get_approvals(opportunity_id: str):
    record = opportunity_store.get(opportunity_id)
    return {"approvals": record["approvals"]}


@app.post("/opportunities/{opportunity_id}/approvals/{approval_id}/decision")
def post_approval_decision(opportunity_id: str, approval_id: str, req: ApprovalDecisionRequest):
    result = decide_approval(
        opportunity_id, approval_id, req.decision, req.reviewer,
        opportunity_store=opportunity_store, conversation_store=conversation_store,
    )
    logger.info(
        "approval_decided", opportunity_id=opportunity_id, approval_id=approval_id,
        decision=req.decision, reviewer=req.reviewer,
    )
    return result


@app.get("/opportunities/{opportunity_id}/messages")
def get_messages(opportunity_id: str):
    opportunity_store.get(opportunity_id)  # raises OpportunityNotFound (404) if missing
    history = conversation_store.load(opportunity_id)
    return {"messages": _simplify_history(history)}


@app.post("/opportunities/{opportunity_id}/chat")
@limiter.limit("15/minute")
def chat(request: Request, opportunity_id: str, req: ChatRequest):
    orchestrator = get_orchestrator()
    reply = orchestrator.chat(opportunity_id, req.message)
    return {"reply": reply}
