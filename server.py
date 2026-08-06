"""FastAPI backend for the study agent (used by the React frontend)."""

import json
import shutil
import uuid
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from src import ingest, projects, search
from src.agent import new_conversation, run_turn
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


@app.post("/api/chat")
def chat(req: ChatRequest):
    messages = load_session(req.session_id) or new_conversation()
    messages.append({"role": "user", "content": req.message})
    messages = run_turn(messages, req.project_id)
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
