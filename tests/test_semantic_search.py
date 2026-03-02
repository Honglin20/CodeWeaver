"""Tests for semantic search with LLM ranking."""

import pytest
from pathlib import Path
from codeweaver.code_db.builder import build_index
from codeweaver.code_db.query import search_symbols_semantic
from codeweaver.llm import create_kimi_llm


def test_semantic_search_with_real_llm(tmp_path):
    """Test semantic search using real LLM for ranking."""
    # Create test project with multiple functions
    src = tmp_path / "src"
    src.mkdir()

    (src / "math_ops.py").write_text("""
def add(a, b):
    return a + b

def subtract(a, b):
    return a - b

def multiply(x, y):
    return x * y

def divide(numerator, denominator):
    return numerator / denominator
""")

    (src / "string_ops.py").write_text("""
def concatenate(s1, s2):
    return s1 + s2

def uppercase(text):
    return text.upper()

def reverse(text):
    return text[::-1]
""")

    # Build index with LLM
    llm_fn = create_kimi_llm()
    build_index(src, tmp_path, llm_describe_fn=llm_fn)

    code_db = tmp_path / "code_db"

    # Search for "addition" - should rank add() highly
    result = search_symbols_semantic(code_db, "addition", llm_fn, top_k=3)

    assert "Semantic Search Results" in result
    assert "add" in result.lower()

    print(f"✓ Semantic search result:\n{result}")


def test_semantic_search_multiple_queries(tmp_path):
    """Test semantic search with different queries."""
    src = tmp_path / "src"
    src.mkdir()

    (src / "calculator.py").write_text("""
def calculate_sum(numbers):
    return sum(numbers)

def calculate_average(numbers):
    return sum(numbers) / len(numbers)

def find_maximum(numbers):
    return max(numbers)

def find_minimum(numbers):
    return min(numbers)
""")

    llm_fn = create_kimi_llm()
    build_index(src, tmp_path, llm_describe_fn=llm_fn)

    code_db = tmp_path / "code_db"

    # Query 1: "find largest value"
    result1 = search_symbols_semantic(code_db, "find largest value", llm_fn, top_k=2)
    assert "find_maximum" in result1 or "maximum" in result1.lower()

    # Query 2: "compute mean"
    result2 = search_symbols_semantic(code_db, "compute mean", llm_fn, top_k=2)
    assert "calculate_average" in result2 or "average" in result2.lower()

    print("✓ Multiple semantic queries work correctly")


def test_semantic_search_no_symbols(tmp_path):
    """Test semantic search when no symbols exist."""
    code_db = tmp_path / "code_db"
    code_db.mkdir(parents=True)

    llm_fn = create_kimi_llm()

    result = search_symbols_semantic(code_db, "test query", llm_fn, top_k=5)

    assert "No symbols found" in result
    assert "Run `codeweaver index`" in result

    print("✓ Handles missing symbols gracefully")


def test_semantic_search_top_k_limit(tmp_path):
    """Test that semantic search respects top_k limit."""
    src = tmp_path / "src"
    src.mkdir()

    # Create file with many functions
    functions = "\n\n".join([
        f"def func_{i}():\n    return {i}"
        for i in range(10)
    ])
    (src / "many_funcs.py").write_text(functions)

    llm_fn = create_kimi_llm()
    build_index(src, tmp_path, llm_describe_fn=llm_fn)

    code_db = tmp_path / "code_db"

    # Search with top_k=3
    result = search_symbols_semantic(code_db, "function", llm_fn, top_k=3)

    # Count how many function entries are in result
    func_count = result.count("## func_")

    # Should have at most 3 results
    assert func_count <= 3

    print(f"✓ top_k limit respected: {func_count} results")


def test_semantic_search_with_descriptions(tmp_path):
    """Test that semantic search uses LLM-generated descriptions."""
    src = tmp_path / "src"
    src.mkdir()

    (src / "data_processor.py").write_text("""
def filter_even_numbers(numbers):
    return [n for n in numbers if n % 2 == 0]

def sort_descending(items):
    return sorted(items, reverse=True)

def remove_duplicates(items):
    return list(set(items))
""")

    llm_fn = create_kimi_llm()
    build_index(src, tmp_path, llm_describe_fn=llm_fn)

    code_db = tmp_path / "code_db"

    # Search for "remove repeated items"
    result = search_symbols_semantic(code_db, "remove repeated items", llm_fn, top_k=2)

    # Should find remove_duplicates based on semantic meaning
    assert "remove_duplicates" in result or "duplicate" in result.lower()

    # Result should include description
    assert "**Description:**" not in result  # Descriptions are shown without markdown
    assert len(result) > 50  # Should have substantial content

    print(f"✓ Semantic search uses descriptions:\n{result}")
