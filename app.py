import sys
import os
import streamlit as st
import time

# --- Path Correction (Robust Version) ---
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__)))
sys.path.insert(0, PROJECT_ROOT)
# ----------------------------------------

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage

# Load environment variables from .env file
load_dotenv()

# --- Local Module Imports ---
from src.apxmind.core.resources import llm, creative_llm, vector_stores, logs
from src.apxmind.config import PAGE_TITLE, TAG_LINE, ASSISTIVE_LANGUAGE_OPTIONS, DEFAULT_LANGUAGE
from src.apxmind.graph.workflow import get_graph
from src.apxmind.ui.quiz import handle_quiz_ui

# --- Page Configuration ---
st.set_page_config(page_title="👩🏽‍⚕️ " + PAGE_TITLE, layout="wide")
st.title("👩🏽‍⚕️ " + PAGE_TITLE)
st.markdown(f"*{TAG_LINE}*")

# --- Resource Loading Status ---
# This block is now corrected
with st.status("🔎 Loading knowledge bases...", expanded=True) as status:
    for log in logs:
        st.write(log)
    if not vector_stores:
        # CORRECTED: The 'state' is changed from "warning" to the valid "error".
        # The 'expanded' argument must also be removed from the update call.
        status.update(label="⚠️ No knowledge bases loaded!", state="error")
    else:
        status.update(label="✅ Knowledge bases loaded!", state="complete", expanded=False)
    time.sleep(1)

# --- Graph Initialization ---
graph = get_graph()

# --- Streamlit UI and Chat Logic ---
# The rest of the file remains unchanged
with st.sidebar:
    st.header("Settings")
    selected_language = st.selectbox(
        "Select Explanation Language",
        ASSISTIVE_LANGUAGE_OPTIONS,
        index=ASSISTIVE_LANGUAGE_OPTIONS.index(DEFAULT_LANGUAGE)
    )
    st.markdown("---")
    if st.button("Restart Apxmind 🔁"):
        st.session_state.clear()
        st.rerun()

if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": "Hi! I'm Apxmind. How can I help you prepare for the NEET exam today?"}]
if "quiz_state" not in st.session_state:
    st.session_state.quiz_state = {"active": False}

for message in st.session_state.messages:
    avatar = "👩🏽‍⚕️" if message["role"] == "assistant" else "🎓"
    with st.chat_message(message["role"], avatar=avatar):
        st.markdown(message["content"])

if st.session_state.quiz_state.get("active"):
    handle_quiz_ui(selected_language, llm, creative_llm)
else:
    if prompt := st.chat_input("Ask, Learn, & Practice — Master NEET with Apxmind"):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user", avatar="🎓"):
            st.markdown(prompt)

        initial_state = {
            "messages": [HumanMessage(content=prompt)],
            "user_explanation_language": selected_language.lower()
        }

        with st.chat_message("assistant", avatar="👩🏽‍⚕️"):
            with st.status("🤔 Thinking...", expanded=True) as status:
                final_state = {}
                node_to_status = {
                    "agent_router": "🚦 Routing to the correct agent...",
                    "teacher_vectordb_router": "📚 Determining the subject...",
                    "teacher_agent": "👩‍🏫 Engaging the Teacher Agent...",
                    "mcq_question_solver_agent": "✍️ Engaging the MCQ Solver Agent...",
                    "trainer_agent": "📝 Preparing your interactive quiz...",
                    "mentor_agent": "👩🏽‍⚕️ Engaging the Mentor Agent...",
                    "general_query_agent": "🤔 Thinking about your general query..."
                }

                for s in graph.stream(initial_state, {"recursion_limit": 10}):
                    node_name = list(s.keys())[-1]
                    if node_name in node_to_status:
                        status.update(label=node_to_status[node_name])
                        time.sleep(0.5)
                    final_state = s

                if not final_state:
                    status.update(label="⚠️ Error!", state="error", expanded=True)
                    st.error("The agent execution failed to produce a result.")
                else:
                    last_node_name = next(reversed(final_state))
                    if 'response_stream' in final_state[last_node_name]:
                        status.update(label="Generating response...", state="running")
                        response_stream = final_state[last_node_name]['response_stream']
                        full_response = st.write_stream(response_stream)
                        st.session_state.messages.append({"role": "assistant", "content": full_response})

                        if st.session_state.quiz_state.get("active"):
                            st.rerun()
                    else:
                        status.update(label="⚠️ Error!", state="error", expanded=True)
                        st.error("The agent did not produce a valid response.")