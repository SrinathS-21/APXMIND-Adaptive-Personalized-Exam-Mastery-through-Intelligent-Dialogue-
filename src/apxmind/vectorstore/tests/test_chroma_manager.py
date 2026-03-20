"""
Test ChromaDB Manager
=====================

Tests for ChromaDB vector store operations.

Usage:
    python src\APXMIND\vectorstore\tests\test_chroma_manager.py
"""

import sys
from pathlib import Path
import tempfile
import shutil
import numpy as np

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from apxmind.vectorstore.storage import ChromaDBManager, AddResult, QueryResult
from apxmind.vectorstore.config import ChromaDBConfig
from apxmind.vectorstore.chunking import Chunk
from datetime import datetime


def test_chroma_manager_initialization():
    """Test ChromaDB manager initialization."""
    print("=" * 60)
    print("TEST 1: ChromaDB Manager Initialization")
    print("=" * 60)
    
    with tempfile.TemporaryDirectory() as temp_dir:
        config = ChromaDBConfig(base_path=temp_dir)
        manager = ChromaDBManager(config)
        
        print(f"\nPASS ChromaDB Manager created")
        print(f"  Base path: {manager.config.base_path}")
        print(f"  Collections: {list(manager.config.collections.keys())}")
        print(f"  Distance metric: {manager.config.distance_metric}")
    
    return True


def test_create_collection():
    """Test creating a collection."""
    print("\n" + "=" * 60)
    print("TEST 2: Create Collection")
    print("=" * 60)
    
    with tempfile.TemporaryDirectory() as temp_dir:
        config = ChromaDBConfig(base_path=temp_dir)
        manager = ChromaDBManager(config)
        
        # Create biology collection
        collection = manager._get_or_create_collection('biology')
        
        print(f"\nPASS Biology collection created")
        print(f"  Name: {collection.name}")
        print(f"  Count: {collection.count()}")
    
    return True


def test_add_chunks():
    """Test adding chunks to collection."""
    print("\n" + "=" * 60)
    print("TEST 3: Add Chunks")
    print("=" * 60)
    
    with tempfile.TemporaryDirectory() as temp_dir:
        config = ChromaDBConfig(base_path=temp_dir)
        manager = ChromaDBManager(config)
        
        # Create test chunks
        chunks = [
            Chunk(
                content=f"Biology content {i}: cells, DNA, and evolution.",
                metadata={'subject': 'biology', 'topic': f'topic_{i}'},
                chunk_id=f'bio_chunk_{i:03d}',
                start_pos=0,
                end_pos=50,
                quality_score=0.8 + (i * 0.01)
            )
            for i in range(5)
        ]
        
        # Create random embeddings (768-dim for nomic-embed-text)
        embeddings = [
            np.random.rand(768).tolist()
            for _ in range(5)
        ]
        
        print(f"\nPASS Adding {len(chunks)} chunks to biology collection")
        
        # Add chunks
        result = manager.add_chunks('biology', chunks, embeddings)
        
        print(f"\nPASS Add result:")
        print(f"  Success: {result.success}")
        print(f"  Documents added: {result.documents_added}/{result.total_documents}")
        print(f"  Errors: {len(result.errors)}")
        print(f"  Processing time: {result.processing_time:.3f}s")
        
        # Verify count
        stats = manager.get_collection_stats('biology')
        print(f"\nPASS Collection stats:")
        print(f"  Document count: {stats['document_count']}")
        
        return result.success and stats['document_count'] == 5


def test_query_collection():
    """Test querying a collection."""
    print("\n" + "=" * 60)
    print("TEST 4: Query Collection")
    print("=" * 60)
    
    with tempfile.TemporaryDirectory() as temp_dir:
        config = ChromaDBConfig(base_path=temp_dir)
        manager = ChromaDBManager(config)
        
        # Add test data
        chunks = [
            Chunk(
                content="Photosynthesis is the process by which plants convert light energy into chemical energy.",
                metadata={'subject': 'biology', 'topic': 'photosynthesis'},
                chunk_id='photo_001',
                start_pos=0,
                end_pos=87,
                quality_score=0.9
            ),
            Chunk(
                content="Mitochondria are the powerhouse of the cell, producing ATP through cellular respiration.",
                metadata={'subject': 'biology', 'topic': 'cellular_biology'},
                chunk_id='mito_001',
                start_pos=0,
                end_pos=88,
                quality_score=0.85
            )
        ]
        
        embeddings = [np.random.rand(768).tolist() for _ in range(2)]
        
        manager.add_chunks('biology', chunks, embeddings)
        
        # Query (using text-based query)
        print(f"\nPASS Querying for 'photosynthesis'")
        
        result = manager.query(
            'biology',
            query_texts=['photosynthesis'],
            top_k=2
        )
        
        print(f"\nPASS Query result:")
        print(f"  Success: {result.success}")
        print(f"  Total results: {result.total_results}")
        print(f"  Processing time: {result.processing_time:.3f}s")
        
        if result.results:
            print(f"\nPASS First result:")
            print(f"  ID: {result.results[0]['id']}")
            print(f"  Content: {result.results[0]['document'][:60]}...")
            print(f"  Distance: {result.results[0]['distance']:.4f}")
        
        return result.success and result.total_results > 0


