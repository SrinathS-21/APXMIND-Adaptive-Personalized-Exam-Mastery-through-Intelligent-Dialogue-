"""
LLM Module
==========

Centralized LLM initialization.
Provides access to chat and creative LLM instances via dependency injection.

Migrated from Ollama + Streamlit to llama-cpp-python.
"""

import logging

logger = logging.getLogger(__name__)

# Module-level references set during app startup via init_llm()
_llm_instance = None
_creative_llm_instance = None


def init_llm(llm, creative_llm=None):
    """
    Initialize LLM instances. Called once at app startup.

    Args:
        llm: Primary LLM (ChatLlamaCpp or compatible LangChain chat model)
        creative_llm: Creative LLM for quiz generation (higher temperature)
    """
    global _llm_instance, _creative_llm_instance
    _llm_instance = llm
    _creative_llm_instance = creative_llm or llm
    logger.info("LLM instances initialized")


def get_llm():
    """Get the primary LLM instance (temperature=0, precise answers)."""
    if _llm_instance is None:
        raise RuntimeError(
            "LLM not initialized. Call init_llm() during app startup."
        )
    return _llm_instance


def get_creative_llm():
    """Get the creative LLM instance (temperature=0.7, quiz generation)."""
    if _creative_llm_instance is None:
        raise RuntimeError(
            "Creative LLM not initialized. Call init_llm() during app startup."
        )
    return _creative_llm_instance
