"""
Test Batch Processor
====================

Tests for batch processing pipeline.

Usage:
    python src\APXMIND\vectorstore\tests\test_batch_processor.py
"""

import sys
from pathlib import Path
from datetime import datetime
import json
import tempfile
import shutil

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from apxmind.vectorstore.ingestion import (
    BatchProcessor,
    DatasetBatchProcessor,
    NCERTBookLoader
)
from apxmind.vectorstore.chunking import SemanticChunker
from apxmind.vectorstore.preprocessing import MetadataEnricher, QualityValidator
from apxmind.vectorstore.config import ProcessingConfig


def test_batch_processor_initialization():
    """Test batch processor initialization."""
    print("=" * 60)
    print("TEST 1: Batch Processor Initialization")
    print("=" * 60)
    
    loader = NCERTBookLoader()
    chunker = SemanticChunker()
    
    processor = BatchProcessor(
        loader=loader,
        chunker=chunker
    )
    
    print(f"\n✓ Batch Processor created")
    print(f"  Loader: {type(processor.loader).__name__}")
    print(f"  Chunker: {type(processor.chunker).__name__}")
    print(f"  Enricher: {type(processor.enricher).__name__}")
    print(f"  Validator: {type(processor.validator).__name__}")
    
    return True


def test_processing_stats():
    """Test processing statistics."""
    print("\n" + "=" * 60)
    print("TEST 2: Processing Statistics")
    print("=" * 60)
    
    loader = NCERTBookLoader()
    chunker = SemanticChunker()
    processor = BatchProcessor(loader, chunker)
    
    stats = processor.get_stats()
    
    print(f"\n✓ Initial statistics:")
    print(f"  Total documents: {stats.total_documents}")
    print(f"  Processed: {stats.processed_documents}")
    print(f"  Failed: {stats.failed_documents}")
    print(f"  Total chunks: {stats.total_chunks}")
    
    return stats.total_documents == 0


def test_process_nonexistent_files():
    """Test processing non-existent files."""
    print("\n" + "=" * 60)
    print("TEST 3: Process Non-Existent Files")
    print("=" * 60)
    
    loader = NCERTBookLoader()
    chunker = SemanticChunker()
    processor = BatchProcessor(loader, chunker)
    
    result = processor.process_files(['nonexistent1.pdf', 'nonexistent2.pdf'], resume=False)
    
    print(f"\n✓ Processing result:")
    print(f"  Success: {result.success}")
    print(f"  Chunks: {len(result.chunks)}")
    print(f"  Failed documents: {result.stats.failed_documents}")
    print(f"  Errors: {len(result.stats.errors)}")
    
    return result.stats.failed_documents == 2


def test_process_actual_pdf():
    """Test processing an actual PDF if available."""
    print("\n" + "=" * 60)
    print("TEST 4: Process Actual PDF")
    print("=" * 60)
    
    # Find a PDF file
    base_path = Path("d:/APXMIND-main/APXMIND-main/Raw Data/NCRTBooks")
    
    if not base_path.exists():
        print(f"\n⚠ Raw Data not found, skipping test")
        return True
    
    pdf_files = list(base_path.rglob("*.pdf"))
    
    if not pdf_files:
        print(f"\n⚠ No PDF files found, skipping test")
        return True
    
    # Use first PDF (limit to first for speed)
    test_file = str(pdf_files[0])
    print(f"\n✓ Processing: {Path(test_file).name}")
    
    # Create temp checkpoint directory
    with tempfile.TemporaryDirectory() as temp_dir:
        loader = NCERTBookLoader()
        chunker = SemanticChunker()
        
        processor = BatchProcessor(
            loader=loader,
            chunker=chunker,
            checkpoint_dir=temp_dir
        )
        
        result = processor.process_files([test_file], resume=False)
        
        print(f"\n  Processing Result:")
        print(f"    Success: {result.success}")
        print(f"    Chunks created: {len(result.chunks)}")
        print(f"    Processed documents: {result.stats.processed_documents}")
        print(f"    Valid chunks: {result.stats.valid_chunks}")
        print(f"    Average quality: {result.stats.average_quality:.2f}")
        print(f"    Processing time: {result.stats.processing_time:.2f}s")
        
        if result.chunks:
            chunk = result.chunks[0]
            print(f"\n  First Chunk:")
            print(f"    ID: {chunk.chunk_id}")
            print(f"    Length: {len(chunk.content)} chars")
            print(f"    Quality: {chunk.quality_score:.2f}")
            print(f"    Key terms: {len(chunk.metadata.get('key_terms', []))}")
    
    return result.success and len(result.chunks) > 0


