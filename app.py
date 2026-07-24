"""Streamlit chat UI for the study agent."""

import streamlit as st

from src.agent import new_conversation, run_turn

st.set_page_config(page_title="Study Agent", page_icon="📚")
st.title("📚 Study Agent")

if "messages" not in st.session_state:
    st.session_state.messages = new_conversation()

for message in st.session_state.messages:
    if message["role"] in ("user", "assistant") and message.get("content"):
        with st.chat_message(message["role"]):
            st.write(message["content"])

if prompt := st.chat_input("무엇이 궁금한가요?"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.write(prompt)

    with st.spinner("생각 중..."):
        st.session_state.messages = run_turn(st.session_state.messages)

    last = st.session_state.messages[-1]
    with st.chat_message("assistant"):
        st.write(last.get("content") or "")