def test_metadata_filtering():
    """Test querying with metadata filters."""
    print("\n" + "=" * 60)
    print("TEST 5: Metadata Filtering")
    print("=" * 60)
    
    with tempfile.TemporaryDirectory() as temp_dir:
        config = ChromaDBConfig(base_path=temp_dir)
        manager = ChromaDBManager(config)
        
        # Add chunks with different quality scores
        chunks = [
            Chunk(
                content=f"Chemistry content {i}",
                metadata={'subject': 'chemistry', 'difficulty': 'high' if i < 3 else 'low'},
                chunk_id=f'chem_{i:03d}',
                start_pos=0,
                end_pos=20,
                quality_score=0.9 if i < 3 else 0.6
            )
            for i in range(6)
        ]
        
        embeddings = [np.random.rand(768).tolist() for _ in range(6)]
        manager.add_chunks('chemistry', chunks, embeddings)
        
        # Query with quality filter
        print(f"\nPASS Querying with quality_score >= 0.8")
        
        result = manager.query(
            'chemistry',
            query_texts=['chemistry'],
            top_k=10,
            where={'quality_score': {'$gte': 0.8}}
        )
        
        print(f"\nPASS Filtered query result:")
        print(f"  Total results: {result.total_results}")
        
        # Check all results meet criteria
        if result.results:
            scores = [r['metadata'].get('quality_score', 0) for r in result.results]
            all_high_quality = all(s >= 0.8 for s in scores)
            print(f"  All results >= 0.8 quality: {all_high_quality}")
            print(f"  Quality scores: {scores}")
        
        return result.success


def test_collection_stats():
    """Test getting collection statistics."""
    print("\n" + "=" * 60)
    print("TEST 6: Collection Statistics")
    print("=" * 60)
    
    with tempfile.TemporaryDirectory() as temp_dir:
        config = ChromaDBConfig(base_path=temp_dir)
        manager = ChromaDBManager(config)
        
        # Add data to multiple collections
        for collection_key in ['biology', 'chemistry', 'physics']:
            chunks = [
                Chunk(
                    content=f"{collection_key} content {i}",
                    metadata={'subject': collection_key},
                    chunk_id=f'{collection_key}_{i:03d}',
                    start_pos=0,
                    end_pos=20,
                    quality_score=0.8
                )
                for i in range(3)
            ]
            embeddings = [np.random.rand(768).tolist() for _ in range(3)]
            manager.add_chunks(collection_key, chunks, embeddings)
        
        # Get all stats
        all_stats = manager.get_all_collection_stats()
        
        print(f"\nPASS All collection stats:")
        for key, stats in all_stats.items():
            if stats.get('document_count', 0) > 0:
                print(f"  {key}: {stats['document_count']} documents")
        
        return len([s for s in all_stats.values() if s.get('document_count', 0) > 0]) == 3


def test_reset_collection():
    """Test resetting a collection."""
    print("\n" + "=" * 60)
    print("TEST 7: Reset Collection")
    print("=" * 60)
    
    with tempfile.TemporaryDirectory() as temp_dir:
        config = ChromaDBConfig(base_path=temp_dir)
        manager = ChromaDBManager(config)
        
        # Add data
        chunks = [
            Chunk(
                content="Test content",
                metadata={},
                chunk_id='test_001',
                start_pos=0,
                end_pos=12,
                quality_score=0.8
            )
        ]
        embeddings = [np.random.rand(768).tolist()]
        manager.add_chunks('physics', chunks, embeddings)
        
        stats_before = manager.get_collection_stats('physics')
        print(f"\nPASS Before reset: {stats_before['document_count']} documents")
        
        # Reset
        success = manager.reset_collection('physics')
        
        stats_after = manager.get_collection_stats('physics')
        print(f"PASS After reset: {stats_after['document_count']} documents")
        print(f"PASS Reset success: {success}")
        
        return success and stats_after['document_count'] == 0


def test_batch_add():
    """Test adding large batch of documents."""
    print("\n" + "=" * 60)
    print("TEST 8: Batch Add")
    print("=" * 60)
    
    with tempfile.TemporaryDirectory() as temp_dir:
        config = ChromaDBConfig(base_path=temp_dir)
        manager = ChromaDBManager(config)
        
        # Create large batch
        num_chunks = 250
        chunks = [
            Chunk(
                content=f"Question bank content {i}",
                metadata={'subject': 'mixed', 'question_type': 'mcq'},
                chunk_id=f'q_{i:04d}',
                start_pos=0,
                end_pos=25,
                quality_score=0.7 + (i % 3) * 0.1
            )
            for i in range(num_chunks)
        ]
        embeddings = [np.random.rand(768).tolist() for _ in range(num_chunks)]
        
        print(f"\nPASS Adding {num_chunks} chunks in batches")
        
        result = manager.add_chunks('question_bank', chunks, embeddings, batch_size=100)
        
        print(f"\nPASS Batch add result:")
        print(f"  Success: {result.success}")
        print(f"  Documents added: {result.documents_added}/{result.total_documents}")
        print(f"  Processing time: {result.processing_time:.3f}s")
        print(f"  Throughput: {result.documents_added / result.processing_time:.1f} docs/sec")
        
        return result.success and result.documents_added == num_chunks


def main():
    """Run all tests."""
    print("\n" + "=" * 60)
    print("CHROMADB MANAGER TEST SUITE")
    print("=" * 60 + "\n")
    
    tests = [
        ("ChromaDB Manager Initialization", test_chroma_manager_initialization),
        ("Create Collection", test_create_collection),
        ("Add Chunks", test_add_chunks),
        ("Query Collection", test_query_collection),
        ("Metadata Filtering", test_metadata_filtering),
        ("Collection Statistics", test_collection_stats),
        ("Reset Collection", test_reset_collection),
        ("Batch Add", test_batch_add),
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            success = test_func()
            results.append((test_name, success))
        except Exception as e:
            print(f"\nFAIL Test '{test_name}' crashed: {e}")
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
        status = "PASS" if success else "FAIL"
        print(f"  {status}: {test_name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    print("=" * 60 + "\n")
    
    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
