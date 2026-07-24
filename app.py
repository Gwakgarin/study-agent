"""Streamlit chat UI for the study agent."""

import streamlit as st

from src.agent import new_conversation, run_turn
from src.tools import get_weak_topics

st.set_page_config(page_title="Study Agent", page_icon="📚", layout="centered")

st.markdown(
    """
    <style>
    .block-container { padding-top: 2rem; max-width: 760px; }
    [data-testid="stChatMessage"] {
        border-radius: 14px;
        padding: 0.4rem 0.2rem;
    }
    .weak-topic-card {
        background: #F0EEFB;
        border-radius: 10px;
        padding: 0.6rem 0.8rem;
        margin-bottom: 0.5rem;
    }
    .weak-topic-card .topic-name { font-weight: 600; }
    .weak-topic-card .topic-rate { color: #6C5CE7; font-size: 0.85rem; }
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("📚 Study Agent")
st.caption("노트를 검색해서 답하고, 틀린 주제를 기억해뒀다가 다음 퀴즈에서 우선 출제하는 학습 에이전트")

with st.sidebar:
    st.subheader("🧠 약점 주제")
    try:
        weak_topics = get_weak_topics()
    except Exception:
        weak_topics = []

    if not weak_topics:
        st.caption("아직 기록된 오답이 없어요. 퀴즈를 풀어보면 여기에 쌓여요.")
    else:
        for item in weak_topics:
            st.markdown(
                f"""
                <div class="weak-topic-card">
                    <div class="topic-name">{item['topic']}</div>
                    <div class="topic-rate">오답률 {item['wrong_rate']:.0%} ({item['wrong']}/{item['attempts']})</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    st.divider()
    if st.button("🗑️ 대화 초기화"):
        st.session_state.messages = new_conversation()
        st.rerun()

if "messages" not in st.session_state:
    st.session_state.messages = new_conversation()

AVATARS = {"user": "🧑", "assistant": "📚"}

for message in st.session_state.messages:
    if message["role"] in ("user", "assistant") and message.get("content"):
        with st.chat_message(message["role"], avatar=AVATARS.get(message["role"])):
            st.write(message["content"])

if prompt := st.chat_input("무엇이 궁금한가요?"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user", avatar=AVATARS["user"]):
        st.write(prompt)

    with st.spinner("생각 중..."):
        st.session_state.messages = run_turn(st.session_state.messages)

    last = st.session_state.messages[-1]
    with st.chat_message("assistant", avatar=AVATARS["assistant"]):
        st.write(last.get("content") or "")