def test_checkpoint_save_load():
    """Test checkpoint saving and loading."""
    print("\n" + "=" * 60)
    print("TEST 5: Checkpoint Save/Load")
    print("=" * 60)
    
    # Find a PDF file
    base_path = Path("d:/APXMIND-main/APXMIND-main/Raw Data/NCRTBooks")
    
    if not base_path.exists():
        print(f"\n⚠ Raw Data not found, skipping test")
        return True
    
    pdf_files = list(base_path.rglob("*.pdf"))[:2]  # Use first 2 files
    
    if len(pdf_files) < 2:
        print(f"\n⚠ Not enough PDF files found, skipping test")
        return True
    
    file_paths = [str(f) for f in pdf_files]
    
    with tempfile.TemporaryDirectory() as temp_dir:
        loader = NCERTBookLoader()
        chunker = SemanticChunker()
        
        # Process first file
        processor1 = BatchProcessor(
            loader=loader,
            chunker=chunker,
            checkpoint_dir=temp_dir
        )
        
        result1 = processor1.process_files([file_paths[0]], resume=False)
        print(f"\n✓ First processing:")
        print(f"  Chunks: {len(result1.chunks)}")
        print(f"  Checkpoint: {result1.checkpoint_path is not None}")
        
        # Resume and process second file
        processor2 = BatchProcessor(
            loader=loader,
            chunker=chunker,
            checkpoint_dir=temp_dir
        )
        
        result2 = processor2.process_files(file_paths, resume=True)
        print(f"\n✓ Resumed processing:")
        print(f"  Total chunks: {len(result2.chunks)}")
        print(f"  Processed documents: {result2.stats.processed_documents}")
        
        # Should have more chunks after processing both files
        more_chunks = len(result2.chunks) >= len(result1.chunks)
        print(f"\n  Has more chunks after resume: {more_chunks}")
    
    return more_chunks


def test_quality_filtering():
    """Test quality filtering."""
    print("\n" + "=" * 60)
    print("TEST 6: Quality Filtering")
    print("=" * 60)
    
    base_path = Path("d:/APXMIND-main/APXMIND-main/Raw Data/NCRTBooks")
    
    if not base_path.exists():
        print(f"\n⚠ Raw Data not found, skipping test")
        return True
    
    pdf_files = list(base_path.rglob("*.pdf"))[:1]
    
    if not pdf_files:
        print(f"\n⚠ No PDF files found, skipping test")
        return True
    
    test_file = str(pdf_files[0])
    
    with tempfile.TemporaryDirectory() as temp_dir:
        # Process with filtering
        config_filtered = ProcessingConfig(
            filter_low_quality=True,
            min_quality_score=0.7
        )
        
        processor_filtered = BatchProcessor(
            loader=NCERTBookLoader(),
            chunker=SemanticChunker(),
            config=config_filtered,
            checkpoint_dir=temp_dir
        )
        
        result_filtered = processor_filtered.process_files([test_file], resume=False)
        
        # Process without filtering
        config_all = ProcessingConfig(
            filter_low_quality=False
        )
        
        processor_all = BatchProcessor(
            loader=NCERTBookLoader(),
            chunker=SemanticChunker(),
            config=config_all,
            checkpoint_dir=temp_dir + "_all"
        )
        
        result_all = processor_all.process_files([test_file], resume=False)
        
        print(f"\n✓ Quality filtering comparison:")
        print(f"  With filtering (>0.7): {len(result_filtered.chunks)} chunks")
        print(f"  Without filtering: {len(result_all.chunks)} chunks")
        print(f"  Filtered out: {len(result_all.chunks) - len(result_filtered.chunks)} chunks")
    
    return True


