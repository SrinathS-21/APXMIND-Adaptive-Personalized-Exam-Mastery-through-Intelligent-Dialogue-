"""
Core Resources (DEPRECATED)
=============================

⚠️  DEPRECATED — kept for backward compatibility only.
New code should import from:
    - core.dependencies  (FastAPI DI providers)
    - llm.llm            (get_llm / get_creative_llm)

This module now delegates to the new DI system when it is initialised,
falling back to the legacy Ollama-direct path only if the new system
has not yet been bootstrapped (e.g. running old Flask code).
"""

import os
import logging
from typing import Dict, Optional, Union
from functools import lru_cache

logger = logging.getLogger(__name__)

# Try to import ChromaDB, fall back to mock if not available
try:
    from langchain_community.vectorstores import Chroma
    CHROMADB_AVAILABLE = True
except ImportError:
    CHROMADB_AVAILABLE = False
    logger.warning("ChromaDB not available - using MockVectorStore fallback")

from .mock_vectorstore import get_mock_vectorstore, MockVectorStore


# ============================================================================
# LLM — delegate to new DI system when available
# ============================================================================

def get_llm():
    """Return primary LLM (delegates to new llm module, falls back to Ollama)."""
    try:
        from ..llm.llm import get_llm as _new_get_llm
        return _new_get_llm()
    except RuntimeError:
        pass  # Not yet initialised — fall through to legacy
    return _legacy_get_llm()


def get_creative_llm():
    """Return creative LLM (delegates to new llm module, falls back to Ollama)."""
    try:
        from ..llm.llm import get_creative_llm as _new_get_creative
        return _new_get_creative()
    except RuntimeError:
        pass
    return _legacy_get_creative_llm()


@lru_cache(maxsize=1)
def _legacy_get_llm():
    from langchain_ollama import ChatOllama
    llm = ChatOllama(
        model=os.getenv("APXMIND_OLLAMA_MODEL", os.getenv("LLM_MODEL", "llama3.2:3b")),
        temperature=0,
        max_tokens=700,
        base_url=os.getenv("APXMIND_OLLAMA_BASE_URL", os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")),
    )
    logger.info(f"Legacy LLM initialised: {llm.model}")
    return llm


@lru_cache(maxsize=1)
def _legacy_get_creative_llm():
    from langchain_ollama import ChatOllama
    llm = ChatOllama(
        model=os.getenv("APXMIND_OLLAMA_MODEL", os.getenv("CREATIVE_LLM_MODEL", "llama3.2:3b")),
        temperature=0.7,
        base_url=os.getenv("APXMIND_OLLAMA_BASE_URL", os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")),
    )
    logger.info(f"Legacy creative LLM initialised: {llm.model}")
    return llm


# ============================================================================
# VECTORSTORE INITIALIZATION
# ============================================================================

# Global cache for vectorstores
_vectorstore_cache: Dict[str, Union['Chroma', MockVectorStore]] = {}


def get_vectorstore(subject: str) -> Union['Chroma', MockVectorStore, None]:
    """
    Get vectorstore for a specific subject.
    Falls back to MockVectorStore if ChromaDB is not available.
    
    Args:
        subject: Subject name (biology, chemistry, physics, question_bank, mentor)
    
    Returns:
        Chroma vectorstore instance, MockVectorStore, or None if not found
    """
    global _vectorstore_cache
    
    # Normalize subject name
    subject = subject.lower()
    
    # Check cache
    if subject in _vectorstore_cache:
        return _vectorstore_cache[subject]
    
    # If ChromaDB not available, use mock vectorstore
    if not CHROMADB_AVAILABLE:
        logger.warning(f"ChromaDB not available - using MockVectorStore for '{subject}'")
        mock_store = get_mock_vectorstore(subject)
        _vectorstore_cache[subject] = mock_store
        return mock_store
    
    # Try to load real ChromaDB vectorstore
    try:
        # Import here to avoid circular dependency
        from ..vectorstore.storage.chroma_manager import ChromaDBManager
        from langchain_community.embeddings import OllamaEmbeddings
        
        # Get embedding function
        embedding_function = OllamaEmbeddings(
            model=os.getenv("EMBEDDING_MODEL", "nomic-embed-text"),
            base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        )
        
        # Initialize ChromaDB manager
        chroma_manager = ChromaDBManager()
        
        # Get collection for subject
        vectorstore = chroma_manager.get_collection(subject, embedding_function)
        
        if vectorstore:
            _vectorstore_cache[subject] = vectorstore
            logger.info(f"Vectorstore loaded for subject: {subject}")
            return vectorstore
        else:
            logger.warning(f"No vectorstore found for subject: {subject}, using MockVectorStore")
            mock_store = get_mock_vectorstore(subject)
            _vectorstore_cache[subject] = mock_store
            return mock_store
            
    except Exception as e:
        logger.error(f"Failed to load vectorstore for {subject}: {e}")
        logger.warning(f"Falling back to MockVectorStore for '{subject}'")
        mock_store = get_mock_vectorstore(subject)
        _vectorstore_cache[subject] = mock_store
        return mock_store


def get_all_vectorstores() -> Dict[str, Union['Chroma', MockVectorStore]]:
    """
    Get all available vectorstores.
    Falls back to MockVectorStore if ChromaDB is not available.
    
    Returns:
        Dictionary mapping subject names to vectorstore instances
    """
    subjects = ['biology', 'chemistry', 'physics', 'question_bank', 'mentor']
    
    vectorstores = {}
    for subject in subjects:
        store = get_vectorstore(subject)
        if store:
            vectorstores[subject] = store
    
    logger.info(f"Loaded {len(vectorstores)} vectorstores: {list(vectorstores.keys())}")
    return vectorstores


def clear_vectorstore_cache():
    """Clear the vectorstore cache."""
    global _vectorstore_cache
    _vectorstore_cache.clear()
    logger.info("Vectorstore cache cleared")
