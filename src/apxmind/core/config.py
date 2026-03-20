"""
Application Configuration
==========================

Unified Pydantic Settings for the entire APXMIND application.
All settings can be overridden via environment variables with the APXMIND_ prefix,
or via a .env file.

Example:
    APXMIND_LLM_MODEL_PATH=models/gemma-3n.gguf
    APXMIND_PORT=8000
"""

from pathlib import Path
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Central configuration for APXMIND."""

    # ─── LLM (Optimized for Ryzen 3, 8GB RAM) ───────────────────────────
    llm_model_path: str = "models/Llama-3.2-3B-Instruct-Q4_K_M.gguf"
    embedding_model_path: str = "models/nomic-embed-text-v1.5.Q8_0.gguf"
    llm_temperature: float = 0.0
    llm_max_tokens: int = 700
    creative_temperature: float = 0.7
    n_gpu_layers: int = 0    # 0 = strictly use CPU (fixes crashes on non-GPU laptops)
    n_threads: int = 4       # Optimized for Ryzen 3 (Quad Core)
    n_ctx: int = 2048        # Halved context window to keep under 4GB RAM usage

    # Fallback: if llama.cpp models aren't downloaded yet, allow Ollama
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.2"
    embedding_model: str = "nomic-embed-text"
    use_ollama_fallback: bool = True  # True until GGUF models are downloaded

    # ─── Database ───────────────────────────────────────────────────────
    database_url: str = "sqlite+aiosqlite:///APXMIND.db"

    # ─── ChromaDB ───────────────────────────────────────────────────────
    chroma_persist_dir: str = "./src/APXMIND/vectordb"

    # ─── Server ─────────────────────────────────────────────────────────
    host: str = "127.0.0.1"
    port: int = 8000
    debug: bool = False
    cors_origins: str = "http://localhost:5173,http://localhost:3000"

    # ─── Auth ───────────────────────────────────────────────────────────
    jwt_secret: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expiry_hours: int = 24

    # ─── Logging ────────────────────────────────────────────────────────
    log_level: str = "INFO"
    log_file: str = "logs/APXMIND_api.log"

    model_config = {
        "env_file": ".env",
        "env_prefix": "APXMIND_",
        "extra": "ignore",
    }

    @property
    def cors_origin_list(self) -> list[str]:
        """Parse comma-separated CORS origins into a list."""
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]
