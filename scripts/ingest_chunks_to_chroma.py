"""
Ingest chunk JSON files into Chroma collections used by APXMIND backend.

Purpose
-------
- Reads preprocessed chunk files from data/vectorstore.
- Populates APXMIND_* Chroma collections.
- Supports reset + idempotent upsert.

Usage
-----
python scripts/ingest_chunks_to_chroma.py
python scripts/ingest_chunks_to_chroma.py --chunks-dir data/vectorstore --persist-dir data/vectorstore --batch-size 64 --no-reset
"""

from __future__ import annotations

import argparse
import json
import hashlib
from pathlib import Path
from typing import Any, Dict, List, Tuple

import chromadb
from chromadb.config import Settings
from chromadb.utils import embedding_functions


FILE_TO_COLLECTION: Dict[str, str] = {
    "biology_chunks.json": "APXMIND_biology",
    "chemistry_chunks.json": "APXMIND_chemistry",
    "physics_chunks.json": "APXMIND_physics",
    "question_bank_chunks.json": "APXMIND_question_bank",
    "mentor_guide_chunks.json": "APXMIND_mentor",
}


def _to_scalar_metadata(metadata: Dict[str, Any]) -> Dict[str, Any]:
    """Convert metadata values to Chroma-supported scalar types."""
    out: Dict[str, Any] = {}
    for key, value in metadata.items():
        if value is None:
            continue
        if isinstance(value, (str, int, float, bool)):
            out[str(key)] = value
            continue
        if isinstance(value, list):
            out[str(key)] = ",".join(str(v) for v in value)
            continue
        out[str(key)] = str(value)
    return out


def _load_chunk_file(path: Path) -> List[Dict[str, Any]]:
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    chunks = data.get("chunks", [])
    if not isinstance(chunks, list):
        raise ValueError(f"Invalid chunks format in {path}")
    return chunks


def _prepare_batch(
    chunks: List[Dict[str, Any]],
    seen_ids: set[str],
    id_offset: int = 0,
) -> Tuple[List[str], List[str], List[Dict[str, Any]]]:
    ids: List[str] = []
    docs: List[str] = []
    metas: List[Dict[str, Any]] = []

    for i, chunk in enumerate(chunks):
        content = str(chunk.get("content") or "").strip()
        if not content:
            continue

        metadata = chunk.get("metadata") if isinstance(chunk.get("metadata"), dict) else {}
        prepared_meta = _to_scalar_metadata(metadata)

        base_id = str(chunk.get("id") or f"chunk_{id_offset + i}")
        source = str(metadata.get("source") or "")
        source_suffix = hashlib.md5(source.encode("utf-8")).hexdigest()[:8] if source else f"i{id_offset + i}"
        candidate_id = f"{base_id}__{source_suffix}"

        # Ensure uniqueness within collection even when source/hash collisions occur.
        if candidate_id in seen_ids:
            candidate_id = f"{candidate_id}__{id_offset + i}"
            dedupe_counter = 1
            while candidate_id in seen_ids:
                dedupe_counter += 1
                candidate_id = f"{base_id}__{source_suffix}__{id_offset + i}__{dedupe_counter}"

        seen_ids.add(candidate_id)

        quality_score = chunk.get("quality_score")
        if isinstance(quality_score, (int, float)):
            prepared_meta["quality_score"] = float(quality_score)

        tokens = chunk.get("tokens")
        if isinstance(tokens, int):
            prepared_meta["tokens"] = tokens

        ids.append(candidate_id)
        docs.append(content)
        metas.append(prepared_meta)

    return ids, docs, metas


def ingest(
    chunks_dir: Path,
    persist_dir: Path,
    embedding_model: str,
    ollama_base_url: str,
    batch_size: int,
    reset_collections: bool,
) -> None:
    if not chunks_dir.exists():
        raise FileNotFoundError(f"Chunks directory not found: {chunks_dir}")

    persist_dir.mkdir(parents=True, exist_ok=True)

    client = chromadb.PersistentClient(
        path=str(persist_dir),
        settings=Settings(anonymized_telemetry=False, allow_reset=True),
    )

    embed_fn = embedding_functions.OllamaEmbeddingFunction(
        url=f"{ollama_base_url.rstrip('/')}/api/embeddings",
        model_name=embedding_model,
    )

    print("=" * 72)
    print("APXMIND Chroma Ingestion")
    print("=" * 72)
    print(f"Chunks dir : {chunks_dir}")
    print(f"Persist dir: {persist_dir}")
    print(f"Embedding  : {embedding_model} @ {ollama_base_url}")
    print(f"Reset      : {reset_collections}")
    print()

    grand_total = 0
    for filename, collection_name in FILE_TO_COLLECTION.items():
        input_file = chunks_dir / filename
        if not input_file.exists():
            print(f"[SKIP] {filename} (missing)")
            continue

        chunks = _load_chunk_file(input_file)
        print(f"[LOAD] {filename}: {len(chunks)} raw chunks")

        if reset_collections:
            try:
                client.delete_collection(collection_name)
                print(f"       reset collection {collection_name}")
            except Exception:
                # It's fine if collection doesn't exist yet.
                pass

        collection = client.get_or_create_collection(
            name=collection_name,
            embedding_function=embed_fn,
            metadata={"source": str(input_file), "collection": collection_name},
        )

        upserted = 0
        seen_ids: set[str] = set()
        for i in range(0, len(chunks), batch_size):
            batch = chunks[i:i + batch_size]
            ids, docs, metas = _prepare_batch(batch, seen_ids=seen_ids, id_offset=i)
            if not ids:
                continue
            collection.upsert(ids=ids, documents=docs, metadatas=metas)
            upserted += len(ids)

        count = collection.count()
        grand_total += count
        print(f"       upserted={upserted}, collection_count={count}")

    print()
    print("=" * 72)
    print(f"Done. Total documents across loaded collections: {grand_total}")
    print("=" * 72)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Ingest APXMIND chunk JSON files into Chroma")
    parser.add_argument("--chunks-dir", default="data/vectorstore", help="Directory containing *_chunks.json files")
    parser.add_argument("--persist-dir", default="data/vectorstore", help="Chroma persist directory")
    parser.add_argument("--embedding-model", default="nomic-embed-text", help="Ollama embedding model name")
    parser.add_argument("--ollama-base-url", default="http://localhost:11434", help="Ollama base URL")
    parser.add_argument("--batch-size", type=int, default=64, help="Upsert batch size")
    parser.add_argument("--no-reset", action="store_true", help="Do not reset collections before ingest")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    ingest(
        chunks_dir=Path(args.chunks_dir),
        persist_dir=Path(args.persist_dir),
        embedding_model=args.embedding_model,
        ollama_base_url=args.ollama_base_url,
        batch_size=args.batch_size,
        reset_collections=not args.no_reset,
    )
