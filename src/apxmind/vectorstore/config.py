"""
Centralized Configuration for APXMIND Vector Store System
=========================================================

All tunable parameters in one place for easy optimization and experimentation.
Configuration is environment-aware and can be overridden via env vars.
"""

from dataclasses import dataclass, field
from typing import Dict, List
import os


@dataclass
class ChunkingConfig:
    """
    Configuration for semantic chunking.
    
    Chunking strategy significantly impacts retrieval quality. We use semantic
    chunking that preserves conceptual boundaries rather than naive fixed-size splits.
    """
    
    # Target chunk size in characters (sweet spot for semantic coherence)
    target_size: int = 800
    
    # Minimum chunk size (prevent tiny, context-free fragments)
    min_size: int = 200
    
    # Maximum chunk size (prevent oversized chunks that dilute focus)
    max_size: int = 1500
    
    # Overlap between chunks for context continuity
    overlap: int = 100
    
    # Semantic boundary markers that indicate topic transitions
    boundary_markers: List[str] = field(default_factory=lambda: [
        # Chapter/Section markers
        "Chapter", "Section", "Unit", "Part",
        # Educational markers
        "Definition:", "Theorem:", "Law:", "Principle:",
        "Example:", "Exercise:", "Question:", "Answer:",
        # Structural markers
        "Note:", "Important:", "Remember:", "Summary:",
        "Key Points:", "Objectives:", "Introduction:",
        # NEET-specific markers
        "NEET Pattern:", "Previous Year:", "Concept:",
    ])
    
    # Respect sentence boundaries (don't break mid-sentence)
    respect_sentence_boundaries: bool = True
    
    # Respect paragraph boundaries when possible
    respect_paragraph_boundaries: bool = True
    
    # Minimum sentences per chunk
    min_sentences: int = 2
    
    # Maximum sentences per chunk
    max_sentences: int = 10


@dataclass
class EmbeddingConfig:
    """
    Configuration for embedding generation.
    
    Embeddings are the core of semantic search. We use nomic-embed-text
    for its excellent performance on educational content and offline capability.
    """
    
    # Model name (deployed via Ollama locally)
    model_name: str = "nomic-embed-text"
    
    # Ollama base URL
    ollama_base_url: str = "http://localhost:11434"
    
    # Batch size for embedding generation (balance speed vs memory)
    batch_size: int = 32
    
    # Dimension of embeddings (nomic-embed-text produces 768-dim vectors)
    embedding_dim: int = 768
    
    # Enable embedding cache (significant speedup for re-processing)
    enable_cache: bool = True
    
    # Cache directory for storing computed embeddings
    cache_dir: str = "./cache/embeddings"
    
    # Maximum cache size in MB (LRU eviction when exceeded)
    max_cache_size_mb: int = 1000
    
    # Normalize embeddings to unit length (improves cosine similarity)
    normalize_embeddings: bool = True
    
    # Retry attempts for failed embeddings
    max_retries: int = 3
    
    # Timeout for embedding generation (seconds)
    timeout_seconds: int = 30


@dataclass
class ChromaDBConfig:
    """
    Configuration for ChromaDB vector storage.
    
    ChromaDB is our local-first vector database. We use multiple collections
    for pre-filtering efficiency (10x speedup vs single collection).
    """
    
    # Base directory for all vector databases
    base_path: str = "./src/APXMIND/vectordb"
    
    # Collection names mapped to subjects
    collections: Dict[str, str] = field(default_factory=lambda: {
        'biology': 'chroma_vector_db_biology_nomic',
        'chemistry': 'chroma_vector_db_chemistry_nomic',
        'physics': 'chroma_vector_db_physics_nomic',
        'question_bank': 'chroma_vector_db_questionbank_nomic',
        'mentor': 'chroma_vector_db_mentor_nomic'
    })
    
    # Distance metric for similarity search
    distance_metric: str = "cosine"  # Options: "cosine", "l2", "ip"
    
    # Enable persistence to disk
    persist: bool = True
    
    # Batch size for adding documents to ChromaDB
    batch_size: int = 100
    
    # Enable HNSW index for faster search (vs brute force)
    enable_hnsw: bool = True
    
    # HNSW index parameters (if enabled)
    hnsw_space: str = "cosine"
    hnsw_construction_ef: int = 200  # Higher = better quality, slower build
    hnsw_search_ef: int = 100        # Higher = better recall, slower search
    
    # Maximum elements in collection before warning
    max_elements_warning: int = 1_000_000


