"""
Constants and Metadata Schemas for APXMIND Vector Store System
===============================================================

Defines enums, type definitions, and metadata schemas used throughout
the vector store system. This ensures type safety and consistent metadata.
"""

from enum import Enum
from typing import TypedDict, List, Optional
from datetime import datetime


class Subject(str, Enum):
    """
    NEET examination subjects.
    
    Used for collection routing and metadata tagging.
    """
    BIOLOGY = "biology"
    CHEMISTRY = "chemistry"
    PHYSICS = "physics"
    GENERAL = "general"  # For non-subject-specific content


class ContentType(str, Enum):
    """
    Types of educational content for fine-grained categorization.
    
    Helps agents understand what kind of content they're working with
    and how to present it to students.
    """
    EXPLANATION = "explanation"           # Conceptual explanation
    DEFINITION = "definition"             # Term definition
    THEOREM = "theorem"                   # Mathematical theorem/law
    PRINCIPLE = "principle"               # Scientific principle
    LAW = "law"                          # Scientific law
    FORMULA = "formula"                   # Mathematical/chemical formula
    EXAMPLE = "example"                   # Worked example
    EXERCISE = "exercise"                 # Practice problem
    QUESTION = "question"                 # Question (MCQ or descriptive)
    ANSWER = "answer"                     # Answer to a question
    SOLUTION = "solution"                 # Step-by-step solution
    DIAGRAM_DESCRIPTION = "diagram_description"  # Description of a figure
    TABLE_DATA = "table_data"            # Tabular information
    SUMMARY = "summary"                   # Chapter/topic summary
    KEY_POINTS = "key_points"            # Important points list
    TIP = "tip"                          # Study tip or hint
    NOTE = "note"                        # Important note
    INTRODUCTION = "introduction"         # Introductory text
    CONCLUSION = "conclusion"             # Concluding remarks
    REFERENCE = "reference"               # Reference to other content


class Difficulty(str, Enum):
    """
    Content difficulty levels aligned with NEET preparation stages.
    
    Helps in progressive learning and personalized content delivery.
    """
    FOUNDATION = "foundation"       # Basic concepts (Class 11 early)
    BASIC = "basic"                # Standard Class 11 level
    INTERMEDIATE = "intermediate"   # Advanced Class 11 / Basic Class 12
    ADVANCED = "advanced"          # Advanced Class 12
    NEET_LEVEL = "neet_level"      # NEET exam standard
    NEET_ADVANCED = "neet_advanced"  # Difficult NEET questions


class QueryType(str, Enum):
    """
    Types of student queries for intelligent agent routing.
    
    Each query type maps to a specific agent in the multi-agent system.
    """
    TEACH = "teach"          # Request for conceptual explanation → Teacher Agent
    QUIZ = "quiz"            # Request for practice questions → Trainer Agent
    DOUBT = "doubt"          # Specific problem to solve → Doubt Solver Agent
    MENTOR = "mentor"        # Study guidance/strategy → Mentor Agent
    GENERAL = "general"      # General query → General Agent


class Language(str, Enum):
    """
    Supported languages for content and responses.
    
    APXMIND supports multilingual learning for Indian students.
    """
    ENGLISH = "english"
    HINDI = "hindi"
    TAMIL = "tamil"
    TELUGU = "telugu"
    BENGALI = "bengali"
    MARATHI = "marathi"


