"""FastAPI backend for the study agent (used by the React frontend)."""

import base64
import json
import secrets
import shutil
import uuid
from pathlib import Path

from fastapi import Depends, FastAPI, File, Form, HTTPException, Request, Response, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from openai import (
    APIConnectionError,
    APIStatusError,
    APITimeoutError,
    AuthenticationError,
    RateLimitError,
)
from pydantic import BaseModel

from src import auth, display, ingest, projects, quizzes, search, usage
from src.agent import ToolLoopError, new_conversation, run_turn, run_turn_stream
from src.config import settings
from src.sessions import get_project_id, load_session, save_session
from src.tracker import get_due_topics, get_weak_topics, project_stats, record_answer

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


def _screen(messages: list[dict]) -> list[dict]:
    """What the chat screen shows: text, note sources and quiz cards, no tool plumbing."""
    return display.visible_messages(messages, quizzes.answers_for(display.quiz_ids(messages)))


# --- accounts -------------------------------------------------------------

SESSION_COOKIE = "recap_session"


def current_user(request: Request) -> dict:
    user = auth.user_for_token(request.cookies.get(SESSION_COOKIE))
    if user is None:
        raise HTTPException(status_code=401, detail="로그인이 필요해요.")
    return user


def owned_project(project_id: str, user: dict) -> dict:
    # Someone else's project answers exactly like a missing one, so ids can't be probed.
    project = projects.get_project(project_id)
    if project is None or project["user_id"] != user["id"]:
        raise HTTPException(status_code=404, detail="과목을 찾을 수 없어요.")
    return project


def _set_login_cookie(response: Response, user_id: str) -> None:
    response.set_cookie(
        SESSION_COOKIE,
        auth.create_login(user_id),
        max_age=auth.SESSION_DAYS * 24 * 3600,
        httponly=True,
        samesite="lax",
        secure=settings.cookie_secure,
    )


class SignupRequest(BaseModel):
    username: str
    password: str
    signup_code: str | None = None


class LoginRequest(BaseModel):
    username: str
    password: str


@app.get("/api/auth/config")
def auth_config():
    return {"signup_code_required": bool(settings.signup_code)}


@app.post("/api/auth/signup")
def signup(req: SignupRequest, response: Response):
    if settings.signup_code and not secrets.compare_digest(
        (req.signup_code or "").encode(), settings.signup_code.encode()
    ):
        raise HTTPException(status_code=403, detail="가입 코드가 맞지 않아요.")
    try:
        user = auth.create_user(req.username, req.password)
    except auth.SignupError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    _set_login_cookie(response, user["id"])
    return user


@app.post("/api/auth/login")
def login(req: LoginRequest, response: Response):
    user = auth.authenticate(req.username, req.password)
    if user is None:
        raise HTTPException(status_code=401, detail="아이디 또는 비밀번호가 맞지 않아요.")
    _set_login_cookie(response, user["id"])
    return user


@app.post("/api/auth/logout")
def logout(request: Request, response: Response):
    auth.delete_login(request.cookies.get(SESSION_COOKIE))
    response.delete_cookie(SESSION_COOKIE)
    return {"ok": True}


@app.get("/api/auth/me")
def me(user: dict = Depends(current_user)):
    return user


# --- study API --------------------------------------------------------------


class CreateProjectRequest(BaseModel):
    name: str


class SessionRequest(BaseModel):
    project_id: str
    resume_session_id: str | None = None


class ChatRequest(BaseModel):
    session_id: str
    project_id: str
    message: str


class ResetRequest(BaseModel):
    session_id: str
    project_id: str


def _project_view(project: dict) -> dict:
    return {"id": project["id"], "name": project["name"], "created_at": project["created_at"]}


@app.post("/api/projects")
def create_project(req: CreateProjectRequest, user: dict = Depends(current_user)):
    return _project_view(projects.create_project(req.name, user["id"]))


@app.get("/api/projects")
def list_projects(user: dict = Depends(current_user)):
    return [
        {**_project_view(p), "notes": len(_note_counts(p["id"])), **project_stats(p["id"])}
        for p in projects.list_projects(user["id"])
    ]


