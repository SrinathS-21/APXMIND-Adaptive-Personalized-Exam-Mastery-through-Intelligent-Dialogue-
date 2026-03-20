"""
Fast NEET Content Ingestion
============================

Optimized version using PyMuPDF for 10-20x faster PDF processing.
Processes all 168 PDFs efficiently with progress tracking.
"""

import sys
import json
import logging
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any
import time

# Add project root
sys.path.insert(0, str(Path(__file__).parent))

from fast_pdf_loader import FastPDFLoader
from src.apxmind.vectorstore.chunking.semantic_chunker import SemanticChunker
from src.apxmind.vectorstore.preprocessing import MetadataEnricher, QualityValidator

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('fast_ingestion.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class FastNEETIngestion:
    """Fast NEET content ingestion using PyMuPDF."""
    
    def __init__(self, raw_data_dir: str = "Raw Data", output_dir: str = "vectorstore_data"):
        self.raw_data_dir = Path(raw_data_dir)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        
        # Initialize components
        self.pdf_loader = FastPDFLoader(min_text_length=50)
        self.chunker = SemanticChunker(chunk_size=800, overlap=150, min_chunk_size=100)
        self.enricher = MetadataEnricher()
        self.validator = QualityValidator(min_quality_score=0.5)
        
        logger.info("FastNEETIngestion initialized")
    
    def get_pdf_files(self, subject: str) -> List[Path]:
        """Get all PDF files for a subject."""
        subject_map = {
            'biology': 'Biology',
            'chemistry': 'chemistry',
            'physics': 'Physics'
        }
        
        subject_dir = self.raw_data_dir / "NCRTBooks" / subject_map.get(subject.lower(), subject.capitalize())
        
        if not subject_dir.exists():
            logger.error(f"Subject directory not found: {subject_dir}")
            return []
        
        pdf_files = sorted(subject_dir.rglob("*.pdf"))
        logger.info(f"Found {len(pdf_files)} PDF files for {subject}")
        return pdf_files
    
    def process_subject(self, subject: str) -> Dict[str, Any]:
        """
        Process all PDFs for a subject.
        
        Args:
            subject: Subject name (biology, chemistry, physics)
            
        Returns:
            Processing statistics
        """
        logger.info(f"\n{'='*60}")
        logger.info(f"Processing {subject.upper()}")
        logger.info(f"{'='*60}")
        
        start_time = time.time()
        
        # Get all PDF files
        pdf_files = self.get_pdf_files(subject)
        if not pdf_files:
            return {'success': False, 'error': 'No PDF files found'}
        
        all_chunks = []
        stats = {
            'subject': subject,
            'total_files': len(pdf_files),
            'processed_files': 0,
            'failed_files': 0,
            'total_chunks': 0,
            'valid_chunks': 0,
            'avg_quality': 0.0,
            'processing_time': 0.0,
            'errors': []
        }
        
        # Process each PDF
        for i, pdf_file in enumerate(pdf_files, 1):
            try:
                logger.info(f"[{i}/{len(pdf_files)}] {pdf_file.name}")
                
                # Load PDF (FAST!)
                doc = self.pdf_loader.load(str(pdf_file))
                text = doc['text']
                
                if not text or len(text) < 100:
                    logger.warning(f"  Skip: Insufficient text ({len(text)} chars)")
                    stats['failed_files'] += 1
                    continue
                
                # Create chunks
                chunks = self.chunker.chunk_text(
                    text=text,
                    metadata={
                        'source': str(pdf_file),
                        'subject': subject,
                        'filename': pdf_file.name,
                        **doc['metadata']
                    }
                )
                
                if not chunks:
                    logger.warning(f"  Skip: No chunks created")
                    stats['failed_files'] += 1
                    continue
                
                # Enrich and validate
                valid_chunks = []
                for chunk in chunks:
                    # Enrich metadata
                    enriched_chunk = self.enricher.enrich(chunk)
                    
                    # Validate quality
                    is_valid, quality_score = self.validator.validate(enriched_chunk)
                    
                    if is_valid:
                        enriched_chunk.quality_score = quality_score
                        valid_chunks.append(enriched_chunk)
                
                all_chunks.extend(valid_chunks)
                stats['processed_files'] += 1
                stats['total_chunks'] += len(chunks)
                stats['valid_chunks'] += len(valid_chunks)
                
                avg_quality = sum(c.quality_score for c in valid_chunks) / len(valid_chunks) if valid_chunks else 0
                logger.info(f"  OK: {len(valid_chunks)}/{len(chunks)} chunks (quality: {avg_quality:.2f})")
                
                # Save progress every 10 files
                if i % 10 == 0:
                    self._save_chunks(all_chunks, subject)
                    logger.info(f"  Progress saved: {i}/{len(pdf_files)} files")
                
            except Exception as e:
                logger.error(f"  Error: {e}")
                stats['failed_files'] += 1
                stats['errors'].append(f"{pdf_file.name}: {str(e)}")
                continue
        
        # Final save
        self._save_chunks(all_chunks, subject)
        
        # Calculate final stats
        stats['processing_time'] = time.time() - start_time
        if all_chunks:
            stats['avg_quality'] = sum(c.quality_score for c in all_chunks) / len(all_chunks)
        
        logger.info(f"\n{'='*60}")
        logger.info(f"{subject.upper()} Complete")
        logger.info(f"{'='*60}")
        logger.info(f"Processed: {stats['processed_files']}/{stats['total_files']} files")
        logger.info(f"Chunks: {stats['valid_chunks']} valid / {stats['total_chunks']} total")
        logger.info(f"Avg Quality: {stats['avg_quality']:.2f}")
        logger.info(f"Time: {stats['processing_time']:.1f}s\n")
        
        return stats
    
    def _save_chunks(self, chunks: List[Any], subject: str):
        """Save chunks to JSON file."""
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
        
        output = {
            'subject': subject,
            'created_at': datetime.now().isoformat(),
            'total_chunks': len(chunks_data),
            'chunks': chunks_data
        }
        
        output_file = self.output_dir / f"{subject}_chunks.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(output, f, indent=2, ensure_ascii=False)
    
    def process_all_subjects(self):
        """Process all subjects."""
        subjects = ['biology', 'chemistry', 'physics']
        all_stats = []
        
        overall_start = time.time()
        
        for subject in subjects:
            stats = self.process_subject(subject)
            all_stats.append(stats)
        
        overall_time = time.time() - overall_start
        
        # Save summary
        summary = {
            'created_at': datetime.now().isoformat(),
            'total_time': overall_time,
            'subjects': all_stats
        }
        
        summary_file = self.output_dir / "ingestion_summary.json"
        with open(summary_file, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)
        
        # Print summary
        print("\n" + "="*60)
        print("INGESTION SUMMARY")
        print("="*60)
        
        total_files = sum(s['processed_files'] for s in all_stats)
        total_chunks = sum(s['valid_chunks'] for s in all_stats)
        
        for stats in all_stats:
            print(f"\n{stats['subject'].upper()}:")
            print(f"  Files: {stats['processed_files']}/{stats['total_files']}")
            print(f"  Chunks: {stats['valid_chunks']}")
            print(f"  Quality: {stats['avg_quality']:.2f}")
            print(f"  Time: {stats['processing_time']:.1f}s")
        
        print(f"\nTOTAL:")
        print(f"  Files: {total_files}")
        print(f"  Chunks: {total_chunks}")
        print(f"  Time: {overall_time/60:.1f} minutes")
        print("="*60)


def main():
    print("="*60)
    print("FAST NEET CONTENT INGESTION")
    print("="*60)
    print("Using PyMuPDF for 10-20x faster processing")
    print("Processing ALL 168 PDFs (Biology: 64, Chemistry: 48, Physics: 56)")
    print("="*60)
    print()
    
    # Check raw data exists
    if not Path("Raw Data/NCRTBooks").exists():
        print("Error: 'Raw Data/NCRTBooks' not found!")
        return
    
    ingestion = FastNEETIngestion()
    ingestion.process_all_subjects()
    
    print("\nDone! Check 'vectorstore_data' directory for output.")


if __name__ == "__main__":
    main()