@dataclass
class RetrievalConfig:
    """
    Configuration for retrieval operations.
    
    Retrieval is the critical path - must be fast (<500ms) and accurate.
    We use hybrid search combining semantic and keyword matching.
    """
    
    # Number of results to retrieve
    top_k: int = 5
    
    # Minimum relevance score threshold (0-1)
    min_relevance_score: float = 0.7
    
    # Enable hybrid search (semantic + keyword BM25)
    enable_hybrid: bool = True
    
    # Weight for semantic search (0-1)
    semantic_weight: float = 0.7
    
    # Weight for keyword search in hybrid mode (0-1)
    # 0.0 = pure semantic, 1.0 = pure keyword, 0.3 = balanced
    keyword_weight: float = 0.3
    
    # BM25 parameters
    bm25_k1: float = 1.5  # Term frequency saturation
    bm25_b: float = 0.75  # Length normalization
    
    # Enable re-ranking of initial results
    enable_reranking: bool = True
    
    # Re-ranking method
    reranking_method: str = "mmr"  # Options: "mmr", "cross-encoder", "diversity"
    
    # MMR diversity parameter (0-1): 0=relevance only, 1=diversity only
    mmr_diversity_score: float = 0.3
    
    # Target retrieval latency in milliseconds
    target_latency_ms: int = 500
    
    # Enable query expansion (add synonyms, related terms)
    enable_query_expansion: bool = False
    
    # Maximum expanded terms to add
    max_expansion_terms: int = 3
    
    # Filter results by metadata fields
    enable_metadata_filtering: bool = True
    
    # Boost results matching user's difficulty level
    enable_difficulty_boosting: bool = True
    difficulty_boost_factor: float = 1.2


@dataclass
class QualityConfig:
    """
    Configuration for quality validation and scoring.
    
    Quality control prevents low-quality chunks from contaminating the database.
    We score chunks on multiple dimensions: completeness, readability, coherence.
    """
    
    # Minimum quality score for chunks to be stored (0-1)
    min_chunk_quality: float = 0.6
    
    # Minimum text length in characters
    min_text_length: int = 50
    
    # Maximum consecutive whitespace characters
    max_consecutive_whitespace: int = 3
    
    # Minimum word count
    min_word_count: int = 10
    
    # Maximum word count (prevent enormous chunks)
    max_word_count: int = 500
    
    # Language for text analysis
    language: str = "en"
    
    # Enable quality scoring (disable for faster processing in dev)
    enable_quality_scoring: bool = True
    
    # Enable completeness checking (chunk contains full concept)
    enable_completeness_check: bool = True
    
    # Enable readability scoring (Flesch-Kincaid)
    enable_readability_scoring: bool = True
    
    # Target readability grade level (NEET students are 11-12 grade)
    target_grade_level: float = 11.0
    
    # Acceptable readability variance
    grade_level_tolerance: float = 2.0
    
    # Enable coherence checking (semantic flow within chunk)
    enable_coherence_check: bool = True
    
    # Minimum coherence score (0-1)
    min_coherence_score: float = 0.5
    
    # Reject chunks with too many special characters (likely OCR errors)
    max_special_char_ratio: float = 0.15
    
    # Reject chunks that are mostly numbers (likely tables/data)
    max_number_ratio: float = 0.30


