"""
APXMIND Vector Store System
===========================

Production-grade semantic retrieval system for offline AI tutoring.

This package provides:
- Intelligent document ingestion (PDF, JSON, TXT)
- Semantic chunking that preserves conceptual boundaries
- Rich metadata enrichment (25+ fields per chunk)
- Quality validation and scoring
- Efficient batch processing with checkpointing
- Hybrid retrieval (semantic + keyword search)
- Performance monitoring and metrics

Architecture:
    Ingest → Preprocess → Chunk → Embed → Store → Retrieve

Target Performance:
    - 1M+ documents supported
    - <500ms retrieval latency
    - Offline-first deployment
    - Resource-aware (runs on 4GB RAM laptops)
"""

__version__ = "2.0.0"
__author__ = "APXMIND Team"

from .config import VectorStoreConfig
from .constants import Subject, ContentType, Difficulty, QueryType

__all__ = [
    "VectorStoreConfig",
    "Subject",
    "ContentType", 
    "Difficulty",
    "QueryType",
]