SAMPLE_NOTES_DIR = Path(__file__).resolve().parent / "eval" / "corpus"
SAMPLE_PROJECT_NAME = "SQLD 맛보기 (샘플)"


@app.post("/api/projects/sample")
def create_sample_project(user: dict = Depends(current_user)):
    """A ready-to-use subject so a new user can try search and quizzes before uploading anything."""
    for existing in projects.list_projects(user["id"]):
        if existing["name"] == SAMPLE_PROJECT_NAME:
            return _project_view(existing)

    project = projects.create_project(SAMPLE_PROJECT_NAME, user["id"])
    notes_dir = projects.notes_dir(project["id"])
    notes_dir.mkdir(parents=True, exist_ok=True)
    for note in sorted(SAMPLE_NOTES_DIR.glob("*.md")):
        shutil.copyfile(note, notes_dir / note.name)
    try:
        ingest.build_index(project["id"])
    except Exception as exc:
        raise HTTPException(
            status_code=502, detail="샘플 노트를 준비하지 못했어요. 잠시 후 다시 시도해주세요."
        ) from exc
    return _project_view(project)


@app.get("/api/review")
def review_topics(project_id: str, user: dict = Depends(current_user)):
    owned_project(project_id, user)
    return get_due_topics(project_id)


@app.post("/api/session")
def create_session(req: SessionRequest, user: dict = Depends(current_user)):
    owned_project(req.project_id, user)
    # Coming back to a subject picks up the last conversation instead of a blank one.
    if req.resume_session_id and get_project_id(req.resume_session_id) == req.project_id:
        resumed = load_session(req.resume_session_id)
        if resumed and len(resumed) > 1:
            return {"session_id": req.resume_session_id, "messages": _screen(resumed)}

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
    return {"session_id": session_id, "messages": _screen(messages)}


def _check_session(session_id: str, project_id: str) -> None:
    # A chat session belongs to the project it was opened for; anything else is refused
    # so one user can't read or overwrite a conversation from another project.
    stored = get_project_id(session_id)
    if stored is not None and stored != project_id:
        raise HTTPException(status_code=404, detail="대화를 찾을 수 없어요.")


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


def _start_chat(req: ChatRequest, user: dict) -> list[dict]:
    owned_project(req.project_id, user)
    _check_session(req.session_id, req.project_id)
    if usage.chats_in_last_hour(user["id"]) >= settings.chat_limit_per_hour:
        raise HTTPException(
            429, f"한 시간에 {settings.chat_limit_per_hour}번까지 질문할 수 있어요. 잠시 후 다시 보내주세요."
        )
    messages = load_session(req.session_id) or new_conversation()
    messages.append({"role": "user", "content": req.message})
    usage.record_chat(user["id"])
    return messages


@app.post("/api/chat/stream")
def chat_stream(req: ChatRequest, user: dict = Depends(current_user)):
    # Checks run before the stream opens, so they still answer with normal status codes.
    messages = _start_chat(req, user)

    def events():
        def event(payload: dict) -> str:
            return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"

        try:
            for kind, text in run_turn_stream(messages, req.project_id):
                yield event({"type": kind, "text": text})
        except Exception as exc:
            # As with /api/chat, nothing is saved, so the message can be resent.
            failure = _chat_failure(exc)
            yield event({"type": "error", "status": failure.status_code, "detail": failure.detail})
            return
        save_session(req.session_id, req.project_id, messages)
        yield event({"type": "done", "messages": _screen(messages)})

    return StreamingResponse(events(), media_type="text/event-stream", headers={"Cache-Control": "no-cache"})


@app.post("/api/chat")
def chat(req: ChatRequest, user: dict = Depends(current_user)):
    messages = _start_chat(req, user)
    try:
        messages = run_turn(messages, req.project_id)
    except Exception as exc:
        # Nothing is saved, so the stored session stays exactly as it was before
        # this message and the client can resend it.
        raise _chat_failure(exc) from exc
    save_session(req.session_id, req.project_id, messages)
    return {"messages": _screen(messages)}


@app.post("/api/reset")
def reset(req: ResetRequest, user: dict = Depends(current_user)):
    owned_project(req.project_id, user)
    _check_session(req.session_id, req.project_id)
    messages = new_conversation()
    save_session(req.session_id, req.project_id, messages)
    return {"messages": []}


