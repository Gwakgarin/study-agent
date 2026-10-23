"""Keep "not in your notes" answers from turning into a general-knowledge lecture.

The model is told to stop after saying the notes don't cover a question, but it often
adds "일반적으로는 ..." anyway. The prompt alone left that in about 7 of 100 off-note
answers, so the first sentence is checked here and what follows a refusal is dropped.
"""

import re

GUIDANCE = "관련 노트를 올려 주시면 그 내용으로 답해 드릴게요."
HOLD_CHARS = 90

_SENTENCE_END = re.compile(r"(?<=[.!?。])\s|(?<=다)\.|\n")
_REFUSAL = re.compile(r"노트.{0,40}?(없|찾지 못|찾을 수 없|않(?:았|습|아|네))")
# A refusal clause often continues into the lecture: "...없지만, 일반적으로는 ...".
_CLAUSE_BREAK = re.compile(r"(없지만|없으나|없습니다만|못했지만|않지만|않습니다만|없는데|없고)")


def first_sentence_end(text: str) -> int | None:
    m = _SENTENCE_END.search(text)
    if not m:
        return None
    return m.end() if text[m.start()] != "\n" else m.start()


def clip_refusal(text: str) -> str | None:
    """The answer cut down to a bare refusal, or None if it is not a refusal."""
    text = text.strip()
    end = first_sentence_end(text)
    first = text if end is None else text[:end].strip()
    if not _REFUSAL.search(first):
        return None
    cut = _CLAUSE_BREAK.search(first)
    if cut:
        first = first[: cut.start()] + {"없": "없어요.", "못": "못했어요.", "않": "않아요."}[cut.group(1)[0]]
    first = first.rstrip()
    if not first.endswith((".", "요", "다")):
        first += "."
    return f"{first} {GUIDANCE}"
