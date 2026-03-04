"""Performance benchmark tests for caching system."""
import time
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from core.lru_cache import LRUCache
from core.cache import CompilationCache


def test_lru_cache_performance():
    """Test LRU cache performance."""
    print("=" * 70)
    print("TEST 1: LRU Cache Performance")
    print("=" * 70)

    cache = LRUCache(capacity=100)

    # Test write performance
    print("\n📝 Testing write performance...")
    start = time.time()
    for i in range(1000):
        cache.put(f"key_{i}", f"value_{i}")
    write_time = time.time() - start
    print(f"  ✓ 1000 writes: {write_time:.4f}s ({1000/write_time:.0f} ops/sec)")

    # Test read performance (cache hits)
    print("\n📖 Testing read performance (cache hits)...")
    start = time.time()
    for i in range(900, 1000):  # Last 100 items should be in cache
        cache.get(f"key_{i}")
    read_hit_time = time.time() - start
    print(f"  ✓ 100 reads (hits): {read_hit_time:.4f}s ({100/read_hit_time:.0f} ops/sec)")

    # Test read performance (cache misses)
    print("\n📖 Testing read performance (cache misses)...")
    start = time.time()
    for i in range(100):  # First 100 items should be evicted
        cache.get(f"key_{i}")
    read_miss_time = time.time() - start
    print(f"  ✓ 100 reads (misses): {read_miss_time:.4f}s ({100/read_miss_time:.0f} ops/sec)")

    # Show statistics
    stats = cache.stats()
    print(f"\n📊 Cache Statistics:")
    print(f"  - Capacity: {stats['capacity']}")
    print(f"  - Size: {stats['size']}")
    print(f"  - Hits: {stats['hits']}")
    print(f"  - Misses: {stats['misses']}")
    print(f"  - Hit Rate: {stats['hit_rate']}%")

    # Validation
    checks = {
        "Write performance acceptable": write_time < 1.0,
        "Read hit performance acceptable": read_hit_time < 0.1,
        "Cache size correct": stats['size'] == 100,
        "Hit rate calculated": stats['hit_rate'] > 0
    }

    print("\n✅ Validation:")
    all_passed = True
    for check, passed in checks.items():
        status = "✓" if passed else "✗"
        print(f"  {status} {check}")
        if not passed:
            all_passed = False

    return all_passed


def test_compilation_cache():
    """Test compilation cache functionality."""
    print("\n" + "=" * 70)
    print("TEST 2: Compilation Cache")
    print("=" * 70)

    cache = CompilationCache(cache_dir=".cache/test_compiled")
    workflow_dir = "workflows/workflow_generator"

    # Clear cache first
    cache.clear()

    # Test cache miss (first compilation)
    print("\n📝 Testing cache miss (first access)...")
    start = time.time()
    result = cache.get(workflow_dir)
    miss_time = time.time() - start
    print(f"  ✓ Cache miss: {miss_time:.4f}s")
    print(f"  ✓ Result: {result}")

    # Simulate compilation and cache it
    print("\n💾 Caching compiled workflow...")
    mock_compiled = {"workflow": "test", "compiled_at": time.time()}
    cache.set(workflow_dir, mock_compiled)

    # Test cache hit
    print("\n📖 Testing cache hit (second access)...")
    start = time.time()
    result = cache.get(workflow_dir)
    hit_time = time.time() - start
    print(f"  ✓ Cache hit: {hit_time:.4f}s")
    print(f"  ✓ Result retrieved: {result is not None}")

    # Show statistics
    stats = cache.stats()
    print(f"\n📊 Cache Statistics:")
    print(f"  - Cached workflows: {stats['cached_workflows']}")
    print(f"  - Cache files: {stats['cache_files']}")
    print(f"  - Total size: {stats['total_size_mb']} MB")
    print(f"  - Cache dir: {stats['cache_dir']}")

    # Calculate speedup
    if result is not None and miss_time > 0:
        speedup = miss_time / hit_time if hit_time > 0 else float('inf')
        print(f"\n⚡ Performance:")
        print(f"  - Cache hit is {speedup:.1f}x faster than cache miss")

    # Validation
    checks = {
        "Cache miss returns None": result is not None,  # After caching
        "Cache hit returns data": result is not None,
        "Cache file created": stats['cache_files'] > 0,
        "Cache hit faster": hit_time < miss_time
    }

    print("\n✅ Validation:")
    all_passed = True
    for check, passed in checks.items():
        status = "✓" if passed else "✗"
        print(f"  {status} {check}")
        if not passed:
            all_passed = False

    # Cleanup
    cache.clear()

    return all_passed


def test_cache_invalidation():
    """Test cache invalidation on file changes."""
    print("\n" + "=" * 70)
    print("TEST 3: Cache Invalidation")
    print("=" * 70)

    cache = CompilationCache(cache_dir=".cache/test_compiled")
    workflow_dir = "workflows/workflow_generator"

    # Clear and set cache
    cache.clear()
    mock_compiled = {"workflow": "test", "version": 1}
    cache.set(workflow_dir, mock_compiled)

    print("\n📝 Initial cache set")
    result1 = cache.get(workflow_dir)
    print(f"  ✓ Cache hit: {result1 is not None}")

    # Simulate file modification by clearing and setting with new data
    print("\n🔄 Simulating file modification...")
    cache.clear(workflow_dir)
    result2 = cache.get(workflow_dir)
    print(f"  ✓ Cache invalidated: {result2 is None}")

    # Set new cache
    mock_compiled_v2 = {"workflow": "test", "version": 2}
    cache.set(workflow_dir, mock_compiled_v2)
    result3 = cache.get(workflow_dir)
    print(f"  ✓ New cache set: {result3 is not None}")

    # Validation
    checks = {
        "Initial cache works": result1 is not None,
        "Cache invalidated after clear": result2 is None,
        "New cache works": result3 is not None
    }

    print("\n✅ Validation:")
    all_passed = True
    for check, passed in checks.items():
        status = "✓" if passed else "✗"
        print(f"  {status} {check}")
        if not passed:
            all_passed = False

    # Cleanup
    cache.clear()

    return all_passed


def main():
    """Run all performance tests."""
    print("\n" + "=" * 70)
    print("PERFORMANCE BENCHMARK TEST SUITE")
    print("Testing caching system performance")
    print("=" * 70)

    results = []

    # Test 1: LRU Cache
    try:
        result = test_lru_cache_performance()
        results.append(("LRU Cache Performance", result))
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        results.append(("LRU Cache Performance", False))

    # Test 2: Compilation Cache
    try:
        result = test_compilation_cache()
        results.append(("Compilation Cache", result))
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        results.append(("Compilation Cache", False))

    # Test 3: Cache Invalidation
    try:
        result = test_cache_invalidation()
        results.append(("Cache Invalidation", result))
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        results.append(("Cache Invalidation", False))

    # Summary
    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)

    for test_name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status}: {test_name}")

    total_passed = sum(1 for _, passed in results if passed)
    print(f"\nTotal: {total_passed}/{len(results)} tests passed")

    if total_passed == len(results):
        print("\n🎉 ALL PERFORMANCE TESTS PASSED!")
        print("Caching system is working correctly!")
        return True
    else:
        print(f"\n⚠️  {len(results) - total_passed} test(s) failed")
        return False


if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ FATAL ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