class ChunkMetadata(TypedDict, total=False):
    """
    Comprehensive metadata schema for each text chunk.
    
    Rich metadata enables:
    - Intelligent routing to correct agents
    - Efficient pre-filtering (10x speed improvement)
    - Quality tracking and monitoring
    - Provenance and audit trails
    - Semantic understanding
    
    Total Fields: 30+
    
    Example:
        metadata = {
            "chunk_id": "bio_class11_ch9_chunk_42",
            "subject": "biology",
            "topic": "Biomolecules",
            "content_type": "explanation",
            "difficulty": "intermediate",
            "quality_score": 0.92,
            ...
        }
    """
    
    # ==========================================
    # CORE IDENTIFICATION (4 fields)
    # ==========================================
    chunk_id: str                       # Unique identifier (e.g., "bio_c11_ch9_chunk_42")
    source_document: str                # Original filename (e.g., "Biology_11th_Ch9.pdf")
    source_path: str                    # Full path to source file
    collection_name: str                # ChromaDB collection (e.g., "biology")
    
    # ==========================================
    # ACADEMIC CLASSIFICATION (7 fields)
    # ==========================================
    subject: str                        # biology/chemistry/physics
    topic: str                          # Main topic (e.g., "Kinematics", "Cell Biology")
    subtopic: str                       # Subtopic (e.g., "Newton's Laws", "Mitochondria")
    chapter: str                        # Chapter name (e.g., "Biomolecules")
    chapter_number: int                 # Chapter number (e.g., 9)
    class_level: int                    # Class 11 or 12
    ncert_book: str                     # NCERT book identifier
    
    # ==========================================
    # CONTENT CHARACTERISTICS (5 fields)
    # ==========================================
    content_type: str                   # explanation/definition/example/question/etc.
    difficulty: str                     # foundation/basic/intermediate/advanced/neet_level
    query_type: str                     # teach/quiz/doubt/mentor (for routing)
    language: str                       # english/hindi/tamil/etc.
    content_category: str               # theory/practical/revision/assessment
    
    # ==========================================
    # STRUCTURAL METADATA (6 fields)
    # ==========================================
    page_number: int                    # Page in source PDF
    page_label: str                     # Page label (e.g., "iii" for roman numerals)
    position_in_document: float         # Relative position 0.0 to 1.0
    chunk_index: int                    # Sequential chunk number from this document
    total_chunks: int                   # Total chunks from this document
    section_title: str                  # Section/subsection title if available
    
    # ==========================================
    # QUALITY METRICS (7 fields)
    # ==========================================
    quality_score: float                # Overall quality score (0.0 to 1.0)
    completeness_score: float           # Does chunk contain full concept?
    readability_score: float            # Flesch-Kincaid or similar
    coherence_score: float              # Semantic coherence within chunk
    has_equations: bool                 # Contains mathematical equations
    has_diagrams_referenced: bool       # References figures/diagrams
    has_tables: bool                    # Contains tabular data
    
    # ==========================================
    # SEMANTIC FEATURES (4 fields)
    # ==========================================
    key_terms: List[str]               # Important terms (e.g., ["protein", "amino acid"])
    entities: List[str]                # Named entities (e.g., ["Newton", "Krebs cycle"])
    concepts: List[str]                # Abstract concepts (e.g., ["energy conservation"])
    keywords: List[str]                # Keywords for BM25 search
    
    # ==========================================
    # PROVENANCE & VERSIONING (5 fields)
    # ==========================================
    created_at: str                    # ISO timestamp of ingestion
    updated_at: str                    # ISO timestamp of last update
    embedding_model: str               # Model used for embedding (e.g., "nomic-embed-text")
    chunking_method: str               # semantic/hybrid/fixed
    processing_version: str            # Version of processing pipeline
    
    # ==========================================
    # TECHNICAL METADATA (4 fields)
    # ==========================================
    chunk_size: int                    # Actual character count
    word_count: int                    # Number of words
    sentence_count: int                # Number of sentences
    token_count: int                   # Approximate token count (for LLM context)
    
    # ==========================================
    # CROSS-REFERENCES (3 fields)
    # ==========================================
    related_chunks: List[str]          # IDs of semantically related chunks
    previous_chunk_id: Optional[str]   # For sequential reading
    next_chunk_id: Optional[str]       # For sequential reading
    
    # ==========================================
    # ADDITIONAL CONTEXT (3 fields)
    # ==========================================
    prerequisites: List[str]            # Required prior knowledge
    learning_objectives: List[str]      # What student should learn
    neet_relevance: str                # How relevant to NEET exam (high/medium/low)


# ==========================================
# EXAMPLE METADATA INSTANCES
# ==========================================