class QuizAnswerRequest(BaseModel):
    session_id: str
    project_id: str
    quiz_id: str
    choice: int


@app.post("/api/quiz/answer")
def answer_quiz(req: QuizAnswerRequest, user: dict = Depends(current_user)):
    owned_project(req.project_id, user)
    _check_session(req.session_id, req.project_id)
    messages = load_session(req.session_id)
    quiz = display.find_quiz(messages or [], req.quiz_id)
    if quiz is None:
        raise HTTPException(status_code=404, detail="퀴즈를 찾을 수 없어요.")
    if not 0 <= req.choice < len(quiz["choices"]):
        raise HTTPException(status_code=400, detail="보기를 다시 골라주세요.")

    # Graded here by comparing indexes, not by asking the model to read "2번".
    correct = req.choice == quiz["answer_index"]
    if quizzes.save_answer(req.quiz_id, req.project_id, req.choice, correct):
        record_answer(req.project_id, quiz.get("topic") or "기타", correct)
        # Tell the model what happened so it doesn't ask again or record it twice.
        picked = quiz["choices"][req.choice]
        messages.append(
            {
                "role": "system",
                "content": (
                    f"사용자가 퀴즈 카드에서 '{picked}'를 골랐고 {'정답' if correct else '오답'}입니다. "
                    "이 결과는 이미 기록되었으니 record_answer를 다시 부르지 마세요."
                ),
            }
        )
        save_session(req.session_id, req.project_id, messages)

    answer = quizzes.answers_for([req.quiz_id])[req.quiz_id]
    return display.public_quiz(quiz, answer)


@app.get("/api/weak-topics")
def weak_topics(project_id: str, user: dict = Depends(current_user)):
    owned_project(project_id, user)
    try:
        return get_weak_topics(project_id)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


def _note_counts(project_id: str) -> list[dict]:
    metadata_path = projects.index_dir(project_id) / "metadata.json"
    if not metadata_path.exists():
        return []

    metadata = json.loads(metadata_path.read_text())
    counts: dict[str, int] = {}
    for entry in metadata:
        counts[entry["source"]] = counts.get(entry["source"], 0) + 1
    return [{"source": source, "chunks": count} for source, count in sorted(counts.items())]


@app.get("/api/notes")
def list_notes(project_id: str, user: dict = Depends(current_user)):
    owned_project(project_id, user)
    return _note_counts(project_id)


@app.post("/api/notes")
async def upload_notes(
    project_id: str = Form(...),
    files: list[UploadFile] = File(...),
    user: dict = Depends(current_user),
):
    owned_project(project_id, user)
    if not files:
        raise HTTPException(status_code=400, detail="업로드할 파일이 없습니다.")

    # Keep only the base name: a filename like "../../x" must not escape the notes folder.
    names = [Path(file.filename or "").name for file in files]
    for name in names:
        if Path(name).suffix.lower() not in ALLOWED_NOTE_EXTENSIONS:
            raise HTTPException(
                status_code=400,
                detail=f"지원하지 않는 파일 형식입니다: {name} (pdf, md, txt만 가능)",
            )

    notes_dir = projects.notes_dir(project_id)
    existing = {p.name for p in notes_dir.iterdir()} if notes_dir.is_dir() else set()
    if len(existing | set(names)) > settings.max_notes_per_project:
        raise HTTPException(
            status_code=400, detail=f"과목당 노트는 {settings.max_notes_per_project}개까지 올릴 수 있어요."
        )

    max_bytes = settings.max_upload_mb * 1024 * 1024
    contents = []
    for name, file in zip(names, files):
        data = await file.read(max_bytes + 1)
        if len(data) > max_bytes:
            raise HTTPException(
                status_code=400, detail=f"{name}이(가) {settings.max_upload_mb}MB를 넘어요."
            )
        contents.append((name, data))

    notes_dir.mkdir(parents=True, exist_ok=True)
    for name, data in contents:
        (notes_dir / name).write_bytes(data)

    try:
        ingest.build_index(project_id)
    except SystemExit as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    search.invalidate(project_id)

    return _note_counts(project_id)


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
