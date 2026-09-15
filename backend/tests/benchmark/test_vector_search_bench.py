"""
Performance Benchmark Tests for Vector Search
向量搜索性能基准测试

Tests performance characteristics:
1. Vector similarity computation
2. Batch vector operations
3. Index lookup performance
4. Memory usage with large vector collections
"""
import pytest
import time
import tracemalloc
import numpy as np


@pytest.mark.benchmark
def test_vector_similarity_cosine():
    """
    Benchmark cosine similarity computation
    余弦相似度计算性能基准
    """
    # Create test vectors
    vector_sizes = [128, 256, 512, 1024, 1536]

    for size in vector_sizes:
        vec1 = np.random.rand(size).astype(np.float32)
        vec2 = np.random.rand(size).astype(np.float32)

        start = time.time()

        # Compute cosine similarity 1000 times
        for i in range(1000):
            dot_product = np.dot(vec1, vec2)
            norm1 = np.linalg.norm(vec1)
            norm2 = np.linalg.norm(vec2)
            similarity = dot_product / (norm1 * norm2)

        elapsed = time.time() - start

        # Should be fast (< 100ms for 1000 computations)
        print(f"Vector size {size}: {elapsed:.4f}s for 1000 similarities")
        assert elapsed < 0.1


@pytest.mark.benchmark
def test_vector_similarity_euclidean():
    """
    Benchmark Euclidean distance computation
    欧几里得距离计算性能基准
    """
    vector_sizes = [128, 256, 512, 1024, 1536]

    for size in vector_sizes:
        vec1 = np.random.rand(size).astype(np.float32)
        vec2 = np.random.rand(size).astype(np.float32)

        start = time.time()

        # Compute Euclidean distance 1000 times
        for i in range(1000):
            distance = np.linalg.norm(vec1 - vec2)

        elapsed = time.time() - start

        # Should be fast
        print(f"Vector size {size}: {elapsed:.4f}s for 1000 distances")
        assert elapsed < 0.1


@pytest.mark.benchmark
def test_batch_vector_operations():
    """
    Benchmark batch vector operations
    批量向量操作性能基准
    """
    # Create batch of vectors
    batch_size = 100
    vector_size = 512

    vectors = np.random.rand(batch_size, vector_size).astype(np.float32)
    query_vector = np.random.rand(vector_size).astype(np.float32)

    start = time.time()

    # Compute similarities for entire batch
    for i in range(100):
        similarities = np.dot(vectors, query_vector)
        norms = np.linalg.norm(vectors, axis=1) * np.linalg.norm(query_vector)
        cosine_sims = similarities / norms

    elapsed = time.time() - start

    # Should be fast (< 50ms for 100 batch operations)
    assert elapsed < 0.05


@pytest.mark.benchmark
def test_knn_search():
    """
    Benchmark k-nearest neighbors search
    K近邻搜索性能基准
    """
    # Create vector collection
    collection_size = 1000
    vector_size = 512

    collection = np.random.rand(collection_size, vector_size).astype(np.float32)
    query = np.random.rand(vector_size).astype(np.float32)

    start = time.time()

    # Find top 10 nearest neighbors (100 queries)
    for i in range(100):
        similarities = np.dot(collection, query)
        top_k_indices = np.argsort(similarities)[-10:][::-1]
        top_k_similarities = similarities[top_k_indices]

    elapsed = time.time() - start

    # Should be fast (< 100ms for 100 KNN queries on 1000 vectors)
    assert elapsed < 0.1


@pytest.mark.benchmark
def test_vector_normalization():
    """
    Benchmark vector normalization
    向量归一化性能基准
    """
    vector_sizes = [128, 256, 512, 1024, 1536]

    for size in vector_sizes:
        vectors = np.random.rand(100, size).astype(np.float32)

        start = time.time()

        # Normalize all vectors
        for i in range(100):
            norms = np.linalg.norm(vectors, axis=1, keepdims=True)
            normalized = vectors / norms

        elapsed = time.time() - start

        # Should be fast (< 20ms for 100 normalizations)
        assert elapsed < 0.02


