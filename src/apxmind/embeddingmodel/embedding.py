import os
import streamlit as st
from langchain_community.embeddings import OllamaEmbeddings

@st.cache_resource
def get_embeddings():
    """Initializes and returns the OllamaEmbeddings instance."""
    return OllamaEmbeddings(model=os.getenv("EMBEDDING_MODEL"))