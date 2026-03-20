"""
Batch Processor
===============

Orchestrates the complete document processing pipeline:
Loading → Chunking → Enrichment → Validation

Features:
- Checkpoint-based recovery
- Progress tracking
- Error accumulation
- Parallel processing support
- Quality monitoring

Author: APXMIND Team
Date: November 2024
"""

import json
from pathlib import Path
from typing import List, Dict, Any, Optional, Callable
from datetime import datetime
from dataclasses import dataclass, asdict
import hashlib

from .base_loader import BaseLoader, Document, LoadResult
from ..chunking import BaseChunker, Chunk, ChunkingResult
from ..preprocessing import MetadataEnricher, QualityValidator
from ..utils import CheckpointManager, ErrorAccumulator, handle_errors
from ..monitoring import get_logger, MetricsCollector, QualityTracker
from ..config import ProcessingConfig


@dataclass
class ProcessingStats:
    """Statistics for batch processing."""
    total_documents: int = 0
    processed_documents: int = 0
    failed_documents: int = 0
    total_chunks: int = 0
    valid_chunks: int = 0
    invalid_chunks: int = 0
    average_quality: float = 0.0
    processing_time: float = 0.0
    errors: List[str] = None
    
    def __post_init__(self):
        if self.errors is None:
            self.errors = []
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


@dataclass
class BatchResult:
    """Result of batch processing."""
    success: bool
    chunks: List[Chunk]
    stats: ProcessingStats
    checkpoint_path: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'success': self.success,
            'chunk_count': len(self.chunks),
            'stats': self.stats.to_dict(),
            'checkpoint_path': self.checkpoint_path
        }