@pytest.mark.benchmark
def test_vector_memory_usage():
    """
    Test memory usage with large vector collections
    大向量集合内存使用测试
    """
    tracemalloc.start()

    collection_sizes = [1000, 5000, 10000, 50000]
    vector_size = 512

    for size in collection_sizes:
        vectors = np.random.rand(size, vector_size).astype(np.float32)
        current, peak = tracemalloc.get_traced_memory()

        # Check memory usage
        memory_per_vector_mb = (current / size) / 1024 / 1024
        print(f"Collection size {size}: {current / 1024 / 1024:.2f}MB total, {memory_per_vector_mb:.6f}MB per vector")

        # 512 floats ≈ 2KB per vector
        assert memory_per_vector_mb < 0.01  # < 10KB per vector

    tracemalloc.stop()


@pytest.mark.benchmark
def test_index_building():
    """
    Benchmark building vector index
    向量索引构建性能基准
    """
    collection_sizes = [100, 500, 1000, 5000]
    vector_size = 512

    for size in collection_sizes:
        vectors = np.random.rand(size, vector_size).astype(np.float32)

        start = time.time()

        # Build simple index (normalize all vectors)
        norms = np.linalg.norm(vectors, axis=1, keepdims=True)
        normalized_vectors = vectors / norms

        elapsed = time.time() - start

        print(f"Index size {size}: {elapsed:.4f}s to build")
        # Should scale reasonably
        assert elapsed < 1.0  # < 1 second for any size


@pytest.mark.benchmark
def test_approximate_search():
    """
    Simulate approximate nearest neighbor search
    近似近邻搜索模拟
    """
    # In production, this would use HNSW or IVF indices
    # Here we simulate the performance characteristics
    collection_size = 10000
    vector_size = 512

    collection = np.random.rand(collection_size, vector_size).astype(np.float32)
    query = np.random.rand(vector_size).astype(np.float32)

    # Pre-normalize for fast similarity
    norms = np.linalg.norm(collection, axis=1, keepdims=True)
    normalized_collection = collection / norms
    query_norm = np.linalg.norm(query)
    normalized_query = query / query_norm

    start = time.time()

    # Perform 100 approximate searches
    for i in range(100):
        # Use top-k instead of full sort
        similarities = np.dot(normalized_collection, normalized_query)
        # Instead of full sort, use argpartition for top 10
        k = 10
        top_indices = np.argpartition(similarities, -k)[-k:]
        top_k_indices = top_indices[np.argsort(-similarities[top_indices])]

    elapsed = time.time() - start

    # Should be fast (< 200ms for 100 searches on 10k vectors)
    assert elapsed < 0.2


@pytest.mark.benchmark
def test_vector_serialization():
    """
    Benchmark vector serialization/deserialization
    向量序列化/反序列化性能基准
    """
    import json

    vector_sizes = [128, 512, 1024]

    for size in vector_sizes:
        vectors = np.random.rand(100, size).astype(np.float32).tolist()

        # Serialization
        start = time.time()
        for i in range(100):
            json_str = json.dumps(vectors)
        serialize_time = time.time() - start

        # Deserialization
        start = time.time()
        for i in range(100):
            parsed = json.loads(json_str)
        deserialize_time = time.time() - start

        print(f"Vector size {size}: serialize {serialize_time:.4f}s, deserialize {deserialize_time:.4f}s")
        # Should be fast
        assert serialize_time < 0.1
        assert deserialize_time < 0.1


@pytest.mark.benchmark
def test_batch_query_processing():
    """
    Benchmark batch query processing
    批量查询处理性能基准
    """
    collection_size = 5000
    vector_size = 512
    batch_size = 50

    collection = np.random.rand(collection_size, vector_size).astype(np.float32)
    queries = np.random.rand(batch_size, vector_size).astype(np.float32)

    start = time.time()

    # Process batch of queries
    for query in queries:
        similarities = np.dot(collection, query)
        top_k = np.argsort(similarities)[-10:][::-1]

    elapsed = time.time() - start

    # Should process 50 queries reasonably fast
    assert elapsed < 0.5


