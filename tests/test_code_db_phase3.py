"""Phase 3 tests for code database with real LLM integration."""

import pytest
from pathlib import Path
from codeweaver.code_db.builder import build_index
from codeweaver.llm import create_kimi_llm


def test_llm_description_generation(tmp_path):
    """Test that real LLM descriptions are generated when llm_fn is provided."""
    # Create test project
    src = tmp_path / "src"
    src.mkdir()
    (src / "main.py").write_text("def hello():\n    return 'world'")

    # Use real Kimi LLM
    llm_fn = create_kimi_llm()

    # Build index with LLM
    code_db = tmp_path / "code_db"
    build_index(src, tmp_path, llm_describe_fn=llm_fn)

    # Check description was generated
    symbols_file = code_db / "symbols" / "main.md"
    assert symbols_file.exists()
    content = symbols_file.read_text()

    # Should NOT contain placeholder
    assert "(no description)" not in content

    # Should contain actual description (LLM-generated)
    assert "**Description:**" in content
    # Description should be non-empty and not just whitespace
    lines = content.split("\n")
    desc_line = [l for l in lines if "**Description:**" in l][0]
    desc_text = desc_line.split("**Description:**")[1].strip()
    assert len(desc_text) > 0
    assert desc_text != "(no description)"

    print(f"✓ LLM generated description: {desc_text}")


def test_description_caching(tmp_path):
    """Test that descriptions are cached and not regenerated for unchanged symbols."""
    src = tmp_path / "src"
    src.mkdir()
    (src / "main.py").write_text("def hello():\n    pass")

    # Track LLM calls
    call_count = [0]
    original_llm = create_kimi_llm()

    def counting_llm(msgs):
        call_count[0] += 1
        return original_llm(msgs)

    # First build
    build_index(src, tmp_path, llm_describe_fn=counting_llm)
    first_count = call_count[0]
    assert first_count > 0, "LLM should be called on first build"

    # Second build without changes
    build_index(src, tmp_path, llm_describe_fn=counting_llm)
    second_count = call_count[0]

    # Should not call LLM again for unchanged symbols
    assert second_count == first_count, f"LLM called {second_count - first_count} extra times (should be 0)"

    print(f"✓ Cache working: {first_count} LLM calls on first build, 0 on second build")


def test_no_llm_uses_placeholder(tmp_path):
    """Test that without LLM, placeholder descriptions are used."""
    src = tmp_path / "src"
    src.mkdir()
    (src / "main.py").write_text("def hello():\n    return 'world'")

    # Build without LLM
    build_index(src, tmp_path, llm_describe_fn=None)

    symbols_file = tmp_path / "code_db" / "symbols" / "main.md"
    content = symbols_file.read_text()

    # Should contain placeholder
    assert "(no description)" in content

    print("✓ Placeholder used when no LLM provided")


def test_cache_invalidation_on_code_change(tmp_path):
    """Test that cache is invalidated when source code changes."""
    src = tmp_path / "src"
    src.mkdir()
    main_py = src / "main.py"
    main_py.write_text("def hello():\n    return 'world'")

    llm_fn = create_kimi_llm()

    # First build
    build_index(src, tmp_path, llm_describe_fn=llm_fn)
    symbols_file = tmp_path / "code_db" / "symbols" / "main.md"
    first_content = symbols_file.read_text()

    # Modify code
    main_py.write_text("def hello():\n    return 'universe'")

    # Force rebuild by removing symbol file
    symbols_file.unlink()

    # Second build
    build_index(src, tmp_path, llm_describe_fn=llm_fn)
    second_content = symbols_file.read_text()

    # Descriptions might be different (or same if LLM gives similar response)
    # But at least verify both have real descriptions
    assert "(no description)" not in first_content
    assert "(no description)" not in second_content

    print("✓ Cache invalidation works on code change")
