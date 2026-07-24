"""FastAPI backend for the study agent (used by the React frontend)."""

import uuid

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from src.agent import new_conversation, run_turn
from src.config import settings
from src.sessions import load_session, save_session
from src.tools import get_weak_topics

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
