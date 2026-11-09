"""Keyword (BM25) ranking and rank fusion, to sit beside the embedding search.

Embeddings match meaning but blur rare terms (NTILE, 힌트 문법); keyword matching does
the reverse. Fusing the two rankings keeps what each is good at.
"""

import math
import re
from collections import Counter

K1 = 1.5
B = 0.75
RRF_K = 60
# On paraphrased questions (little word overlap with the notes) weights of 1:2 beat 1:1 and 1:3;
# keyword matching is the steadier half on a small note set, embeddings still catch synonyms.
# Rechecked on a second subject (eval/holdout): 1:1 and 2:1 were worse on every set there too.
WEIGHTS = (1.0, 2.0)  # (embedding, keyword)

_WORD = re.compile(r"[0-9A-Za-z_]+|[가-힣]+")


def tokenize(text: str) -> list[str]:
    """Latin words whole, Korean words as character pairs so particles (조인은 / 조인을) still match."""
    tokens = []
    for word in _WORD.findall(text.lower()):
        if word.isascii():
            tokens.append(word)
        elif len(word) == 1:
            tokens.append(word)
        else:
            tokens.extend(word[i : i + 2] for i in range(len(word) - 1))
    return tokens


class BM25:
    def __init__(self, documents: list[str]):
        self.docs = [Counter(tokenize(d)) for d in documents]
        self.lengths = [sum(c.values()) for c in self.docs]
        self.avg_len = (sum(self.lengths) / len(self.lengths)) if self.lengths else 0.0
        df = Counter(t for c in self.docs for t in c)
        n = len(self.docs)
        self.idf = {t: math.log(1 + (n - f + 0.5) / (f + 0.5)) for t, f in df.items()}

    def scores(self, query: str) -> list[float]:
        terms = [t for t in tokenize(query) if t in self.idf]
        out = []
        for counts, length in zip(self.docs, self.lengths):
            norm = K1 * (1 - B + B * length / self.avg_len) if self.avg_len else K1
            out.append(sum(self.idf[t] * counts[t] * (K1 + 1) / (counts[t] + norm) for t in terms if t in counts))
        return out

    def rank(self, query: str, k: int) -> list[int]:
        scores = self.scores(query)
        order = sorted(range(len(scores)), key=lambda i: -scores[i])
        return [i for i in order[:k] if scores[i] > 0]


def fuse(dense: list[int], keyword: list[int], k: int) -> list[int]:
    """The app's ranking: weighted RRF, but the embedding search's best match always makes the top k.

    With keyword weight 2, a chunk only the embedding search finds scores 1/61, below every
    keyword match in the pool (2/80 at rank 20). On questions that share almost no words with
    the notes, that pushed embedding hits that were ranked first out of the top 5.
    """
    fused = rrf([dense, keyword], WEIGHTS)
    top = fused[:k]
    # The fused first place is never given up; only the last slot of a longer list is.
    if dense and k > 1 and dense[0] not in top:
        top = top[: k - 1] + [dense[0]]
    return top + [i for i in fused if i not in top]


def rrf(rankings: list[list[int]], weights: tuple[float, ...] | None = None, k: int = RRF_K) -> list[int]:
    """Reciprocal rank fusion: an item scores weight/(k+rank) in every list that has it."""
    fused: dict[int, float] = {}
    for ranking, weight in zip(rankings, weights or (1.0,) * len(rankings)):
        for rank, idx in enumerate(ranking, start=1):
            fused[idx] = fused.get(idx, 0.0) + weight / (k + rank)
    return sorted(fused, key=lambda i: -fused[i])