class BatchProcessor:
    """
    Orchestrates batch processing of documents.
    
    Pipeline:
    1. Load documents (PDFs, text files)
    2. Chunk documents (semantic chunking)
    3. Enrich chunks (metadata extraction)
    4. Validate chunks (quality checking)
    5. Save checkpoints (crash recovery)
    """
    
    def __init__(self,
                 loader: BaseLoader,
                 chunker: BaseChunker,
                 enricher: Optional[MetadataEnricher] = None,
                 validator: Optional[QualityValidator] = None,
                 config: Optional[ProcessingConfig] = None,
                 checkpoint_dir: Optional[str] = None):
        """
        Initialize batch processor.
        
        Args:
            loader: Document loader
            chunker: Document chunker
            enricher: Metadata enricher (optional)
            validator: Quality validator (optional)
            config: Processing configuration (optional)
            checkpoint_dir: Directory for checkpoints (optional)
        """
        self.loader = loader
        self.chunker = chunker
        self.enricher = enricher or MetadataEnricher()
        self.validator = validator or QualityValidator()
        self.config = config or ProcessingConfig()
        
        # Initialize utilities
        self.checkpoint_manager = CheckpointManager(
            checkpoint_dir or "./checkpoints"
        )
        self.error_accumulator = ErrorAccumulator()
        
        # Initialize monitoring
        self.logger = get_logger("BatchProcessor")
        self.metrics = MetricsCollector()
        self.quality_tracker = QualityTracker()
        
        # Processing state
        self.stats = ProcessingStats()
    
    def process_files(self, 
                     file_paths: List[str],
                     resume: bool = True) -> BatchResult:
        """
        Process multiple files through the complete pipeline.
        
        Args:
            file_paths: List of file paths to process
            resume: Whether to resume from checkpoint
            
        Returns:
            BatchResult with processed chunks and statistics
        """
        start_time = datetime.now()
        
        self.logger.info(f"Starting batch processing of {len(file_paths)} files")
        
        # Initialize stats
        self.stats = ProcessingStats(total_documents=len(file_paths))
        
        # Try to resume from checkpoint
        processed_files = set()
        all_chunks = []
        
        if resume:
            checkpoint = self._load_checkpoint()
            if checkpoint:
                processed_files = set(checkpoint.get('processed_files', []))
                all_chunks = self._deserialize_chunks(checkpoint.get('chunks', []))
                self.logger.info(f"Resumed from checkpoint: {len(processed_files)} files already processed")
        
        # Process each file
        for file_path in file_paths:
            if file_path in processed_files:
                self.logger.debug(f"Skipping already processed file: {file_path}")
                continue
            
            try:
                # Process single file
                chunks = self._process_file(file_path)
                
                if chunks:
                    all_chunks.extend(chunks)
                    self.stats.processed_documents += 1
                    processed_files.add(file_path)
                    
                    # Save checkpoint periodically
                    if len(processed_files) % self.config.checkpoint_interval == 0:
                        self._save_checkpoint(processed_files, all_chunks)
                else:
                    self.stats.failed_documents += 1
                    self.stats.errors.append(f"No chunks extracted from {file_path}")
            
            except Exception as e:
                self.stats.failed_documents += 1
                error_msg = f"Failed to process {file_path}: {str(e)}"
                self.stats.errors.append(error_msg)
                self.logger.error(error_msg)
        
        # Final checkpoint
        checkpoint_path = self._save_checkpoint(processed_files, all_chunks)
        
        # Update stats
        self.stats.total_chunks = len(all_chunks)
        self.stats.valid_chunks = sum(1 for c in all_chunks if c.quality_score >= self.config.min_quality_score)
        self.stats.invalid_chunks = self.stats.total_chunks - self.stats.valid_chunks
        
        if all_chunks:
            self.stats.average_quality = sum(c.quality_score for c in all_chunks) / len(all_chunks)
        
        # Processing time
        self.stats.processing_time = (datetime.now() - start_time).total_seconds()
        
        self.logger.info(f"Batch processing complete: {self.stats.processed_documents}/{self.stats.total_documents} files processed")
        
        return BatchResult(
            success=self.stats.failed_documents < self.stats.total_documents,
            chunks=all_chunks,
            stats=self.stats,
            checkpoint_path=checkpoint_path
        )
    
    def _process_file(self, file_path: str) -> List[Chunk]:
        """
        Process a single file through the pipeline.
        
        Args:
            file_path: Path to file
            
        Returns:
            List of processed chunks
        """
        self.logger.info(f"Processing file: {file_path}")
        
        # Step 1: Load document
        load_result = self.loader.load(file_path)
        
        if not load_result.success or not load_result.document:
            self.logger.error(f"Failed to load {file_path}: {load_result.error}")
            return []
        
        document = load_result.document
        self.logger.debug(f"Loaded document: {len(document.content)} chars")
        
        # Step 2: Chunk document (pass text and metadata separately)
        chunking_result = self.chunker.chunk(
            text=document.content,
            metadata=document.metadata
        )
        
        if not chunking_result.success or not chunking_result.chunks:
            self.logger.error(f"Failed to chunk {file_path}")
            return []
        
        chunks = chunking_result.chunks
        self.logger.debug(f"Created {len(chunks)} chunks")
        
        # Step 3: Enrich chunks
        enriched_chunks = []
        for chunk in chunks:
            try:
                enriched = self.enricher.enrich(chunk)
                enriched_chunks.append(enriched)
            except Exception as e:
                self.logger.warning(f"Failed to enrich chunk: {str(e)}")
                enriched_chunks.append(chunk)  # Use unenriched chunk
        
        self.logger.debug(f"Enriched {len(enriched_chunks)} chunks")
        
        # Step 4: Validate chunks
        validated_chunks = []
        for chunk in enriched_chunks:
            try:
                validation = self.validator.validate(chunk)
                
                # Update chunk quality score from validation
                chunk.quality_score = validation.score
                
                # Track quality
                self.quality_tracker.track_chunk(chunk)
                
                # Only keep chunks that meet minimum quality
                if validation.valid or not self.config.filter_low_quality:
                    validated_chunks.append(chunk)
                else:
                    self.logger.debug(f"Filtered low-quality chunk: {validation.score:.2f}")
            
            except Exception as e:
                self.logger.warning(f"Failed to validate chunk: {str(e)}")
                validated_chunks.append(chunk)  # Keep chunk despite validation failure
        
        self.logger.info(f"Validated {len(validated_chunks)}/{len(enriched_chunks)} chunks")
        
        return validated_chunks
    
    def _save_checkpoint(self, 
                        processed_files: set, 
                        chunks: List[Chunk]) -> str:
        """
        Save processing checkpoint.
        
        Args:
            processed_files: Set of processed file paths
            chunks: List of processed chunks
            
        Returns:
            Path to checkpoint file
        """
        checkpoint_data = {
            'processed_files': list(processed_files),
            'chunks': self._serialize_chunks(chunks),
            'stats': self.stats.to_dict(),
            'timestamp': datetime.now().isoformat()
        }
        
        checkpoint_id = f"batch_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.checkpoint_manager.save(
            checkpoint_id,
            checkpoint_data
        )
        
        checkpoint_path = str(self.checkpoint_manager.checkpoint_dir / f"{checkpoint_id}.json")
        self.logger.debug(f"Saved checkpoint: {checkpoint_path}")
        return checkpoint_path
    
    def _load_checkpoint(self) -> Optional[Dict[str, Any]]:
        """
        Load most recent checkpoint.
        
        Returns:
            Checkpoint data or None
        """
        # Find most recent checkpoint
        checkpoint_dir = Path(self.checkpoint_manager.checkpoint_dir)
        
        if not checkpoint_dir.exists():
            return None
        
        checkpoint_files = list(checkpoint_dir.glob("batch_*.json"))
        
        if not checkpoint_files:
            return None
        
        # Get most recent
        latest = max(checkpoint_files, key=lambda p: p.stat().st_mtime)
        
        try:
            checkpoint_data = self.checkpoint_manager.load(latest.stem)
            self.logger.info(f"Loaded checkpoint: {latest.name}")
            return checkpoint_data
        except Exception as e:
            self.logger.warning(f"Failed to load checkpoint: {str(e)}")
            return None
    
    def _serialize_chunks(self, chunks: List[Chunk]) -> List[Dict[str, Any]]:
        """
        Serialize chunks for checkpoint storage.
        
        Args:
            chunks: List of chunks
            
        Returns:
            List of serialized chunks
        """
        serialized = []
        for chunk in chunks:
            serialized.append({
                'content': chunk.content,
                'metadata': chunk.metadata,
                'chunk_id': chunk.chunk_id,
                'start_pos': chunk.start_pos,
                'end_pos': chunk.end_pos,
                'quality_score': chunk.quality_score,
                'created_at': chunk.created_at.isoformat()
            })
        return serialized
    
    def _deserialize_chunks(self, serialized: List[Dict[str, Any]]) -> List[Chunk]:
        """
        Deserialize chunks from checkpoint.
        
        Args:
            serialized: List of serialized chunks
            
        Returns:
            List of Chunk objects
        """
        chunks = []
        for data in serialized:
            chunk = Chunk(
                content=data['content'],
                metadata=data['metadata'],
                chunk_id=data['chunk_id'],
                start_pos=data['start_pos'],
                end_pos=data['end_pos'],
                quality_score=data['quality_score'],
                created_at=datetime.fromisoformat(data['created_at'])
            )
            chunks.append(chunk)
        return chunks
    
    def get_stats(self) -> ProcessingStats:
        """Get current processing statistics."""
        return self.stats
    
    def get_quality_report(self) -> Dict[str, Any]:
        """
        Get quality analysis report.
        
        Returns:
            Quality statistics and distribution
        """
        avg_quality = self.quality_tracker.get_average_quality()
        by_subject = self.quality_tracker.get_quality_by_subject()
        
        return {
            'average_quality': avg_quality,
            'by_subject': by_subject,
            'summary': self.quality_tracker.get_summary()
        }


