"""
Test Embedding Manager
======================

Tests for embedding generation and caching.

Usage:
    python src\APXMIND\vectorstore\tests\test_embedding_manager.py
"""

import sys
from pathlib import Path
import numpy as np
import tempfile
import shutil
from datetime import datetime

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from apxmind.vectorstore.embedding import (
    EmbeddingManager,
    EmbeddingCache,
    EmbeddingResult,
    BatchEmbeddingResult
)
from apxmind.vectorstore.config import EmbeddingConfig
from apxmind.vectorstore.chunking import Chunk


def test_embedding_manager_initialization():
    """Test embedding manager initialization."""
    print("=" * 60)
    print("TEST 1: Embedding Manager Initialization")
    print("=" * 60)
    
    with tempfile.TemporaryDirectory() as temp_dir:
        config = EmbeddingConfig(cache_dir=temp_dir)
        manager = EmbeddingManager(config)
        
        print(f"\nPASS Embedding Manager created")
        print(f"  Model: {manager.config.model_name}")
        print(f"  Dimension: {manager.config.embedding_dim}")
        print(f"  Batch size: {manager.config.batch_size}")
        print(f"  Cache enabled: {manager.config.enable_cache}")
        print(f"  Normalization: {manager.config.normalize_embeddings}")
    
    return True


def test_embedding_cache():
    """Test embedding cache."""
    print("\n" + "=" * 60)
    print("TEST 2: Embedding Cache")
    print("=" * 60)
    
    with tempfile.TemporaryDirectory() as temp_dir:
        cache = EmbeddingCache(cache_dir=temp_dir, max_size_mb=10)
        
        # Test cache miss
        text = "The mitochondria is the powerhouse of the cell."
        embedding = cache.get(text)
        print(f"\nPASS Cache miss (expected): {embedding is None}")
        
        # Test cache put
        test_embedding = np.random.rand(768).astype(np.float32)
        cache.put(text, test_embedding)
        print(f"PASS Cached embedding")
        
        # Test cache hit
        cached = cache.get(text)
        hit = cached is not None
        print(f"PASS Cache hit: {hit}")
        
        if hit:
            match = np.allclose(cached, test_embedding)
            print(f"PASS Embedding matches: {match}")
        
        # Test cache stats
        stats = cache.get_stats()
        print(f"\nPASS Cache stats:")
        print(f"  Total entries: {stats['total_entries']}")
        print(f"  Total size MB: {stats['total_size_mb']:.4f}")
        print(f"  Utilization: {stats['utilization']:.2%}")
    
    return True


def test_single_chunk_embedding():
    """Test embedding a single chunk."""
    print("\n" + "=" * 60)
    print("TEST 3: Single Chunk Embedding")
    print("=" * 60)
    
    with tempfile.TemporaryDirectory() as temp_dir:
        config = EmbeddingConfig(cache_dir=temp_dir)
        manager = EmbeddingManager(config)
        
        # Create test chunk
        chunk = Chunk(
            content="Photosynthesis is the process by which plants convert light energy into chemical energy.",
            metadata={'subject': 'biology', 'topic': 'photosynthesis'},
            chunk_id='test_chunk_001',
            start_pos=0,
            end_pos=87
        )
        
        print(f"\nPASS Embedding chunk: {chunk.chunk_id}")
        print(f"  Content length: {len(chunk.content)} chars")
        
        # Generate embedding
        result = manager.embed_chunk(chunk)
        
        print(f"\nPASS Embedding result:")
        print(f"  Success: {result.success}")
        print(f"  Chunk ID: {result.chunk_id}")
        print(f"  Model: {result.model_name}")
        print(f"  Dimension: {result.dimension}")
        print(f"  Normalized: {result.normalized}")
        print(f"  Cache hit: {result.cache_hit}")
        print(f"  Processing time: {result.processing_time:.3f}s")
        
        if result.success:
            # Verify embedding properties
            print(f"\nPASS Embedding properties:")
            print(f"  Shape: {result.embedding.shape}")
            print(f"  Dtype: {result.embedding.dtype}")
            
            if result.normalized:
                norm = np.linalg.norm(result.embedding)
                print(f"  Norm (should be ~1.0): {norm:.6f}")
        
        return result.success


def test_cache_hit():
    """Test cache hit on second embedding."""
    print("\n" + "=" * 60)
    print("TEST 4: Cache Hit")
    print("=" * 60)
    
    with tempfile.TemporaryDirectory() as temp_dir:
        config = EmbeddingConfig(cache_dir=temp_dir)
        manager = EmbeddingManager(config)
        
        chunk = Chunk(
            content="DNA carries genetic information.",
            metadata={},
            chunk_id='test_chunk_002',
            start_pos=0,
            end_pos=32
        )
        
        # First embedding (cache miss)
        result1 = manager.embed_chunk(chunk)
        print(f"\nPASS First embedding:")
        print(f"  Cache hit: {result1.cache_hit}")
        print(f"  Processing time: {result1.processing_time:.3f}s")
        
        # Second embedding (should be cache hit)
        result2 = manager.embed_chunk(chunk)
        print(f"\nPASS Second embedding:")
        print(f"  Cache hit: {result2.cache_hit}")
        print(f"  Processing time: {result2.processing_time:.3f}s")
        
        # Verify embeddings match
        if result1.success and result2.success:
            match = np.allclose(result1.embedding, result2.embedding)
            print(f"\nPASS Embeddings match: {match}")
        
        return result1.success and result2.cache_hit


