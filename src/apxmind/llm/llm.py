import os
import streamlit as st
from langchain_ollama import ChatOllama

# A cached function to load and initialize the primary LLM.
# Caching prevents re-loading the model on every script rerun.
@st.cache_resource
def get_llm():
    """Initializes and returns the primary ChatOllama instance."""
    llm = ChatOllama(
        model=os.getenv("LLM_MODEL"), 
        temperature=0, 
        max_tokens=700
    )
    # A quick invocation to check for connection errors early.
    try:
        llm.invoke("Test")
    except Exception as e:
        st.error(f"**Fatal Error: Could not connect to Ollama LLM.**\nPlease ensure Ollama is running and the model '{os.getenv('LLM_MODEL')}' is available.\n\n**Details:** {e}", icon="🚨")
        st.stop()
    return llm

# A cached function to load the 'creative' LLM used for quiz generation.
@st.cache_resource
def get_creative_llm():
    """Initializes and returns the creative ChatOllama instance with higher temperature."""
    creative_llm = ChatOllama(
        model=os.getenv("CREATIVE_LLM_MODEL"),
        temperature=0.7
    )
    return creative_llm