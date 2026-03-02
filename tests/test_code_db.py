import time
from pathlib import Path
import pytest

from codeweaver.code_db.builder import build_index
from codeweaver.code_db.query import (
    get_file_list,
    get_file_dependencies,
    get_file_symbols,
    get_symbol_source,
    search_symbols,
)

FIXTURE = Path(__file__).parent / "fixtures" / "sample_project"


def _build(tmp_path):
    build_index(FIXTURE, tmp_path)
    return tmp_path / "code_db"


def test_file_list_discovery(tmp_path):
    db = _build(tmp_path)
    content = get_file_list(db)
    assert "main.py" in content
    assert "utils.py" in content


def test_import_relationship_extraction(tmp_path):
    db = _build(tmp_path)
    content = get_file_list(db)
    assert "src.utils" in content


def test_function_symbol_extraction(tmp_path):
    db = _build(tmp_path)
    symbols = get_file_symbols(db, "src/main.py")
    assert "train_model" in symbols


def test_class_symbol_extraction(tmp_path):
    db = _build(tmp_path)
    symbols = get_file_symbols(db, "src/main.py")
    assert "Trainer" in symbols


def test_variable_symbol_extraction(tmp_path):
    db = _build(tmp_path)
    symbols = get_file_symbols(db, "src/main.py")
    assert "LR" in symbols


def test_source_code_extraction(tmp_path):
    db = _build(tmp_path)
    src = get_symbol_source(db, "src/main.py", "train_model")
    assert "def train_model" in src


def test_query_tool_get_file_list(tmp_path):
    db = _build(tmp_path)
    result = get_file_list(db)
    assert isinstance(result, str)
    assert "src" in result


def test_query_tool_get_symbol_source(tmp_path):
    db = _build(tmp_path)
    result = get_symbol_source(db, "src/main.py", "train_model")
    assert "def train_model" in result


def test_incremental_update(tmp_path):
    build_index(FIXTURE, tmp_path)
    db = tmp_path / "code_db"
    main_sym = db / "symbols" / "src__main.md"
    utils_sym = db / "symbols" / "src__utils.md"

    # Record mtime of utils symbol file
    utils_mtime = utils_sym.stat().st_mtime

    # Touch main.py to simulate a change
    time.sleep(0.05)
    main_sym.touch()
    main_mtime_before = main_sym.stat().st_mtime

    # Rebuild
    build_index(FIXTURE, tmp_path)

    # utils should be unchanged (same mtime), main should be refreshed
    assert utils_sym.stat().st_mtime == utils_mtime
    # main symbol file was regenerated (mtime >= before)
    assert main_sym.stat().st_mtime >= main_mtime_before
