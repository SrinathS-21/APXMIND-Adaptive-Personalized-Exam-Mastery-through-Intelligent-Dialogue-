"""
Data Source Configuration for APXMIND Vector Store
==================================================

Defines paths to raw data sources and their organization.
All data ingestion pipelines should reference this configuration
to ensure consistency.
"""

from pathlib import Path
from typing import Dict, List
from dataclasses import dataclass, field


# Base paths
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent.parent  # APXMIND-main/
RAW_DATA_DIR = PROJECT_ROOT / "Raw Data"
PROCESSED_DATA_DIR = PROJECT_ROOT / "Processed Data"  # For intermediate artifacts
VECTOR_DB_DIR = PROJECT_ROOT / "src" / "APXMIND" / "vectordb"


@dataclass
class DataSourceConfig:
    """Configuration for a single data source."""
    
    name: str                       # Human-readable name
    source_dir: Path                # Directory containing source files
    subject: str                    # biology/chemistry/physics/mentor/question_bank
    file_pattern: str               # Glob pattern for files (e.g., "*.pdf")
    collection_name: str            # ChromaDB collection name
    description: str = ""           # Optional description
    class_level: int = None        # 11 or 12 (for NCERT books)
    recursive: bool = True          # Search subdirectories


# ==========================================
# NCERT BIOLOGY DATA SOURCES
# ==========================================

BIOLOGY_CLASS_11 = DataSourceConfig(
    name="NCERT Biology Class 11",
    source_dir=RAW_DATA_DIR / "NCRTBooks" / "Biology" / "11Bio1",
    subject="biology",
    file_pattern="*.pdf",
    collection_name="chroma_vector_db_biology_nomic",
    description="NCERT Biology textbook for Class 11",
    class_level=11,
    recursive=True
)

BIOLOGY_CLASS_12 = DataSourceConfig(
    name="NCERT Biology Class 12",
    source_dir=RAW_DATA_DIR / "NCRTBooks" / "Biology" / "12Bio1",
    subject="biology",
    file_pattern="*.pdf",
    collection_name="chroma_vector_db_biology_nomic",
    description="NCERT Biology textbook for Class 12",
    class_level=12,
    recursive=True
)

# Aggregate biology sources
BIOLOGY_SOURCES = [BIOLOGY_CLASS_11, BIOLOGY_CLASS_12]


# ==========================================
# NCERT CHEMISTRY DATA SOURCES
# ==========================================

CHEMISTRY_CLASS_11_PART1 = DataSourceConfig(
    name="NCERT Chemistry Class 11 Part 1",
    source_dir=RAW_DATA_DIR / "NCRTBooks" / "chemistry" / "11ChemPart1",
    subject="chemistry",
    file_pattern="*.pdf",
    collection_name="chroma_vector_db_chemistry_nomic",
    description="NCERT Chemistry textbook for Class 11 Part 1",
    class_level=11,
    recursive=True
)

CHEMISTRY_CLASS_11_PART2 = DataSourceConfig(
    name="NCERT Chemistry Class 11 Part 2",
    source_dir=RAW_DATA_DIR / "NCRTBooks" / "chemistry" / "11ChemPart2",
    subject="chemistry",
    file_pattern="*.pdf",
    collection_name="chroma_vector_db_chemistry_nomic",
    description="NCERT Chemistry textbook for Class 11 Part 2",
    class_level=11,
    recursive=True
)

CHEMISTRY_CLASS_12_PART1 = DataSourceConfig(
    name="NCERT Chemistry Class 12 Part 1",
    source_dir=RAW_DATA_DIR / "NCRTBooks" / "chemistry" / "12ChemPart1",
    subject="chemistry",
    file_pattern="*.pdf",
    collection_name="chroma_vector_db_chemistry_nomic",
    description="NCERT Chemistry textbook for Class 12 Part 1",
    class_level=12,
    recursive=True
)

CHEMISTRY_CLASS_12_PART2 = DataSourceConfig(
    name="NCERT Chemistry Class 12 Part 2",
    source_dir=RAW_DATA_DIR / "NCRTBooks" / "chemistry" / "12ChemPart2",
    subject="chemistry",
    file_pattern="*.pdf",
    collection_name="chroma_vector_db_chemistry_nomic",
    description="NCERT Chemistry textbook for Class 12 Part 2",
    class_level=12,
    recursive=True
)

