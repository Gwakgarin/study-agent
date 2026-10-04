"""Measure Recap's RAG quality on a fixed SQLD note set.

Retrieval: for each chunk size, index eval/corpus and check whether the chunk holding
each question's evidence span comes back in the top k (Hit@k, MRR).

Answers (--answers): run the real agent loop (run_turn) against the same index, then
have a judge model grade each answer for correctness and grounding. Questions whose
answer is not in the notes check that the agent says it doesn't know.

    python -m eval.run_eval                       # retrieval only, chunk sizes 300/500/800
    python -m eval.run_eval --answers --chunk-size 500
"""

import argparse
import hashlib
import json
import time
from datetime import datetime
from pathlib import Path

import faiss
import numpy as np

from src import search
from src.agent import new_conversation, run_turn
from src.config import settings
from src.ingest import EMBEDDING_MODEL, chunk_text, get_client
from src.rag_eval import first_hit_rank, hit_rate_at_k, mean_reciprocal_rank

EVAL_DIR = Path(__file__).resolve().parent
CORPUS_DIR = EVAL_DIR / "corpus"
QUESTIONS_PATH = EVAL_DIR / "questions.jsonl"
CACHE_PATH = EVAL_DIR / ".cache" / "embeddings.json"
RESULTS_DIR = EVAL_DIR / "results"

EVAL_PROJECT_ID = "__eval__"
TOP_K = 10
KS = (1, 3, 5)

JUDGE_PROMPT = """학습 노트 기반 Q&A 에이전트의 답변을 채점합니다.

[질문]
{question}

[정답] (null이면 노트에 답이 없는 질문)
{reference}

[에이전트가 검색한 노트 내용]
{context}

[에이전트 답변]
{answer}

아래 기준으로 JSON만 출력하세요.
- correct: 정답이 있는 질문이면 답변이 정답과 같은 내용을 말하는지. 정답이 null이면 false.
- grounded: 답변의 사실 주장이 모두 검색한 노트 내용으로 뒷받침되는지. 모른다고만 답했으면 true.
- refused: 노트에 없어서 답할 수 없다고 말했는지.
{{"correct": true, "grounded": true, "refused": false, "reason": "한 문장"}}"""


def load_questions() -> list[dict]:
    return [json.loads(line) for line in QUESTIONS_PATH.read_text().splitlines() if line.strip()]


def load_chunks(chunk_size: int, overlap: int) -> list[dict]:
    chunks = []
    for path in sorted(CORPUS_DIR.glob("*.md")):
        for i, text in enumerate(chunk_text(path.read_text(encoding="utf-8"), chunk_size, overlap)):
            chunks.append({"source": path.name, "chunk_index": i, "text": text})
    return chunks


class EmbeddingCache:
    """Reruns only pay for texts that were never embedded with this model."""

    def __init__(self, path: Path):
        self.path = path
        self.data = json.loads(path.read_text()) if path.exists() else {}

    def _key(self, text: str) -> str:
        return hashlib.sha1(f"{EMBEDDING_MODEL}\n{text}".encode()).hexdigest()

    def embed(self, texts: list[str]) -> np.ndarray:
        missing = list(dict.fromkeys(t for t in texts if self._key(t) not in self.data))
        for start in range(0, len(missing), 100):
            batch = missing[start : start + 100]
            response = get_client().embeddings.create(model=EMBEDDING_MODEL, input=batch)
            for text, item in zip(batch, response.data):
                self.data[self._key(text)] = item.embedding
        if missing:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.path.write_text(json.dumps(self.data))
        vectors = np.array([self.data[self._key(t)] for t in texts], dtype="float32")
        faiss.normalize_L2(vectors)
        return vectors


def build_index(chunks: list[dict], cache: EmbeddingCache) -> faiss.Index:
    vectors = cache.embed([c["text"] for c in chunks])
    index = faiss.IndexFlatIP(vectors.shape[1])
    index.add(vectors)
    return index


def evaluate_retrieval(chunk_size: int, overlap: int, questions: list[dict], cache: EmbeddingCache) -> dict:
    answerable = [q for q in questions if q["evidence"]]
    chunks = load_chunks(chunk_size, overlap)
    index = build_index(chunks, cache)
    query_vectors = cache.embed([q["question"] for q in answerable])
    _, indices = index.search(query_vectors, min(TOP_K, len(chunks)))

    ranks, misses = [], []
    for q, row in zip(answerable, indices):
        retrieved = [chunks[i]["text"] for i in row if i != -1]
        rank = first_hit_rank(retrieved, q["evidence"])
        ranks.append(rank)
        if rank is None or rank > 5:
            misses.append({"id": q["id"], "question": q["question"], "rank": rank})

    return {
        "chunk_size": chunk_size,
        "overlap": overlap,
        "chunks": len(chunks),
        "questions": len(answerable),
        **{f"hit@{k}": hit_rate_at_k(ranks, k) for k in KS},
        "mrr": mean_reciprocal_rank(ranks),
        "misses_top5": misses,
    }


