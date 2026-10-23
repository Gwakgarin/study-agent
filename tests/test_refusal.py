from src.refusal import GUIDANCE, clip_refusal


def test_drops_general_knowledge_after_a_refusal():
    assert clip_refusal("노트에 없다. 하지만 일반적으로 A입니다.") == f"노트에 없다. {GUIDANCE}"


def test_cuts_a_refusal_clause_that_runs_into_a_lecture():
    text = "노트에서 격리 수준에 대한 언급은 없지만, 일반적으로는 네 가지입니다."
    assert clip_refusal(text) == f"노트에서 격리 수준에 대한 언급은 없어요. {GUIDANCE}"


def test_leaves_answers_from_the_notes_alone():
    assert clip_refusal("노트에 따르면 정규화는 중복을 줄이는 것입니다. 일반적으로 3NF까지 합니다.") is None