@dataclass
class ProcessingConfig:
    """
    Configuration for batch processing and pipeline execution.
    
    Large-scale document processing requires robust error handling,
    checkpointing, and parallelization.
    """
    
    # Batch size for document processing
    batch_size: int = 50
    
    # Enable checkpointing (save progress periodically)
    enable_checkpointing: bool = True
    
    # Checkpoint directory
    checkpoint_dir: str = "./checkpoints"
    
    # Checkpoint interval (save every N batches)
    checkpoint_interval: int = 10
    
    # Number of worker threads for parallel processing
    num_workers: int = 4
    
    # Enable multiprocessing (vs multithreading)
    enable_multiprocessing: bool = False  # False for offline CPU-only
    
    # Maximum retries for failed operations
    max_retries: int = 3
    
    # Retry backoff factor (exponential backoff)
    retry_backoff_factor: float = 2.0
    
    # Timeout for individual operations (seconds)
    operation_timeout: int = 60
    
    # Skip documents that have already been processed
    skip_existing: bool = True
    
    # Validate all data before processing
    enable_validation: bool = True
    
    # Filter low-quality chunks
    filter_low_quality: bool = True
    
    # Minimum quality score threshold (0.0 - 1.0)
    min_quality_score: float = 0.6
    
    # Memory limit per worker (MB) - for resource-constrained environments
    memory_limit_mb: int = 2048
    
    # Graceful shutdown timeout (seconds)
    shutdown_timeout: int = 30


@dataclass
class MonitoringConfig:
    """
    Configuration for monitoring, logging, and metrics collection.
    
    Production systems need observability. We track performance, quality,
    and errors to enable continuous improvement.
    """
    
    # Enable metrics collection
    enable_metrics: bool = True
    
    # Metrics output directory
    metrics_dir: str = "./metrics"
    
    # Log level
    log_level: str = "INFO"  # DEBUG, INFO, WARNING, ERROR, CRITICAL
    
    # Log directory
    log_dir: str = "./logs"
    
    # Log file rotation size (MB)
    log_rotation_size_mb: int = 10
    
    # Number of log files to keep
    log_backup_count: int = 5
    
    # Enable performance tracking (latency, throughput)
    track_performance: bool = True
    
    # Enable quality tracking (chunk quality over time)
    track_quality: bool = True
    
    # Enable error tracking (categorize and count errors)
    track_errors: bool = True
    
    # Performance metrics collection interval (seconds)
    metrics_interval: int = 60
    
    # Enable console output (vs file-only logging)
    console_output: bool = True
    
    # Enable structured logging (JSON format)
    structured_logging: bool = True
    
    # Enable distributed tracing (for debugging pipelines)
    enable_tracing: bool = False
    
    # Metrics export format
    metrics_format: str = "json"  # Options: "json", "csv", "prometheus"