# Aggregate chemistry sources
CHEMISTRY_SOURCES = [
    CHEMISTRY_CLASS_11_PART1,
    CHEMISTRY_CLASS_11_PART2,
    CHEMISTRY_CLASS_12_PART1,
    CHEMISTRY_CLASS_12_PART2
]


# ==========================================
# NCERT PHYSICS DATA SOURCES
# ==========================================

PHYSICS_CLASS_11_PART1 = DataSourceConfig(
    name="NCERT Physics Class 11 Part 1",
    source_dir=RAW_DATA_DIR / "NCRTBooks" / "Physics" / "11Physics1",
    subject="physics",
    file_pattern="*.pdf",
    collection_name="chroma_vector_db_physics_nomic",
    description="NCERT Physics textbook for Class 11 Part 1",
    class_level=11,
    recursive=True
)

PHYSICS_CLASS_11_PART2 = DataSourceConfig(
    name="NCERT Physics Class 11 Part 2",
    source_dir=RAW_DATA_DIR / "NCRTBooks" / "Physics" / "11Physics2",
    subject="physics",
    file_pattern="*.pdf",
    collection_name="chroma_vector_db_physics_nomic",
    description="NCERT Physics textbook for Class 11 Part 2",
    class_level=11,
    recursive=True
)

PHYSICS_CLASS_12_PART1 = DataSourceConfig(
    name="NCERT Physics Class 12 Part 1",
    source_dir=RAW_DATA_DIR / "NCRTBooks" / "Physics" / "12Physics1",
    subject="physics",
    file_pattern="*.pdf",
    collection_name="chroma_vector_db_physics_nomic",
    description="NCERT Physics textbook for Class 12 Part 1",
    class_level=12,
    recursive=True
)

PHYSICS_CLASS_12_PART2 = DataSourceConfig(
    name="NCERT Physics Class 12 Part 2",
    source_dir=RAW_DATA_DIR / "NCRTBooks" / "Physics" / "12Physics2",
    subject="physics",
    file_pattern="*.pdf",
    collection_name="chroma_vector_db_physics_nomic",
    description="NCERT Physics textbook for Class 12 Part 2",
    class_level=12,
    recursive=True
)

# Aggregate physics sources
PHYSICS_SOURCES = [
    PHYSICS_CLASS_11_PART1,
    PHYSICS_CLASS_11_PART2,
    PHYSICS_CLASS_12_PART1,
    PHYSICS_CLASS_12_PART2
]


# ==========================================
# MENTOR GUIDE DATA SOURCES
# ==========================================

MENTOR_GUIDE = DataSourceConfig(
    name="APXMIND Mentor Knowledge Base",
    source_dir=RAW_DATA_DIR / "MentorGuide",
    subject="mentor",
    file_pattern="*.pdf",
    collection_name="chroma_vector_db_mentor_nomic",
    description="Study strategies, tips, and guidance from NEET toppers and experts",
    recursive=False
)

MENTOR_SOURCES = [MENTOR_GUIDE]


# ==========================================
# QUESTION BANK DATA SOURCES
# ==========================================

QUESTION_BANK = DataSourceConfig(
    name="NEET Question Papers",
    source_dir=RAW_DATA_DIR / "QuestionBank",
    subject="question_bank",
    file_pattern="Question_Paper_*.pdf",
    collection_name="chroma_vector_db_questionbank_nomic",
    description="Past NEET exam question papers with solutions",
    recursive=False
)

QUESTION_BANK_SOURCES = [QUESTION_BANK]


# ==========================================
# AGGREGATED CONFIGURATIONS
# ==========================================

ALL_DATA_SOURCES = {
    "biology": BIOLOGY_SOURCES,
    "chemistry": CHEMISTRY_SOURCES,
    "physics": PHYSICS_SOURCES,
    "mentor": MENTOR_SOURCES,
    "question_bank": QUESTION_BANK_SOURCES,
}

# Flattened list of all sources
ALL_SOURCES_FLAT = [
    source
    for sources_list in ALL_DATA_SOURCES.values()
    for source in sources_list
]


def get_sources_by_subject(subject: str) -> List[DataSourceConfig]:
    """
    Get all data sources for a specific subject.
    
    Args:
        subject: One of 'biology', 'chemistry', 'physics', 'mentor', 'question_bank'
    
    Returns:
        List of DataSourceConfig objects
    
    Example:
        sources = get_sources_by_subject('biology')
        for source in sources:
            print(f"Processing {source.name} from {source.source_dir}")
    """
    return ALL_DATA_SOURCES.get(subject, [])


