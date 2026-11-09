from src.hybrid import BM25, fuse, rrf, tokenize


def test_korean_particles_still_match():
    assert set(tokenize("조인은")) & set(tokenize("조인을"))


def test_latin_terms_stay_whole():
    assert tokenize("NTILE(4)는") == ["ntile", "4", "는"]


def test_bm25_ranks_the_chunk_with_the_rare_term_first():
    bm = BM25(["윈도우 함수 설명", "NTILE 로 행을 나눈다", "집계 함수 설명"])
    assert bm.rank("NTILE", 3) == [1]


def test_bm25_ignores_unknown_terms():
    assert BM25(["조인 설명"]).rank("zzz", 3) == []


def test_rrf_prefers_items_both_rankings_agree_on():
    assert rrf([[1, 2, 3], [3, 1, 4]])[:2] == [1, 3]


def test_rrf_weight_lets_one_ranking_break_a_tie():
    assert rrf([[1, 2], [2, 1]], weights=(1.0, 2.0))[0] == 2


def test_fuse_keeps_the_embedding_top_hit_the_keyword_search_missed():
    # 9 only shows up in the embedding ranking; keyword weight 2 alone would push it past 5th.
    dense = [9, 1, 2, 3, 4, 5]
    keyword = [1, 2, 3, 4, 5, 6]

    assert 9 not in rrf([dense, keyword], (1.0, 2.0))[:5]
    top = fuse(dense, keyword, 5)[:5]
    assert 9 in top and top[:4] == rrf([dense, keyword], (1.0, 2.0))[:4]


def test_fuse_leaves_the_order_alone_when_the_embedding_top_hit_is_already_in():
    dense, keyword = [1, 2, 3], [2, 1, 3]

    assert fuse(dense, keyword, 2) == rrf([dense, keyword], (1.0, 2.0))