@pytest.mark.benchmark
def test_vector_filtering():
    """
    Benchmark vector filtering with metadata
    元数据过滤向量查询性能基准
    """
    collection_size = 1000
    vector_size = 512

    vectors = np.random.rand(collection_size, vector_size).astype(np.float32)
    metadata = [
        {"category": "cat" if i % 2 == 0 else "dog", "id": i}
        for i in range(collection_size)
    ]

    query = np.random.rand(vector_size).astype(np.float32)

    start = time.time()

    # Filtered search (only "cat" category)
    for i in range(100):
        # Compute all similarities
        similarities = np.dot(vectors, query)

        # Apply filter
        cat_indices = [j for j, meta in enumerate(metadata) if meta["category"] == "cat"]
        filtered_similarities = [(j, similarities[j]) for j in cat_indices]

        # Get top k
        sorted_results = sorted(filtered_similarities, key=lambda x: x[1], reverse=True)[:10]

    elapsed = time.time() - start

    # Filtered search should still be reasonably fast
    assert elapsed < 0.5


@pytest.mark.benchmark
def test_vector_update_operations():
    """
    Benchmark vector update operations
    向量更新操作性能基准
    """
    collection_size = 1000
    vector_size = 512

    collection = np.random.rand(collection_size, vector_size).astype(np.float32)

    start = time.time()

    # Perform 100 updates
    for i in range(100):
        index = i % collection_size
        new_vector = np.random.rand(vector_size).astype(np.float32)
        collection[index] = new_vector

    elapsed = time.time() - start

    # Updates should be very fast
    assert elapsed < 0.01


@pytest.mark.benchmark
def test_multilingual_vector_sizes():
    """
    Test performance with different embedding model sizes
    不同嵌入模型大小性能测试
    """
    # Simulate different embedding sizes
    model_sizes = {
        "multilingual-e5-small": 384,
        "multilingual-e5-base": 768,
        "multilingual-e5-large": 1024,
        "openai-text-embedding-3-small": 1536,
        "openai-text-embedding-3-large": 3072,
    }

    query_count = 100

    for model, size in model_sizes.items():
        vectors = np.random.rand(1000, size).astype(np.float32)
        query = np.random.rand(size).astype(np.float32)

        start = time.time()

        # Perform similarity search
        for i in range(query_count):
            similarities = np.dot(vectors, query)
            top_k = np.argsort(similarities)[-10:]

        elapsed = time.time() - start

        print(f"{model} (size={size}): {elapsed:.4f}s for {query_count} queries")
        # Larger vectors should still be reasonably fast
        assert elapsed < 1.0


@pytest.mark.benchmark
def test_sparse_vs_dense_vectors():
    """
    Compare sparse vs dense vector operations
    稀疏与密集向量操作对比
    """
    vector_size = 512

    # Dense vectors
    dense_vec1 = np.random.rand(vector_size).astype(np.float32)
    dense_vec2 = np.random.rand(vector_size).astype(np.float32)

    start = time.time()
    for i in range(1000):
        dense_sim = np.dot(dense_vec1, dense_vec2)
    dense_time = time.time() - start

    # Sparse vectors (90% zeros)
    sparse_vec1 = np.random.rand(vector_size).astype(np.float32) * np.random.choice([0, 1], size=vector_size, p=[0.9, 0.1])
    sparse_vec2 = np.random.rand(vector_size).astype(np.float32) * np.random.choice([0, 1], size=vector_size, p=[0.9, 0.1])

    start = time.time()
    for i in range(1000):
        sparse_sim = np.dot(sparse_vec1, sparse_vec2)
    sparse_time = time.time() - start

    print(f"Dense: {dense_time:.4f}s, Sparse: {sparse_time:.4f}s")
    # Dense should be faster or similar (NumPy optimizations)
    assert dense_time <= sparse_time * 2
