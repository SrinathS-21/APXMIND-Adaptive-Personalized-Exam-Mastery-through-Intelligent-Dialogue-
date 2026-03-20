"""
LlamaEngine
=============

Unified LLM engine wrapping llama-cpp-python.
Provides chat completion, streaming, structured output, and embeddings.

This is a standalone utility — the LangChain ChatLlamaCpp is used for
agent/chain compatibility. LlamaEngine is for direct low-level access.
"""

import json
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class LlamaEngine:
    """
    Low-level llama.cpp wrapper for direct model access.
    
    For LangChain chain/agent usage, use ChatLlamaCpp instead.
    This class is useful for:
    - Embedding generation
    - Structured JSON output
    - Direct streaming without LangChain overhead
    """

    def __init__(
        self,
        model_path: str,
        embedding_model_path: Optional[str] = None,
        n_gpu_layers: int = 0,
        n_ctx: int = 2048,
        n_threads: int = 4,
        verbose: bool = False,
    ):
        try:
            from llama_cpp import Llama
        except ImportError:
            raise ImportError(
                "llama-cpp-python is required. Install with: pip install llama-cpp-python"
            )

        # Chat model
        logger.info(f"Loading chat model: {model_path} with {n_threads} threads and {n_gpu_layers} GPU layers.")
        self._chat_model = Llama(
            model_path=str(model_path),
            n_gpu_layers=n_gpu_layers,
            n_ctx=n_ctx,
            n_threads=n_threads,
            verbose=verbose,
            chat_format="chatml-function-calling",
        )

        # Embedding model (optional, separate GGUF)
        self._embed_model = None
        if embedding_model_path and Path(embedding_model_path).exists():
            logger.info(f"Loading embedding model: {embedding_model_path}")
            self._embed_model = Llama(
                model_path=str(embedding_model_path),
                n_gpu_layers=n_gpu_layers,
                n_threads=n_threads,
                embedding=True,
                verbose=verbose,
            )

        logger.info("LlamaEngine initialized")

    def chat(
        self,
        messages: list[dict],
        temperature: float = 0.0,
        max_tokens: int = 700,
    ) -> str:
        """Chat completion — returns full response text."""
        response = self._chat_model.create_chat_completion(
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return response["choices"][0]["message"]["content"]

    def chat_stream(
        self,
        messages: list[dict],
        temperature: float = 0.0,
        max_tokens: int = 700,
    ):
        """Streaming chat — yields tokens one by one."""
        stream = self._chat_model.create_chat_completion(
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=True,
        )
        for chunk in stream:
            delta = chunk["choices"][0].get("delta", {})
            content = delta.get("content", "")
            if content:
                yield content

    def structured_output(
        self,
        messages: list[dict],
        schema: dict,
        temperature: float = 0.0,
    ) -> dict:
        """JSON Schema constrained output — for routing decisions."""
        response = self._chat_model.create_chat_completion(
            messages=messages,
            temperature=temperature,
            response_format={
                "type": "json_object",
                "schema": schema,
            },
        )
        return json.loads(response["choices"][0]["message"]["content"])

    def embed(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for a list of texts."""
        if self._embed_model is None:
            raise RuntimeError("No embedding model loaded")
        result = self._embed_model.create_embedding(texts)
        return [item["embedding"] for item in result["data"]]

    def close(self):
        """Release model resources."""
        if hasattr(self, "_chat_model"):
            del self._chat_model
        if hasattr(self, "_embed_model") and self._embed_model:
            del self._embed_model
        logger.info("LlamaEngine closed")
