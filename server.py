"""FastAPI backend for the study agent (used by the React frontend)."""

import base64
import json
import secrets
import shutil
import uuid
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, Request, Response, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from openai import (
    APIConnectionError,
    APIStatusError,
    APITimeoutError,
    AuthenticationError,
    RateLimitError,
)
from pydantic import BaseModel

from src import ingest, projects, search
from src.agent import ToolLoopError, new_conversation, run_turn
from src.config import settings
from src.sessions import load_session, save_session
from src.tracker import get_due_topics, get_weak_topics

ALLOWED_NOTE_EXTENSIONS = {".pdf", ".md", ".txt"}

app = FastAPI(title="Study Agent API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

PUBLIC_PATHS = {"/api/health"}


def _password_ok(header: str | None) -> bool:
    if not header or not header.startswith("Basic "):
        return False
    try:
        decoded = base64.b64decode(header[6:]).decode()
    except (ValueError, UnicodeDecodeError):
        return False
    _, _, password = decoded.partition(":")
    return secrets.compare_digest(password.encode(), settings.access_password.encode())


@app.middleware("http")
async def require_password(request: Request, call_next):
    # The browser shows its own login prompt on 401 and then resends the credentials
    # on every same-origin fetch, so the React app needs no changes.
    if settings.access_password and request.url.path not in PUBLIC_PATHS:
        if not _password_ok(request.headers.get("authorization")):
            return Response(status_code=401, headers={"WWW-Authenticate": 'Basic realm="Recap"'})
    return await call_next(request)


@app.get("/api/health")
def health():
    return {"status": "ok"}


def _visible(messages: list[dict]) -> list[dict]:
    return [
        {"role": m["role"], "content": m["content"]}
        for m in messages
        if m["role"] in ("user", "assistant") and m.get("content")
    ]


class CreateProjectRequest(BaseModel):
    name: str


class SessionRequest(BaseModel):
    project_id: str


class ChatRequest(BaseModel):
    session_id: str
    project_id: str
    message: str


class ResetRequest(BaseModel):
    session_id: str
    project_id: str


@app.post("/api/projects")
def create_project(req: CreateProjectRequest):
    return projects.create_project(req.name)


@app.get("/api/projects")
def list_projects():
    return projects.list_projects()


@app.post("/api/session")
def create_session(req: SessionRequest):
    session_id = str(uuid.uuid4())
    messages = new_conversation()

    due = get_due_topics(req.project_id)
    if due:
        topic_list = ", ".join(t["topic"] for t in due[:3])
        messages.append(
            {
                "role": "assistant",
                "content": f"오늘 복습하면 좋을 주제가 있어요: {topic_list}. 퀴즈 볼까요?",
            }
        )

    save_session(session_id, req.project_id, messages)
    return {"session_id": session_id, "messages": _visible(messages)}


def _chat_failure(exc: Exception) -> HTTPException:
    # Order matters: APITimeoutError is a subclass of APIConnectionError.
    if isinstance(exc, APITimeoutError):
        return HTTPException(504, "AI 응답이 너무 오래 걸려요. 잠시 후 다시 보내주세요.")
    if isinstance(exc, RateLimitError):
        return HTTPException(429, "요청이 몰려서 지금은 답할 수 없어요. 잠시 후 다시 보내주세요.")
    if isinstance(exc, APIConnectionError):
        return HTTPException(503, "AI 서버에 연결하지 못했어요. 네트워크를 확인하고 다시 보내주세요.")
    if isinstance(exc, AuthenticationError):
        return HTTPException(500, "서버의 OpenAI API 키 설정에 문제가 있어요.")
    if isinstance(exc, APIStatusError):
        return HTTPException(502, "AI 서버에서 오류가 났어요. 잠시 후 다시 보내주세요.")
    if isinstance(exc, ToolLoopError):
        return HTTPException(502, "답변을 정리하지 못했어요. 질문을 조금 바꿔서 다시 보내주세요.")
    return HTTPException(500, "답변을 만드는 중 오류가 났어요.")


@app.post("/api/chat")
def chat(req: ChatRequest):
    messages = load_session(req.session_id) or new_conversation()
    messages.append({"role": "user", "content": req.message})
    try:
        messages = run_turn(messages, req.project_id)
    except Exception as exc:
        # Nothing is saved, so the stored session stays exactly as it was before
        # this message and the client can resend it.
        raise _chat_failure(exc) from exc
    save_session(req.session_id, req.project_id, messages)
    return {"messages": _visible(messages)}


@app.post("/api/reset")
def reset(req: ResetRequest):
    messages = new_conversation()
    save_session(req.session_id, req.project_id, messages)
    return {"messages": []}


@app.get("/api/weak-topics")
def weak_topics(project_id: str):
    try:
        return get_weak_topics(project_id)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.get("/api/notes")
def list_notes(project_id: str):
    metadata_path = projects.index_dir(project_id) / "metadata.json"
    if not metadata_path.exists():
        return []

    metadata = json.loads(metadata_path.read_text())
    counts: dict[str, int] = {}
    for entry in metadata:
        counts[entry["source"]] = counts.get(entry["source"], 0) + 1
    return [{"source": source, "chunks": count} for source, count in sorted(counts.items())]


@app.post("/api/notes")
async def upload_notes(project_id: str = Form(...), files: list[UploadFile] = File(...)):
    if not files:
        raise HTTPException(status_code=400, detail="업로드할 파일이 없습니다.")

    for file in files:
        if Path(file.filename).suffix.lower() not in ALLOWED_NOTE_EXTENSIONS:
            raise HTTPException(
                status_code=400,
                detail=f"지원하지 않는 파일 형식입니다: {file.filename} (pdf, md, txt만 가능)",
            )

    notes_dir = projects.notes_dir(project_id)
    notes_dir.mkdir(parents=True, exist_ok=True)
    for file in files:
        with (notes_dir / file.filename).open("wb") as dest:
            shutil.copyfileobj(file.file, dest)

    try:
        ingest.build_index(project_id)
    except SystemExit as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    search.invalidate(project_id)

    return list_notes(project_id)


# In the Docker image the built React app sits next to the API, so one server
# handles both. Locally (npm run dev) the dist folder is absent and Vite serves it.
FRONTEND_DIST = Path(__file__).resolve().parent / "frontend" / "dist"

if FRONTEND_DIST.is_dir():
    app.mount("/assets", StaticFiles(directory=FRONTEND_DIST / "assets"), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    def spa(full_path: str):
        if full_path.startswith("api/"):
            raise HTTPException(status_code=404)
        candidate = (FRONTEND_DIST / full_path).resolve()
        if full_path and candidate.is_file() and candidate.is_relative_to(FRONTEND_DIST):
            return FileResponse(candidate)
        # React Router paths like /app/<id> fall back to index.html.
        return FileResponse(FRONTEND_DIST / "index.html")