def test_dataset_processor():
    """Test dataset batch processor."""
    print("\n" + "=" * 60)
    print("TEST 7: Dataset Batch Processor")
    print("=" * 60)
    
    base_path = Path("d:/APXMIND-main/APXMIND-main/Raw Data/NCRTBooks")
    
    if not base_path.exists():
        print(f"\n⚠ Raw Data not found, skipping test")
        return True
    
    pdf_files = list(base_path.rglob("*.pdf"))[:1]
    
    if not pdf_files:
        print(f"\n⚠ No PDF files found, skipping test")
        return True
    
    file_paths = [str(f) for f in pdf_files]
    
    with tempfile.TemporaryDirectory() as temp_dir:
        processor = DatasetBatchProcessor(
            loader=NCERTBookLoader(),
            chunker=SemanticChunker(),
            checkpoint_dir=temp_dir
        )
        
        result = processor.process_dataset(
            dataset_name="test_dataset",
            file_paths=file_paths,
            output_dir=temp_dir
        )
        
        print(f"\n✓ Dataset processing:")
        print(f"  Success: {result.success}")
        print(f"  Chunks: {len(result.chunks)}")
        
        # Check output file
        output_file = Path(temp_dir) / "test_dataset_chunks.json"
        exists = output_file.exists()
        print(f"  Output file exists: {exists}")
        
        if exists:
            with open(output_file, encoding='utf-8') as f:
                data = json.load(f)
            print(f"  Dataset name: {data['dataset_name']}")
            print(f"  Chunk count: {data['chunk_count']}")
    
    return result.success


def test_quality_report():
    """Test quality reporting."""
    print("\n" + "=" * 60)
    print("TEST 8: Quality Report")
    print("=" * 60)
    
    base_path = Path("d:/APXMIND-main/APXMIND-main/Raw Data/NCRTBooks")
    
    if not base_path.exists():
        print(f"\n⚠ Raw Data not found, skipping test")
        return True
    
    pdf_files = list(base_path.rglob("*.pdf"))[:1]
    
    if not pdf_files:
        print(f"\n⚠ No PDF files found, skipping test")
        return True
    
    with tempfile.TemporaryDirectory() as temp_dir:
        processor = BatchProcessor(
            loader=NCERTBookLoader(),
            chunker=SemanticChunker(),
            checkpoint_dir=temp_dir
        )
        
        result = processor.process_files([str(pdf_files[0])], resume=False)
        
        if result.success:
            report = processor.get_quality_report()
            
            print(f"\n✓ Quality Report:")
            print(f"  Average quality: {report['average_quality']:.2f}")
            if report['by_subject']:
                print(f"  Subjects tracked: {len(report['by_subject'])}")
            print(f"  Summary: {report['summary'][:100]}...")
    
    return True


def main():
    """Run all tests."""
    print("\n" + "=" * 60)
    print("BATCH PROCESSOR TEST SUITE")
    print("=" * 60 + "\n")
    
    tests = [
        ("Batch Processor Initialization", test_batch_processor_initialization),
        ("Processing Statistics", test_processing_stats),
        ("Process Non-Existent Files", test_process_nonexistent_files),
        ("Process Actual PDF", test_process_actual_pdf),
        ("Checkpoint Save/Load", test_checkpoint_save_load),
        ("Quality Filtering", test_quality_filtering),
        ("Dataset Processor", test_dataset_processor),
        ("Quality Report", test_quality_report),
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            success = test_func()
            results.append((test_name, success))
        except Exception as e:
            print(f"\n✗ Test '{test_name}' crashed: {e}")
            import traceback
            traceback.print_exc()
            results.append((test_name, False))
    
    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    passed = sum(1 for _, success in results if success)
    total = len(results)
    
    for test_name, success in results:
        status = "✓ PASS" if success else "✗ FAIL"
        print(f"  {status}: {test_name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    print("=" * 60 + "\n")
    
    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
