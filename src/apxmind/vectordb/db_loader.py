import os
import streamlit as st
from langchain_community.vectorstores import Chroma
from ..config import VECTOR_DB_CONFIGS

@st.cache_resource
def load_vector_stores(_embeddings):
    """
    Loads all Chroma vector stores specified in the config.

    Args:
        _embeddings: The embedding function to use for the vector stores.

    Returns:
        A tuple containing:
        - A dictionary of loaded vector stores.
        - A list of log messages about the loading process.
    """
    base_path = os.getenv("VECTORDB_BASE_PATH")
    vector_stores = {}
    log_messages = []

    for subject, db_name in VECTOR_DB_CONFIGS.items():
        persist_dir = os.path.join(base_path, db_name)
        if not os.path.exists(persist_dir):
            log_messages.append(f"⚠️ **Warning:** Knowledge base for '{subject}' not found.")
            continue
        try:
            vector_stores[subject] = Chroma(persist_directory=persist_dir, embedding_function=_embeddings)
            log_messages.append(f"✅ Successfully loaded knowledge base for **{subject}**.")
        except Exception as e:
            log_messages.append(f"❌ **Error:** Failed to load knowledge base for '{subject}'. Details: {e}")
            
    return vector_stores, log_messages