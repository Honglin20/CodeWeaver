"""Tests for code editing tool with change notification."""

import pytest
from pathlib import Path
from codeweaver.tools.code_edit import edit_code, insert_code
from codeweaver.llm import create_kimi_llm


def test_edit_code_updates_file_and_notifies(tmp_path):
    """Test that edit_code modifies file and triggers notification."""
    src = tmp_path / "src"
    src.mkdir()
    main_py = src / "main.py"
    main_py.write_text("def old():\n    pass")

    memory = tmp_path / "memory"
    code_db = tmp_path / "code_db"

    # Edit code
    result = edit_code(
        str(main_py),
        "def old():\n    pass",
        "def new():\n    pass",
        memory,
        code_db,
        src,
        llm_fn=None,
    )

    assert result["success"]
    assert "Edited" in result["message"]
    assert main_py.read_text() == "def new():\n    pass"

    # Check notification was written
    notif_file = memory / "notifications" / "code_changes.md"
    assert notif_file.exists()
    content = notif_file.read_text()
    assert str(main_py) in content
    assert "modified" in content

    # Check code database was updated
    symbols_file = code_db / "symbols" / "main.md"
    assert symbols_file.exists()
    symbols_content = symbols_file.read_text()
    assert "def new()" in symbols_content
    assert "def old()" not in symbols_content

    print("✓ edit_code updates file and triggers notification")


def test_edit_code_with_real_llm(tmp_path):
    """Test edit_code with real LLM description generation."""
    src = tmp_path / "src"
    src.mkdir()
    calc_py = src / "calculator.py"
    calc_py.write_text("def add(a, b):\n    return a + b")

    memory = tmp_path / "memory"
    code_db = tmp_path / "code_db"
    llm_fn = create_kimi_llm()

    # Edit with LLM
    result = edit_code(
        str(calc_py),
        "def add(a, b):\n    return a + b",
        "def add(a, b):\n    \"\"\"Add two numbers.\"\"\"\n    return a + b",
        memory,
        code_db,
        src,
        llm_fn=llm_fn,
    )

    assert result["success"]

    # Check LLM description was generated
    symbols_file = code_db / "symbols" / "calculator.md"
    content = symbols_file.read_text()
    assert "(no description)" not in content
    assert "**Description:**" in content

    print("✓ edit_code works with real LLM")


def test_edit_code_validates_python_syntax(tmp_path):
    """Test that edit_code validates Python syntax."""
    src = tmp_path / "src"
    src.mkdir()
    main_py = src / "main.py"
    main_py.write_text("def hello():\n    pass")

    memory = tmp_path / "memory"
    code_db = tmp_path / "code_db"

    # Try to edit with invalid Python
    result = edit_code(
        str(main_py),
        "def hello():\n    pass",
        "def invalid(\n    # missing closing paren",
        memory,
        code_db,
        src,
        llm_fn=None,
    )

    assert not result["success"]
    assert "not valid Python" in result["message"]

    # Original file should be unchanged
    assert main_py.read_text() == "def hello():\n    pass"

    print("✓ edit_code validates Python syntax")


def test_edit_code_handles_missing_old_code(tmp_path):
    """Test edit_code when old_code is not found."""
    src = tmp_path / "src"
    src.mkdir()
    main_py = src / "main.py"
    main_py.write_text("def hello():\n    pass")

    memory = tmp_path / "memory"
    code_db = tmp_path / "code_db"

    result = edit_code(
        str(main_py),
        "def nonexistent():\n    pass",
        "def new():\n    pass",
        memory,
        code_db,
        src,
        llm_fn=None,
    )

    assert not result["success"]
    assert "Old code not found" in result["message"]

    print("✓ edit_code handles missing old_code")


def test_insert_code_at_start(tmp_path):
    """Test inserting code at the start of a file."""
    src = tmp_path / "src"
    src.mkdir()
    main_py = src / "main.py"
    main_py.write_text("def existing():\n    pass")

    memory = tmp_path / "memory"
    code_db = tmp_path / "code_db"

    result = insert_code(
        str(main_py),
        "# Header comment",
        "start",
        memory,
        code_db,
        src,
        llm_fn=None,
    )

    assert result["success"]
    content = main_py.read_text()
    assert content.startswith("# Header comment\n")
    assert "def existing()" in content

    print("✓ insert_code works at start")


def test_insert_code_at_end(tmp_path):
    """Test inserting code at the end of a file."""
    src = tmp_path / "src"
    src.mkdir()
    main_py = src / "main.py"
    main_py.write_text("def existing():\n    pass")

    memory = tmp_path / "memory"
    code_db = tmp_path / "code_db"

    result = insert_code(
        str(main_py),
        "def new_function():\n    pass",
        "end",
        memory,
        code_db,
        src,
        llm_fn=None,
    )

    assert result["success"]
    content = main_py.read_text()
    assert content.endswith("def new_function():\n    pass")

    print("✓ insert_code works at end")


def test_insert_code_after_pattern(tmp_path):
    """Test inserting code after a specific pattern."""
    src = tmp_path / "src"
    src.mkdir()
    main_py = src / "main.py"
    main_py.write_text("def first():\n    pass\n\ndef second():\n    pass")

    memory = tmp_path / "memory"
    code_db = tmp_path / "code_db"

    result = insert_code(
        str(main_py),
        "def inserted():\n    pass",
        "after:def first():\n    pass",
        memory,
        code_db,
        src,
        llm_fn=None,
    )

    assert result["success"]
    content = main_py.read_text()
    assert "def first():\n    pass\ndef inserted():" in content

    print("✓ insert_code works after pattern")


def test_insert_code_validates_syntax(tmp_path):
    """Test that insert_code validates Python syntax."""
    src = tmp_path / "src"
    src.mkdir()
    main_py = src / "main.py"
    main_py.write_text("def hello():\n    pass")

    memory = tmp_path / "memory"
    code_db = tmp_path / "code_db"

    result = insert_code(
        str(main_py),
        "def invalid(\n    # bad syntax",
        "end",
        memory,
        code_db,
        src,
        llm_fn=None,
    )

    assert not result["success"]
    assert "Invalid Python code" in result["message"]

    print("✓ insert_code validates syntax")