@dataclass
class VectorStoreConfig:
    """
    Master configuration aggregating all sub-configurations.
    
    This is the single entry point for all configuration. Can be loaded
    from environment variables, config files, or instantiated directly.
    
    Example Usage:
        # Load from environment
        config = VectorStoreConfig.from_env()
        
        # Override specific settings
        config.chunking.target_size = 1000
        config.retrieval.top_k = 10
        
        # Access nested configs
        print(config.embedding.model_name)  # "nomic-embed-text"
    """
    
    chunking: ChunkingConfig = field(default_factory=ChunkingConfig)
    embedding: EmbeddingConfig = field(default_factory=EmbeddingConfig)
    chromadb: ChromaDBConfig = field(default_factory=ChromaDBConfig)
    retrieval: RetrievalConfig = field(default_factory=RetrievalConfig)
    quality: QualityConfig = field(default_factory=QualityConfig)
    processing: ProcessingConfig = field(default_factory=ProcessingConfig)
    monitoring: MonitoringConfig = field(default_factory=MonitoringConfig)
    
    @classmethod
    def from_env(cls) -> 'VectorStoreConfig':
        """
        Load configuration from environment variables.
        
        Environment variables override default values. Useful for
        deployment without code changes.
        
        Supported Env Vars:
            EMBEDDING_MODEL: Embedding model name
            VECTORDB_BASE_PATH: Base path for vector databases
            LOG_LEVEL: Logging level
            CHUNK_TARGET_SIZE: Target chunk size
            RETRIEVAL_TOP_K: Number of results to retrieve
            BATCH_SIZE: Processing batch size
            ENABLE_CHECKPOINTING: Enable checkpointing (true/false)
        """
        config = cls()
        
        # Embedding configuration
        if embedding_model := os.getenv("EMBEDDING_MODEL"):
            config.embedding.model_name = embedding_model
        
        if embedding_dim := os.getenv("EMBEDDING_DIM"):
            config.embedding.embedding_dim = int(embedding_dim)
        
        # ChromaDB configuration
        if vectordb_path := os.getenv("VECTORDB_BASE_PATH"):
            config.chromadb.base_path = vectordb_path
        
        # Chunking configuration
        if chunk_size := os.getenv("CHUNK_TARGET_SIZE"):
            config.chunking.target_size = int(chunk_size)
        
        if chunk_overlap := os.getenv("CHUNK_OVERLAP"):
            config.chunking.overlap = int(chunk_overlap)
        
        # Retrieval configuration
        if top_k := os.getenv("RETRIEVAL_TOP_K"):
            config.retrieval.top_k = int(top_k)
        
        if min_score := os.getenv("MIN_RELEVANCE_SCORE"):
            config.retrieval.min_relevance_score = float(min_score)
        
        # Processing configuration
        if batch_size := os.getenv("BATCH_SIZE"):
            config.processing.batch_size = int(batch_size)
        
        if checkpointing := os.getenv("ENABLE_CHECKPOINTING"):
            config.processing.enable_checkpointing = checkpointing.lower() == "true"
        
        # Monitoring configuration
        if log_level := os.getenv("LOG_LEVEL"):
            config.monitoring.log_level = log_level.upper()
        
        if metrics_dir := os.getenv("METRICS_DIR"):
            config.monitoring.metrics_dir = metrics_dir
        
        return config
    
    def to_dict(self) -> Dict:
        """
        Convert configuration to dictionary.
        
        Useful for logging, serialization, and debugging.
        """
        return {
            "chunking": self.chunking.__dict__,
            "embedding": self.embedding.__dict__,
            "chromadb": self.chromadb.__dict__,
            "retrieval": self.retrieval.__dict__,
            "quality": self.quality.__dict__,
            "processing": self.processing.__dict__,
            "monitoring": self.monitoring.__dict__,
        }
    
    def validate(self) -> List[str]:
        """
        Validate configuration for consistency and sanity.
        
        Returns:
            List of validation error messages (empty if valid)
        """
        errors = []
        
        # Chunking validation
        if self.chunking.min_size >= self.chunking.target_size:
            errors.append("min_size must be less than target_size")
        
        if self.chunking.target_size >= self.chunking.max_size:
            errors.append("target_size must be less than max_size")
        
        if self.chunking.overlap >= self.chunking.target_size:
            errors.append("overlap must be less than target_size")
        
        # Embedding validation
        if self.embedding.batch_size < 1:
            errors.append("embedding batch_size must be >= 1")
        
        if self.embedding.embedding_dim not in [384, 768, 1024, 1536]:
            errors.append(f"unusual embedding_dim: {self.embedding.embedding_dim}")
        
        # Retrieval validation
        if not 0 <= self.retrieval.min_relevance_score <= 1:
            errors.append("min_relevance_score must be between 0 and 1")
        
        if not 0 <= self.retrieval.keyword_weight <= 1:
            errors.append("keyword_weight must be between 0 and 1")
        
        # Quality validation
        if not 0 <= self.quality.min_chunk_quality <= 1:
            errors.append("min_chunk_quality must be between 0 and 1")
        
        if self.quality.min_text_length >= self.chunking.min_size:
            errors.append("quality min_text_length should be less than chunking min_size")
        
        # Processing validation
        if self.processing.num_workers < 1:
            errors.append("num_workers must be >= 1")
        
        if self.processing.checkpoint_interval < 1:
            errors.append("checkpoint_interval must be >= 1")
        
        return errors


# Default configuration instance
DEFAULT_CONFIG = VectorStoreConfig()