def _retrieved_context(messages: list[dict]) -> str:
    parts = []
    for m in messages:
        if m["role"] != "tool":
            continue
        try:
            payload = json.loads(m["content"])
        except json.JSONDecodeError:
            continue
        if isinstance(payload, list):
            parts.extend(item.get("text", "") for item in payload if isinstance(item, dict))
    return "\n---\n".join(parts) or "(검색 결과 없음)"


def judge(question: dict, context: str, answer: str) -> dict:
    prompt = JUDGE_PROMPT.format(
        question=question["question"],
        reference=json.dumps(question["answer"], ensure_ascii=False),
        context=context,
        answer=answer,
    )
    response = get_client().chat.completions.create(
        model=settings.chat_model,
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"},
        temperature=0,
    )
    return json.loads(response.choices[0].message.content)


def evaluate_answers(chunk_size: int, overlap: int, questions: list[dict], cache: EmbeddingCache) -> dict:
    chunks = load_chunks(chunk_size, overlap)
    # search_notes reads indexes through this cache, so the agent searches the eval
    # corpus without touching data/projects.
    search._cache[EVAL_PROJECT_ID] = (build_index(chunks, cache), chunks)

    rows = []
    for q in questions:
        started = time.perf_counter()
        messages = run_turn(new_conversation() + [{"role": "user", "content": q["question"]}], EVAL_PROJECT_ID)
        latency = time.perf_counter() - started
        answer = messages[-1].get("content") or ""
        grade = judge(q, _retrieved_context(messages), answer)
        searched = any(
            call["function"]["name"] == "search_notes"
            for m in messages
            for call in m.get("tool_calls", [])
        )
        rows.append(
            {
                "id": q["id"],
                "answerable": bool(q["evidence"]),
                "question": q["question"],
                "answer": answer,
                "searched": searched,
                "latency_s": round(latency, 2),
                **grade,
            }
        )
        print(f"  {q['id']}: correct={grade.get('correct')} grounded={grade.get('grounded')} "
              f"refused={grade.get('refused')} ({latency:.1f}s)")

    answerable = [r for r in rows if r["answerable"]]
    unanswerable = [r for r in rows if not r["answerable"]]
    latencies = sorted(r["latency_s"] for r in rows)
    return {
        "chunk_size": chunk_size,
        "overlap": overlap,
        "chat_model": settings.chat_model,
        "accuracy": sum(bool(r.get("correct")) for r in answerable) / len(answerable),
        "groundedness": sum(bool(r.get("grounded")) for r in rows) / len(rows),
        "refusal_on_unanswerable": sum(bool(r.get("refused")) for r in unanswerable) / len(unanswerable),
        "false_refusal_on_answerable": sum(bool(r.get("refused")) for r in answerable) / len(answerable),
        "search_call_rate": sum(r["searched"] for r in rows) / len(rows),
        "latency_p50_s": latencies[len(latencies) // 2],
        "latency_max_s": latencies[-1],
        "rows": rows,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--chunk-sizes", type=int, nargs="+", default=[300, 500, 800])
    parser.add_argument("--overlap", type=int, default=settings.chunk_overlap)
    parser.add_argument("--answers", action="store_true", help="also grade end-to-end agent answers")
    parser.add_argument("--chunk-size", type=int, default=settings.chunk_size, help="chunk size for --answers")
    args = parser.parse_args()

    questions = load_questions()
    cache = EmbeddingCache(CACHE_PATH)
    report = {"run_at": datetime.now().isoformat(timespec="seconds"), "embedding_model": EMBEDDING_MODEL}

    report["retrieval"] = [evaluate_retrieval(size, args.overlap, questions, cache) for size in args.chunk_sizes]
    print(f"\nRetrieval ({len([q for q in questions if q['evidence']])} questions, overlap {args.overlap})")
    print("| chunk_size | chunks | Hit@1 | Hit@3 | Hit@5 | MRR |")
    print("|---:|---:|---:|---:|---:|---:|")
    for r in report["retrieval"]:
        print(f"| {r['chunk_size']} | {r['chunks']} | {r['hit@1']:.1%} | {r['hit@3']:.1%} | "
              f"{r['hit@5']:.1%} | {r['mrr']:.3f} |")

    if args.answers:
        print(f"\nAnswers (chunk_size {args.chunk_size})")
        a = evaluate_answers(args.chunk_size, args.overlap, questions, cache)
        report["answers"] = a
        print(f"accuracy {a['accuracy']:.1%} | groundedness {a['groundedness']:.1%} | "
              f"refusal on unanswerable {a['refusal_on_unanswerable']:.1%} | "
              f"false refusal {a['false_refusal_on_answerable']:.1%} | "
              f"search call rate {a['search_call_rate']:.1%} | p50 {a['latency_p50_s']}s")

    RESULTS_DIR.mkdir(exist_ok=True)
    out = RESULTS_DIR / f"{datetime.now():%Y%m%d-%H%M%S}.json"
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2))
    print(f"\nSaved {out.relative_to(EVAL_DIR.parent)}")


if __name__ == "__main__":
    main()