def test_batch_embedding():
    """Test batch embedding."""
    print("\n" + "=" * 60)
    print("TEST 5: Batch Embedding")
    print("=" * 60)
    
    with tempfile.TemporaryDirectory() as temp_dir:
        config = EmbeddingConfig(
            cache_dir=temp_dir,
            batch_size=3
        )
        manager = EmbeddingManager(config)
        
        # Create test chunks
        chunks = [
            Chunk(
                content=f"Test content for chunk {i}. This is biology content about cells and organisms.",
                metadata={'subject': 'biology'},
                chunk_id=f'batch_chunk_{i:03d}',
                start_pos=0,
                end_pos=50
            )
            for i in range(7)
        ]
        
        print(f"\nPASS Embedding {len(chunks)} chunks in batches of {config.batch_size}")
        
        # Generate batch embeddings
        result = manager.embed_chunks(chunks)
        
        print(f"\nPASS Batch result:")
        print(f"  Success: {result.success}")
        print(f"  Total chunks: {result.total_chunks}")
        print(f"  Successful: {result.successful_embeddings}")
        print(f"  Failed: {result.failed_embeddings}")
        print(f"  Cache hits: {result.cache_hits}")
        print(f"  Total time: {result.total_processing_time:.3f}s")
        print(f"  Avg time/chunk: {result.total_processing_time / result.total_chunks:.3f}s")
        
        if result.success:
            print(f"\nPASS Generated {len(result.embeddings)} embeddings")
            print(f"  Embedding shape: {result.embeddings[0].shape}")
        
        return result.success


def test_batch_with_cache():
    """Test batch embedding with cache."""
    print("\n" + "=" * 60)
    print("TEST 6: Batch with Cache")
    print("=" * 60)
    
    with tempfile.TemporaryDirectory() as temp_dir:
        config = EmbeddingConfig(cache_dir=temp_dir, batch_size=5)
        manager = EmbeddingManager(config)
        
        # Create chunks
        chunks = [
            Chunk(
                content=f"Chemistry topic {i}: chemical reactions and molecular structure.",
                metadata={'subject': 'chemistry'},
                chunk_id=f'chem_chunk_{i:03d}',
                start_pos=0,
                end_pos=50
            )
            for i in range(10)
        ]
        
        # First batch (no cache)
        result1 = manager.embed_chunks(chunks)
        print(f"\nPASS First batch:")
        print(f"  Cache hits: {result1.cache_hits}")
        print(f"  Processing time: {result1.total_processing_time:.3f}s")
        
        # Second batch (all cache hits)
        result2 = manager.embed_chunks(chunks)
        print(f"\nPASS Second batch (should be cached):")
        print(f"  Cache hits: {result2.cache_hits}")
        print(f"  Processing time: {result2.total_processing_time:.3f}s")
        print(f"  Speedup: {result1.total_processing_time / result2.total_processing_time:.1f}x")
        
        # Verify all were cache hits
        all_cached = result2.cache_hits == len(chunks)
        print(f"\nPASS All chunks cached: {all_cached}")
        
        return all_cached


def test_normalization():
    """Test embedding normalization."""
    print("\n" + "=" * 60)
    print("TEST 7: Embedding Normalization")
    print("=" * 60)
    
    with tempfile.TemporaryDirectory() as temp_dir:
        # With normalization
        config_norm = EmbeddingConfig(
            cache_dir=temp_dir + "_norm",
            normalize_embeddings=True
        )
        manager_norm = EmbeddingManager(config_norm)
        
        # Without normalization
        config_no_norm = EmbeddingConfig(
            cache_dir=temp_dir + "_no_norm",
            normalize_embeddings=False
        )
        manager_no_norm = EmbeddingManager(config_no_norm)
        
        chunk = Chunk(
            content="Newton's laws of motion describe the relationship between force and motion.",
            metadata={'subject': 'physics'},
            chunk_id='physics_chunk_001',
            start_pos=0,
            end_pos=73
        )
        
        # Generate with normalization
        result_norm = manager_norm.embed_chunk(chunk)
        norm_value = np.linalg.norm(result_norm.embedding)
        print(f"\nPASS With normalization:")
        print(f"  Norm: {norm_value:.6f}")
        print(f"  Close to 1.0: {abs(norm_value - 1.0) < 0.001}")
        
        # Generate without normalization
        result_no_norm = manager_no_norm.embed_chunk(chunk)
        norm_value_no_norm = np.linalg.norm(result_no_norm.embedding)
        print(f"\nPASS Without normalization:")
        print(f"  Norm: {norm_value_no_norm:.6f}")
        
        return abs(norm_value - 1.0) < 0.001


def test_error_handling():
    """Test error handling with invalid input."""
    print("\n" + "=" * 60)
    print("TEST 8: Error Handling")
    print("=" * 60)
    
    with tempfile.TemporaryDirectory() as temp_dir:
        config = EmbeddingConfig(cache_dir=temp_dir)
        manager = EmbeddingManager(config)
        
        # Empty chunk
        chunk = Chunk(
            content="",
            metadata={},
            chunk_id='empty_chunk',
            start_pos=0,
            end_pos=0
        )
        
        print(f"\nPASS Testing empty chunk:")
        result = manager.embed_chunk(chunk)
        print(f"  Success: {result.success}")
        
        if not result.success:
            print(f"  Error: {result.error}")
        
        return True


def main():
    """Run all tests."""
    print("\n" + "=" * 60)
    print("EMBEDDING MANAGER TEST SUITE")
    print("=" * 60 + "\n")
    
    tests = [
        ("Embedding Manager Initialization", test_embedding_manager_initialization),
        ("Embedding Cache", test_embedding_cache),
        ("Single Chunk Embedding", test_single_chunk_embedding),
        ("Cache Hit", test_cache_hit),
        ("Batch Embedding", test_batch_embedding),
        ("Batch with Cache", test_batch_with_cache),
        ("Normalization", test_normalization),
        ("Error Handling", test_error_handling),
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