EXAMPLE_METADATA_BIOLOGY: ChunkMetadata = {
    # Core identification
    "chunk_id": "bio_class11_ch9_chunk_042",
    "source_document": "Biology_11th_NCERT_BOOK_Chapter_9.pdf",
    "source_path": "/data/ncert/biology/11/ch9.pdf",
    "collection_name": "biology",
    
    # Academic classification
    "subject": "biology",
    "topic": "Biomolecules",
    "subtopic": "Proteins and Amino Acids",
    "chapter": "Biomolecules",
    "chapter_number": 9,
    "class_level": 11,
    "ncert_book": "NCERT_Biology_Class_11",
    
    # Content characteristics
    "content_type": "explanation",
    "difficulty": "intermediate",
    "query_type": "teach",
    "language": "english",
    "content_category": "theory",
    
    # Structural metadata
    "page_number": 5,
    "page_label": "105",
    "position_in_document": 0.31,
    "chunk_index": 42,
    "total_chunks": 135,
    "section_title": "9.4 Proteins",
    
    # Quality metrics
    "quality_score": 0.92,
    "completeness_score": 0.88,
    "readability_score": 0.75,
    "coherence_score": 0.91,
    "has_equations": False,
    "has_diagrams_referenced": True,
    "has_tables": False,
    
    # Semantic features
    "key_terms": ["protein", "amino acid", "peptide bond", "enzyme", "hemoglobin"],
    "entities": ["hemoglobin", "insulin", "collagen"],
    "concepts": ["protein structure", "denaturation", "enzyme catalysis"],
    "keywords": ["protein", "structure", "function", "amino", "acid"],
    
    # Provenance
    "created_at": "2025-11-01T10:30:00Z",
    "updated_at": "2025-11-01T10:30:00Z",
    "embedding_model": "nomic-embed-text",
    "chunking_method": "semantic",
    "processing_version": "2.0.0",
    
    # Technical metadata
    "chunk_size": 782,
    "word_count": 124,
    "sentence_count": 6,
    "token_count": 156,
    
    # Cross-references
    "related_chunks": ["bio_class11_ch9_chunk_043", "bio_class12_ch3_chunk_012"],
    "previous_chunk_id": "bio_class11_ch9_chunk_041",
    "next_chunk_id": "bio_class11_ch9_chunk_043",
    
    # Additional context
    "prerequisites": ["basic chemistry", "organic compounds"],
    "learning_objectives": ["understand protein structure", "identify amino acids"],
    "neet_relevance": "high"
}


EXAMPLE_METADATA_QUESTION_BANK: ChunkMetadata = {
    "chunk_id": "qbank_neet2024_physics_q_0127",
    "source_document": "NEET_2024_Physics_Solutions.pdf",
    "source_path": "/data/questionbank/neet2024/physics.pdf",
    "collection_name": "question_bank",
    
    "subject": "physics",
    "topic": "Kinematics",
    "subtopic": "Projectile Motion",
    "chapter": "Motion in a Plane",
    "chapter_number": 4,
    "class_level": 11,
    "ncert_book": "NCERT_Physics_Class_11",
    
    "content_type": "question",
    "difficulty": "neet_level",
    "query_type": "quiz",
    "language": "english",
    "content_category": "assessment",
    
    "page_number": 12,
    "page_label": "12",
    "position_in_document": 0.15,
    "chunk_index": 127,
    "total_chunks": 850,
    "section_title": "NEET 2024 Physics - Section A",
    
    "quality_score": 0.95,
    "completeness_score": 1.0,
    "readability_score": 0.80,
    "coherence_score": 0.95,
    "has_equations": True,
    "has_diagrams_referenced": False,
    "has_tables": False,
    
    "key_terms": ["projectile", "range", "velocity", "angle"],
    "entities": [],
    "concepts": ["projectile motion", "range optimization"],
    "keywords": ["projectile", "motion", "maximum", "range", "angle"],
    
    "created_at": "2025-11-01T11:00:00Z",
    "updated_at": "2025-11-01T11:00:00Z",
    "embedding_model": "nomic-embed-text",
    "chunking_method": "semantic",
    "processing_version": "2.0.0",
    
    "chunk_size": 456,
    "word_count": 67,
    "sentence_count": 4,
    "token_count": 89,
    
    "related_chunks": ["qbank_neet2024_physics_q_0126", "qbank_neet2023_physics_q_0089"],
    "previous_chunk_id": "qbank_neet2024_physics_q_0126",
    "next_chunk_id": "qbank_neet2024_physics_q_0128",
    
    "prerequisites": ["basic kinematics", "vector resolution"],
    "learning_objectives": ["apply projectile motion formulas", "optimize launch angle"],
    "neet_relevance": "high"
}


# ==========================================
# METADATA FIELD GROUPS
# ==========================================

REQUIRED_METADATA_FIELDS = [
    "chunk_id",
    "source_document",
    "subject",
    "content_type",
    "created_at",
    "embedding_model",
    "chunk_size"
]

QUALITY_METADATA_FIELDS = [
    "quality_score",
    "completeness_score",
    "readability_score",
    "coherence_score"
]

SEMANTIC_METADATA_FIELDS = [
    "key_terms",
    "entities",
    "concepts",
    "keywords"
]

ROUTING_METADATA_FIELDS = [
    "subject",
    "query_type",
    "difficulty",
    "content_type"
]
