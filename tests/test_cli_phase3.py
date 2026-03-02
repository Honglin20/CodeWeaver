"""Tests for CLI Phase 3 commands."""

import pytest
from pathlib import Path
from typer.testing import CliRunner
from codeweaver.cli import app

runner = CliRunner()


def test_index_command_no_llm(tmp_path, monkeypatch):
    """Test codeweaver index command without LLM."""
    # Change to tmp directory
    monkeypatch.chdir(tmp_path)

    # Create test project
    src = tmp_path / "test_project"
    src.mkdir()
    (src / "main.py").write_text("def hello():\n    pass")

    # Run index command
    result = runner.invoke(app, ["index", str(src), "--no-llm"])

    assert result.exit_code == 0
    assert "Indexing" in result.stdout
    assert "Index built" in result.stdout

    # Check code_db was created
    code_db = tmp_path / ".codeweaver" / "code_db"
    assert code_db.exists()
    assert (code_db / "index.md").exists()
    assert (code_db / "symbols" / "main.md").exists()

    # Verify no LLM descriptions
    symbols_content = (code_db / "symbols" / "main.md").read_text()
    assert "(no description)" in symbols_content

    print("✓ Index command works without LLM")


def test_index_command_with_llm(tmp_path, monkeypatch):
    """Test codeweaver index command with real LLM."""
    monkeypatch.chdir(tmp_path)

    # Create test project
    src = tmp_path / "test_project"
    src.mkdir()
    (src / "calculator.py").write_text("""
def add(a, b):
    return a + b

def multiply(x, y):
    return x * y
""")

    # Run index command with LLM
    result = runner.invoke(app, ["index", str(src), "--llm"])

    assert result.exit_code == 0
    assert "with LLM descriptions" in result.stdout
    assert "Index built" in result.stdout

    # Check LLM descriptions were generated
    code_db = tmp_path / ".codeweaver" / "code_db"
    symbols_file = code_db / "symbols" / "calculator.md"
    assert symbols_file.exists()

    content = symbols_file.read_text()
    assert "(no description)" not in content
    assert "**Description:**" in content

    print("✓ Index command works with real LLM")


def test_index_command_nonexistent_directory(tmp_path, monkeypatch):
    """Test index command with nonexistent directory."""
    monkeypatch.chdir(tmp_path)

    result = runner.invoke(app, ["index", "/nonexistent/path"])

    assert result.exit_code == 1
    assert "Directory not found" in result.stdout

    print("✓ Index command handles nonexistent directory")


def test_index_command_default_uses_llm(tmp_path, monkeypatch):
    """Test that index command uses LLM by default."""
    monkeypatch.chdir(tmp_path)

    src = tmp_path / "test_project"
    src.mkdir()
    (src / "main.py").write_text("def test(): pass")

    # Run without explicit flag (should default to --llm)
    result = runner.invoke(app, ["index", str(src)])

    assert result.exit_code == 0
    assert "with LLM descriptions" in result.stdout

    # Verify LLM was used
    code_db = tmp_path / ".codeweaver" / "code_db"
    symbols_content = (code_db / "symbols" / "main.md").read_text()
    assert "(no description)" not in symbols_content

    print("✓ Index command defaults to using LLM")
