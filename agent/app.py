"""Streamlit entry point."""

from __future__ import annotations

import streamlit as st

from agent.orchestrator import AnalyticsOrchestrator
from agent.settings import get_settings
from agent.tools.schema_tool import get_dataset_schema
from agent.ui.components import render_response
from agent.ui.suggested_questions import SUGGESTED_QUESTIONS

st.set_page_config(page_title="TechSolve Operations AI", layout="wide")

settings = get_settings()
schema = get_dataset_schema(settings)

st.title("TechSolve Operations AI")
st.caption(
    "Synthetic support-ticket analytics. Default reporting scope: 2024-2025 eligible records."
)

with st.sidebar:
    st.subheader("Session")
    st.write(f"Dataset version: `{schema['dataset_version']}`")
    st.write(f"Model: `{settings.groq_model}`")
    st.write("Mode: `fake`" if settings.use_fake_llm else "Mode: `groq`")
    if st.button("Reset conversation"):
        st.session_state.messages = []

if "messages" not in st.session_state:
    st.session_state.messages = []

with st.expander("Suggested questions", expanded=not st.session_state.messages):
    cols = st.columns(2)
    for idx, suggested_question in enumerate(SUGGESTED_QUESTIONS):
        if cols[idx % 2].button(suggested_question, key=f"suggested_{idx}"):
            st.session_state.pending_question = suggested_question

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

question: str | None = st.chat_input(
    "Ask about ticket trends, SLA, teams, categories, holidays, or data quality"
)
if not question and "pending_question" in st.session_state:
    question = st.session_state.pop("pending_question")

if question:
    st.session_state.messages.append({"role": "user", "content": question})
    with st.chat_message("user"):
        st.markdown(question)
    with st.chat_message("assistant"):
        with st.spinner("Planning, validating SQL, and querying DuckDB..."):
            orchestrator = AnalyticsOrchestrator(settings)
            response = orchestrator.answer(question)
        render_response(response)
        content = (
            response.answer.answer_markdown
            if response.answer
            else response.refusal_reason or "No answer."
        )
        st.session_state.messages.append({"role": "assistant", "content": content})
