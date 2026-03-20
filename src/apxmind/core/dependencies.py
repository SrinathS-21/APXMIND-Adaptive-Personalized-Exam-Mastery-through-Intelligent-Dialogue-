"""
FastAPI Dependency Injection
=============================

Centralized resource providers for the APXMIND application.
Resources are initialized once during app startup (lifespan) and
injected into route handlers via FastAPI's Depends().
"""

import logging
from functools import lru_cache
from .config import Settings

logger = logging.getLogger(__name__)

# ─── Global singletons (set during startup) ────────────────────────────────
_llm = None
_creative_llm = None
_vectorstores: dict = {}
_pipeline = None


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the cached Settings instance."""
    return Settings()


async def init_resources(settings: Settings):
    """
    Initialize all shared resources at app startup.
    Called from FastAPI lifespan context manager.
    """
    global _llm, _creative_llm, _vectorstores

    # 1. Initialize database
    from ..db.session import init_db_engine, create_tables
    init_db_engine(settings)
    await create_tables()
    logger.info("Database initialized")

    # 2. Initialize LLM
    _init_llm(settings)
    logger.info("LLM initialized")

    # 3. Load vectorstores
    _vectorstores = _load_vectorstores(settings)
    logger.info(f"Vectorstores loaded: {list(_vectorstores.keys())}")


def _init_llm(settings: Settings):
    """Initialize LLM instances based on available backend."""
    global _llm, _creative_llm

    try:
        from langchain_community.chat_models import ChatLlamaCpp
        from pathlib import Path

        model_path = Path(settings.llm_model_path)
        if model_path.exists():
            logger.info(f"Loading llama.cpp model: {model_path}")
            _llm = ChatLlamaCpp(
                model_path=str(model_path),
                n_gpu_layers=settings.n_gpu_layers,
                n_ctx=settings.n_ctx,
                n_threads=settings.n_threads,
                temperature=settings.llm_temperature,
                max_tokens=settings.llm_max_tokens,
                chat_format="chatml-function-calling",
                verbose=False,
            )
            _creative_llm = ChatLlamaCpp(
                model_path=str(model_path),
                n_gpu_layers=settings.n_gpu_layers,
                n_ctx=settings.n_ctx,
                n_threads=settings.n_threads,
                temperature=settings.creative_temperature,
                max_tokens=settings.llm_max_tokens,
                chat_format="chatml-function-calling",
                verbose=False,
            )
            logger.info("llama.cpp models loaded successfully")
        else:
            logger.warning(f"GGUF model not found at {model_path}, falling back to Ollama")
            _init_ollama_fallback(settings)
    except ImportError:
        logger.warning("ChatLlamaCpp not available, falling back to Ollama")
        _init_ollama_fallback(settings)
    except Exception as e:
        logger.warning(f"Failed to load llama.cpp model: {e}, falling back to Ollama")
        _init_ollama_fallback(settings)

    # Inject into the llm module so that agent code (get_llm()) works
    from ..llm.llm import init_llm
    init_llm(_llm, _creative_llm)


def _init_ollama_fallback(settings: Settings):
    """Fall back to Ollama while GGUF models aren't downloaded yet."""
    global _llm, _creative_llm

    from langchain_ollama import ChatOllama

    _llm = ChatOllama(
        model=settings.ollama_model,
        temperature=settings.llm_temperature,
        max_tokens=settings.llm_max_tokens,
        base_url=settings.ollama_base_url,
    )
    _creative_llm = ChatOllama(
        model=settings.ollama_model,
        temperature=settings.creative_temperature,
        base_url=settings.ollama_base_url,
    )
    logger.info(f"Ollama fallback initialized: {settings.ollama_model}")


def _load_vectorstores(settings: Settings) -> dict:
    """Load LangChain Chroma vectorstores for all subjects."""
    stores = {}
    try:
        from langchain_community.vectorstores import Chroma
        from langchain_community.embeddings import OllamaEmbeddings

        embedding_fn = OllamaEmbeddings(
            model=settings.embedding_model,
            base_url=settings.ollama_base_url,
        )

        # Map subject → ChromaDB collection name (must match what was ingested)
        collection_map = {
            "biology": "APXMIND_biology",
            "chemistry": "APXMIND_chemistry",
            "physics": "APXMIND_physics",
            "question_bank": "APXMIND_question_bank",
            "mentor": "APXMIND_mentor",
        }

        persist_dir = settings.chroma_persist_dir

        for subject, col_name in collection_map.items():
            try:
                store = Chroma(
                    collection_name=col_name,
                    persist_directory=persist_dir,
                    embedding_function=embedding_fn,
                )
                # Quick sanity check — count docs (0 is fine, error is not)
                store._collection.count()
                stores[subject] = store
                logger.info(f"Vectorstore loaded: {subject} ({col_name})")
            except Exception as e:
                logger.warning(f"Failed to load vectorstore '{subject}': {e}")
    except ImportError as e:
        logger.error(f"ChromaDB/Embeddings import failed: {e}")
    except Exception as e:
        logger.error(f"Failed to initialize vectorstores: {e}")

    return stores


async def cleanup_resources():
    """Release all resources at app shutdown."""
    from ..db.session import close_db
    await close_db()
    logger.info("Resources cleaned up")


# ─── Dependency providers (for FastAPI Depends) ────────────────────────────

def get_llm():
    """Get the primary LLM instance."""
    if _llm is None:
        raise RuntimeError("LLM not initialized")
    return _llm


def get_creative_llm():
    """Get the creative LLM instance."""
    if _creative_llm is None:
        raise RuntimeError("Creative LLM not initialized")
    return _creative_llm


def get_vectorstores() -> dict:
    """Get all loaded vectorstores."""
    return _vectorstores


def get_vectorstore(subject: str):
    """Get vectorstore for a specific subject."""
    return _vectorstores.get(subject.lower())