class DatasetBatchProcessor(BatchProcessor):
    """
    Specialized batch processor for complete datasets.
    
    Handles processing of entire NCERT curriculum or question banks.
    """
    
    def process_dataset(self, 
                       dataset_name: str,
                       file_paths: List[str],
                       output_dir: Optional[str] = None) -> BatchResult:
        """
        Process complete dataset with organized output.
        
        Args:
            dataset_name: Name of dataset (e.g., 'ncert_biology_11')
            file_paths: List of files in dataset
            output_dir: Directory for output (optional)
            
        Returns:
            BatchResult
        """
        self.logger.info(f"Processing dataset: {dataset_name}")
        
        # Process files
        result = self.process_files(file_paths, resume=True)
        
        # Save organized output
        if output_dir and result.success:
            self._save_dataset_output(dataset_name, result, output_dir)
        
        # Generate report
        self._generate_report(dataset_name, result)
        
        return result
    
    def _save_dataset_output(self, 
                            dataset_name: str,
                            result: BatchResult,
                            output_dir: str):
        """
        Save dataset chunks to organized output.
        
        Args:
            dataset_name: Dataset name
            result: Processing result
            output_dir: Output directory
        """
        output_path = Path(output_dir) / f"{dataset_name}_chunks.json"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Serialize chunks
        chunks_data = self._serialize_chunks(result.chunks)
        
        output = {
            'dataset_name': dataset_name,
            'chunk_count': len(result.chunks),
            'stats': result.stats.to_dict(),
            'chunks': chunks_data,
            'generated_at': datetime.now().isoformat()
        }
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(output, f, indent=2, ensure_ascii=False)
        
        self.logger.info(f"Saved dataset output: {output_path}")
    
    def _generate_report(self, dataset_name: str, result: BatchResult):
        """
        Generate processing report.
        
        Args:
            dataset_name: Dataset name
            result: Processing result
        """
        report = f"""
{'='*70}
DATASET PROCESSING REPORT: {dataset_name}
{'='*70}

Processing Summary:
  Total Documents: {result.stats.total_documents}
  Processed: {result.stats.processed_documents}
  Failed: {result.stats.failed_documents}
  Success Rate: {result.stats.processed_documents/result.stats.total_documents*100:.1f}%

Chunk Statistics:
  Total Chunks: {result.stats.total_chunks}
  Valid Chunks: {result.stats.valid_chunks}
  Invalid Chunks: {result.stats.invalid_chunks}
  Validation Rate: {result.stats.valid_chunks/result.stats.total_chunks*100:.1f}% (if chunks > 0 else 0)
  Average Quality: {result.stats.average_quality:.2f}

Processing Time: {result.stats.processing_time:.2f} seconds

Quality Distribution:
"""
        
        avg_quality = self.quality_tracker.get_average_quality()
        report += f"  Average Quality: {avg_quality:.2f}\n"
        
        # Get quality by subject if available
        by_subject = self.quality_tracker.get_quality_by_subject()
        if by_subject:
            report += "\nQuality by Subject:\n"
            for subject, stats in by_subject.items():
                if 'avg' in stats:
                    report += f"  {subject}: {stats['avg']:.2f}\n"
        
        if result.stats.errors:
            report += f"\nErrors ({len(result.stats.errors)}):\n"
            for error in result.stats.errors[:10]:  # Show first 10
                report += f"  • {error}\n"
        
        report += f"\n{'='*70}\n"
        
        self.logger.info(report)
        print(report)