def get_all_subjects() -> List[str]:
    """Get list of all available subjects."""
    return list(ALL_DATA_SOURCES.keys())


def validate_data_sources() -> Dict[str, bool]:
    """
    Validate that all configured data sources exist.
    
    Returns:
        Dictionary mapping source names to existence status
    
    Example:
        validation = validate_data_sources()
        for name, exists in validation.items():
            if not exists:
                print(f"Warning: {name} directory not found")
    """
    validation = {}
    
    for source in ALL_SOURCES_FLAT:
        exists = source.source_dir.exists() and source.source_dir.is_dir()
        validation[source.name] = exists
    
    return validation


def get_source_statistics() -> Dict[str, Dict]:
    """
    Get statistics about available data sources.
    
    Returns:
        Dictionary with counts of files per source
    
    Example:
        stats = get_source_statistics()
        print(f"Biology: {stats['biology']['total_files']} files")
    """
    stats = {}
    
    for subject, sources in ALL_DATA_SOURCES.items():
        total_files = 0
        source_details = []
        
        for source in sources:
            if source.source_dir.exists():
                pattern = f"**/{source.file_pattern}" if source.recursive else source.file_pattern
                files = list(source.source_dir.glob(pattern))
                file_count = len(files)
                total_files += file_count
                
                source_details.append({
                    "name": source.name,
                    "file_count": file_count,
                    "path": str(source.source_dir)
                })
        
        stats[subject] = {
            "total_files": total_files,
            "source_count": len(sources),
            "sources": source_details
        }
    
    return stats


# ==========================================
# LEGACY SUPPORT (DEPRECATED)
# ==========================================

# Note: The old DataPrep-Notebooks and standalone processed files are deprecated.
# All processing should use this configuration and the new vectorstore/ pipeline.

DEPRECATED_PATHS = [
    PROJECT_ROOT / "DataPrep-Notebooks",  # Old notebook-based processing
    PROCESSED_DATA_DIR / "processed_biology_chunks.json",  # Old chunking format
    PROCESSED_DATA_DIR / "processed_chemistry_chunks.json",
    PROCESSED_DATA_DIR / "processed_physics_chunks.json",
    PROCESSED_DATA_DIR / "solved_question_papers.json",
    PROCESSED_DATA_DIR / "mentor_data.json",
]


def check_deprecated_files() -> List[Path]:
    """
    Check for deprecated data processing files that should be removed.
    
    Returns:
        List of deprecated files/directories that exist
    """
    return [path for path in DEPRECATED_PATHS if path.exists()]


if __name__ == "__main__":
    # Validation and statistics when run as script
    print("=" * 60)
    print("APXMIND Data Source Validation")
    print("=" * 60)
    print()
    
    # Validate sources
    print("Validating data sources...")
    validation = validate_data_sources()
    all_valid = all(validation.values())
    
    for name, exists in validation.items():
        status = "✅" if exists else "❌"
        print(f"{status} {name}")
    
    print()
    
    if not all_valid:
        print("⚠️  Warning: Some data sources are missing!")
        print("   Please ensure all NCERT books and question papers are in Raw Data/")
    else:
        print("✅ All data sources found!")
    
    print()
    print("=" * 60)
    print("Data Source Statistics")
    print("=" * 60)
    print()
    
    stats = get_source_statistics()
    total_files = sum(s["total_files"] for s in stats.values())
    
    for subject, info in stats.items():
        print(f"{subject.upper()}:")
        print(f"  Total files: {info['total_files']}")
        print(f"  Sources: {info['source_count']}")
        for source in info['sources']:
            print(f"    - {source['name']}: {source['file_count']} files")
        print()
    
    print(f"TOTAL: {total_files} files across {len(ALL_SOURCES_FLAT)} sources")
    print()
    
    # Check for deprecated files
    deprecated = check_deprecated_files()
    if deprecated:
        print("=" * 60)
        print("⚠️  Deprecated Files Found")
        print("=" * 60)
        print()
        print("The following old data processing artifacts were found:")
        for path in deprecated:
            print(f"  - {path}")
        print()
        print("These should be removed to avoid confusion.")
        print("The new vectorstore/ system replaces all old processing.")
    else:
        print("✅ No deprecated files found - clean workspace!")
