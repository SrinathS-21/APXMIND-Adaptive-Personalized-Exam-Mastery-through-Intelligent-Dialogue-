"""
Model Manager
==============

Downloads GGUF models from HuggingFace Hub on first run.
Provides progress tracking for the UI to display download status.
"""

import logging
from pathlib import Path
from typing import Optional, Callable

logger = logging.getLogger(__name__)

# Default model configurations
MODELS = {
    "chat": {
        "repo_id": "google/gemma-3n-E4B-it-GGUF",
        "filename": "gemma-3n-e4b-it-q4_k_m.gguf",
        "description": "Gemma 3n chat model (Q4_K_M quantization)",
        "size_gb": 2.5,
    },
    "embedding": {
        "repo_id": "nomic-ai/nomic-embed-text-v1.5-GGUF",
        "filename": "nomic-embed-text-v1.5.Q8_0.gguf",
        "description": "Nomic Embed Text v1.5 (Q8_0 quantization)",
        "size_gb": 0.14,
    },
}


def get_model_status(models_dir: Path = Path("models")) -> dict:
    """
    Check which models are downloaded.
    
    Returns:
        Dict mapping model name to {"downloaded": bool, "path": str, "size_gb": float}
    """
    status = {}
    for name, info in MODELS.items():
        target = models_dir / info["filename"]
        status[name] = {
            "downloaded": target.exists(),
            "path": str(target),
            "filename": info["filename"],
            "description": info["description"],
            "size_gb": info["size_gb"],
        }
    return status


def ensure_models_downloaded(
    models_dir: Path = Path("models"),
    progress_callback: Optional[Callable[[str, float], None]] = None,
) -> dict:
    """
    Download models on first run if not present.
    
    Args:
        models_dir: Directory to store models
        progress_callback: Optional callback(model_name, progress_fraction)
    
    Returns:
        Dict mapping model name to local file path
    """
    models_dir.mkdir(parents=True, exist_ok=True)
    paths = {}

    for name, info in MODELS.items():
        target = models_dir / info["filename"]

        if target.exists():
            logger.info(f"Model '{name}' already present: {target}")
            paths[name] = str(target)
            continue

        logger.info(
            f"Downloading model '{name}' ({info['size_gb']:.1f} GB) from HuggingFace..."
        )

        try:
            from huggingface_hub import hf_hub_download

            local_path = hf_hub_download(
                repo_id=info["repo_id"],
                filename=info["filename"],
                local_dir=str(models_dir),
            )
            paths[name] = local_path
            logger.info(f"Model '{name}' downloaded: {local_path}")

            if progress_callback:
                progress_callback(name, 1.0)

        except ImportError:
            logger.error(
                "huggingface-hub is required for model download. "
                "Install with: pip install huggingface-hub"
            )
            raise
        except Exception as e:
            logger.error(f"Failed to download model '{name}': {e}")
            raise

    return paths


def list_available_models(models_dir: Path = Path("models")) -> list[dict]:
    """List all GGUF files in the models directory."""
    if not models_dir.exists():
        return []

    return [
        {
            "filename": f.name,
            "path": str(f),
            "size_mb": round(f.stat().st_size / (1024 * 1024), 1),
        }
        for f in models_dir.glob("*.gguf")
    ]
