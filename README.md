# Study Agent

공부 노트를 검색(RAG)하고 퀴즈를 내주는 학습 에이전트입니다. 단순 질의응답에서 그치지 않고, 틀린 주제를 기억해뒀다가 다음 퀴즈에서 그 주제를 우선 출제하는 적응형 학습 트래킹이 핵심입니다.

## 아키텍처 (예정)

```
사용자 질문/요청
     ↓
LLM 에이전트 (OpenAI function calling)
     ↓
┌─────────────┬──────────────────┬────────────────┐
search_notes   generate_quiz      record_answer /
(RAG 검색)     (퀴즈 생성)         get_weak_topics
     ↓              ↓                    ↓
FAISS 인덱스   검색 결과 기반        SQLite (주제별
(노트 임베딩)   문제 생성            정답/오답 기록)
```

## 기술 스택

- Python, OpenAI API (function calling)
- FAISS — 노트 임베딩 검색
- SQLite — 약점 주제 트래킹
- FastAPI — 백엔드 API (`server.py`)
- React (Vite) — 프런트엔드 (`frontend/`)

## 실행

```bash
# 백엔드
source venv/bin/activate
uvicorn server:app --reload

# 프런트엔드 (다른 터미널)
cd frontend
npm install
npm run dev
```

`.env`에 `OPENAI_API_KEY`를 설정해야 합니다 (`.env.example` 참고).

## 상태

RAG 검색, 퀴즈 생성, 약점 트래킹 도구와 에이전트 루프 구현 완료. FastAPI + React 기반 UI로 개발 중입니다.
