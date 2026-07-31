"""FastAPI backend for the study agent (used by the React frontend)."""

import json
import shutil
import uuid
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from src import ingest, search
from src.agent import new_conversation, run_turn
from src.config import settings
from src.sessions import load_session, save_session
from src.tools import get_weak_topics

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


class ChatRequest(BaseModel):
    session_id: str
    message: str


class ResetRequest(BaseModel):
    session_id: str


@app.post("/api/session")
def create_session():
    session_id = str(uuid.uuid4())
    save_session(session_id, new_conversation())
    return {"session_id": session_id, "messages": []}


@app.post("/api/chat")
def chat(req: ChatRequest):
    messages = load_session(req.session_id) or new_conversation()
    messages.append({"role": "user", "content": req.message})
    messages = run_turn(messages)
    save_session(req.session_id, messages)
    return {"messages": _visible(messages)}


@app.post("/api/reset")
def reset(req: ResetRequest):
    messages = new_conversation()
    save_session(req.session_id, messages)
    return {"messages": []}


@app.get("/api/weak-topics")
def weak_topics():
    try:
        return get_weak_topics()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.get("/api/notes")
def list_notes():
    metadata_path = ingest.INDEX_DIR / "metadata.json"
    if not metadata_path.exists():
        return []

    metadata = json.loads(metadata_path.read_text())
    counts: dict[str, int] = {}
    for entry in metadata:
        counts[entry["source"]] = counts.get(entry["source"], 0) + 1
    return [{"source": source, "chunks": count} for source, count in sorted(counts.items())]


@app.post("/api/notes")
async def upload_notes(files: list[UploadFile] = File(...)):
    if not files:
        raise HTTPException(status_code=400, detail="업로드할 파일이 없습니다.")

    for file in files:
        if Path(file.filename).suffix.lower() not in ALLOWED_NOTE_EXTENSIONS:
            raise HTTPException(
                status_code=400,
                detail=f"지원하지 않는 파일 형식입니다: {file.filename} (pdf, md, txt만 가능)",
            )

    ingest.NOTES_DIR.mkdir(parents=True, exist_ok=True)
    for file in files:
        with (ingest.NOTES_DIR / file.filename).open("wb") as dest:
            shutil.copyfileobj(file.file, dest)

    try:
        ingest.build_index()
    except SystemExit as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    # the search module caches the loaded index at module scope; force a reload
    search._index = None
    search._metadata = None

    return list_notes()
