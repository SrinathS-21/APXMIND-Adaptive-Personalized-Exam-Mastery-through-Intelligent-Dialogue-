"""
NEET Content Ingestion Script
==============================

Uses the existing vectorstore infrastructure to process NCERT PDFs
and create vector embeddings for semantic search.

This script:
1. Loads PDFs from Raw Data/NCRTBooks
2. Chunks content intelligently 
3. Enriches with metadata
4. Creates embeddings using Ollama
5. Stores in JSON format (ChromaDB alternative for Python 3.14)

Author: APXMIND Team
Date: November 2, 2025
"""

import sys
import os
from pathlib import Path
import json
import logging
from typing import List, Dict, Any
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.apxmind.vectorstore.ingestion.pdf_loader import PDFLoader
from src.apxmind.vectorstore.ingestion.batch_processor import BatchProcessor
from src.apxmind.vectorstore.chunking.semantic_chunker import SemanticChunker
from src.apxmind.vectorstore.preprocessing import MetadataEnricher, QualityValidator
from src.apxmind.vectorstore.constants import Subject
from src.apxmind.vectorstore.config import ProcessingConfig

# Setup logging with UTF-8 encoding
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('neet_ingestion.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class NEETDataIngestion:
    """Orchestrates NEET data ingestion pipeline."""
    
    def __init__(self, raw_data_dir: str = "Raw Data", output_dir: str = "vectorstore_data"):
        """
        Initialize ingestion pipeline.
        
        Args:
            raw_data_dir: Directory containing Raw Data/NCRTBooks
            output_dir: Directory to save processed chunks
        """
        self.raw_data_dir = Path(raw_data_dir)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        
        # Initialize components
        self.pdf_loader = PDFLoader(
            extract_images=True,
            extract_tables=True,
            min_text_length=50
        )
        
        self.chunker = SemanticChunker(
            chunk_size=800,
            overlap=150,
            min_chunk_size=100
        )
        
        self.enricher = MetadataEnricher()
        self.validator = QualityValidator(min_quality_score=0.5)
        
        self.config = ProcessingConfig(
            enable_checkpointing=True,
            checkpoint_interval=10,
            batch_size=50,
            min_quality_score=0.5
        )
        
        logger.info("✅ NEETDataIngestion initialized")
    
    def get_pdf_files(self, subject: str) -> List[Path]:
        """
        Get all PDF files for a subject.
        
        Args:
            subject: Subject name (biology, chemistry, physics)
            
        Returns:
            List of PDF file paths
        """
        # Map subject to directory name
        subject_map = {
            'biology': 'Biology',
            'chemistry': 'chemistry',  # lowercase in actual directory
            'physics': 'Physics'
        }
        
        subject_dir = self.raw_data_dir / "NCRTBooks" / subject_map.get(subject.lower(), subject.capitalize())
        
        if not subject_dir.exists():
            logger.error(f"Subject directory not found: {subject_dir}")
            return []
        
        # Find all PDFs recursively
        pdf_files = list(subject_dir.rglob("*.pdf"))
        logger.info(f"Found {len(pdf_files)} PDF files for {subject}")
        
        return pdf_files
    
    def process_subject(self, subject: str, max_files: int = None) -> Dict[str, Any]:
        """
        Process all PDFs for a subject.
        
        Args:
            subject: Subject name
            max_files: Maximum number of files to process (None = all)
            
        Returns:
            Processing results dictionary
        """
        logger.info(f"\n{'='*60}")
        logger.info(f"Processing {subject.upper()}")
        logger.info(f"{'='*60}\n")
        
        # Get PDF files
        pdf_files = self.get_pdf_files(subject)
        
        if not pdf_files:
            logger.warning(f"No PDF files found for {subject}")
            return {'success': False, 'error': 'No PDF files found'}
        
        # Limit files if specified
        if max_files:
            pdf_files = pdf_files[:max_files]
            logger.info(f"Processing first {max_files} files (limit applied)")
        
        # Initialize batch processor
        checkpoint_dir = self.output_dir / f"{subject}_checkpoints"
        checkpoint_dir.mkdir(exist_ok=True)
        
        processor = BatchProcessor(
            loader=self.pdf_loader,
            chunker=self.chunker,
            enricher=self.enricher,
            validator=self.validator,
            config=self.config,
            checkpoint_dir=str(checkpoint_dir)
        )
        
        # Process all PDFs
        all_chunks = []
        stats = {
            'total_files': len(pdf_files),
            'processed_files': 0,
            'failed_files': 0,
            'total_chunks': 0,
            'valid_chunks': 0,
            'errors': []
        }
        
        for i, pdf_file in enumerate(pdf_files, 1):
            logger.info(f"[{i}/{len(pdf_files)}] Processing: {pdf_file.name}")
            
            try:
                # Process single file
                result = processor.process_files(
                    file_paths=[str(pdf_file)],
                    resume=True
                )
                
                if result.success:
                    chunks = result.chunks
                    all_chunks.extend(chunks)
                    stats['processed_files'] += 1
                    stats['total_chunks'] += len(chunks)
                    stats['valid_chunks'] += result.stats.valid_chunks
                    
                    logger.info(f"  ✅ Created {len(chunks)} chunks (quality score: {result.stats.average_quality:.2f})")
                    
                    # Save progress every 10 files
                    if i % 10 == 0:
                        output_file = self.output_dir / f"{subject}_chunks.json"
                        self.save_chunks(all_chunks, output_file, subject)
                        logger.info(f"  💾 Progress saved: {i}/{len(pdf_files)} files")
                else:
                    stats['failed_files'] += 1
                    stats['errors'].extend(result.stats.errors)
                    logger.warning(f"  ❌ Failed to process {pdf_file.name}")
                    
            except Exception as e:
                logger.error(f"  ❌ Error processing {pdf_file.name}: {e}")
                stats['failed_files'] += 1
                stats['errors'].append(f"{pdf_file.name}: {str(e)}")
                continue  # Continue with next file instead of stopping
        
        # Save chunks to JSON
        output_file = self.output_dir / f"{subject}_chunks.json"
        self.save_chunks(all_chunks, output_file, subject)
        
        # Update stats
        stats['output_file'] = str(output_file)
        stats['success'] = stats['processed_files'] > 0
        
        logger.info(f"\n{'='*60}")
        logger.info(f"✅ {subject.upper()} Processing Complete")
        logger.info(f"{'='*60}")
        logger.info(f"Processed: {stats['processed_files']}/{stats['total_files']} files")
        logger.info(f"Total chunks: {stats['total_chunks']}")
        logger.info(f"Valid chunks: {stats['valid_chunks']}")
        logger.info(f"Output: {output_file}\n")
        
        return stats
    
    def save_chunks(self, chunks: List[Any], output_file: Path, subject: str):
        """
        Save chunks to JSON file.
        
        Args:
            chunks: List of Chunk objects
            output_file: Output file path
            subject: Subject name
        """
        # Convert chunks to dictionaries
        chunks_data = []
        for chunk in chunks:
            chunk_dict = {
                'id': chunk.id,
                'content': chunk.content,
                'metadata': chunk.metadata,
                'quality_score': chunk.quality_score,
                'tokens': chunk.tokens
            }
            chunks_data.append(chunk_dict)
        
        # Create output structure
        output = {
            'subject': subject,
            'created_at': datetime.now().isoformat(),
            'total_chunks': len(chunks_data),
            'chunks': chunks_data
        }
        
        # Save to JSON
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(output, f, indent=2, ensure_ascii=False)
        
        logger.info(f"💾 Saved {len(chunks_data)} chunks to {output_file}")
    
    def process_all_subjects(self, max_files_per_subject: int = 5):
        """
        Process all NEET subjects.
        
        Args:
            max_files_per_subject: Max files to process per subject
        """
        subjects = ['biology', 'chemistry', 'physics']
        
        overall_stats = {
            'start_time': datetime.now(),
            'subjects': {},
            'total_chunks': 0
        }
        
        for subject in subjects:
            stats = self.process_subject(subject, max_files=max_files_per_subject)
            overall_stats['subjects'][subject] = stats
            overall_stats['total_chunks'] += stats.get('total_chunks', 0)
        
        overall_stats['end_time'] = datetime.now()
        overall_stats['duration'] = (overall_stats['end_time'] - overall_stats['start_time']).total_seconds()
        
        # Save summary
        summary_file = self.output_dir / 'ingestion_summary.json'
        with open(summary_file, 'w', encoding='utf-8') as f:
            json.dump(overall_stats, f, indent=2, default=str)
        
        logger.info(f"\n{'='*60}")
        logger.info(f"🎉 ALL SUBJECTS PROCESSED")
        logger.info(f"{'='*60}")
        logger.info(f"Total chunks created: {overall_stats['total_chunks']}")
        logger.info(f"Duration: {overall_stats['duration']:.2f} seconds")
        logger.info(f"Summary saved to: {summary_file}\n")


def main():
    """Main entry point."""
    print("\n" + "="*60)
    print("NEET CONTENT INGESTION PIPELINE")
    print("="*60 + "\n")
    
    # Check if Raw Data exists
    if not Path("Raw Data/NCRTBooks").exists():
        print("❌ Error: 'Raw Data/NCRTBooks' directory not found!")
        print("Please ensure NCERT PDFs are in: Raw Data/NCRTBooks/{subject}/")
        return
    
    # Initialize and run
    ingestion = NEETDataIngestion()
    
    print("Starting ingestion...")
    print("This will process ALL PDFs and create searchable chunks.")
    print("⚠️  This may take 15-30 minutes depending on PDF count.\n")
    
    # Process all subjects (NO LIMIT - production mode)
    ingestion.process_all_subjects(max_files_per_subject=None)
    
    print("\n✅ Ingestion complete! Check 'vectorstore_data' directory for output.")
    print("📄 Log file: neet_ingestion.log\n")


if __name__ == "__main__":
    main()
