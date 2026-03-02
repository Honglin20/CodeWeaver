"""Tests for change notification system."""

import pytest
from pathlib import Path
from codeweaver.code_db.builder import build_index
from codeweaver.code_db.watcher import notify_code_change
from codeweaver.llm import create_kimi_llm


def test_notify_code_change_reindexes(tmp_path):
    """Test that notify_code_change re-indexes the changed file."""
    src = tmp_path / "src"
    src.mkdir()
    main_py = src / "main.py"
    main_py.write_text("def old():\n    pass")

    code_db = tmp_path / "code_db"
    memory = tmp_path / "memory"

    # Initial index
    build_index(src, tmp_path, llm_describe_fn=None)

    # Verify old function exists
    symbols_file = code_db / "symbols" / "main.md"
    content = symbols_file.read_text()
    assert "def old()" in content

    # Modify file
    main_py.write_text("def new():\n    pass")

    # Notify change
    notify_code_change(main_py, "modified", memory, code_db, src, llm_fn=None)

    # Check symbols were updated
    content = symbols_file.read_text()
    assert "def new()" in content
    assert "def old()" not in content

    print("✓ File re-indexed after modification")


def test_notification_written_to_memory(tmp_path):
    """Test that notification is written to memory/notifications/."""
    src = tmp_path / "src"
    src.mkdir()
    main_py = src / "main.py"
    main_py.write_text("def hello():\n    pass")

    memory = tmp_path / "memory"
    code_db = tmp_path / "code_db"

    notify_code_change(main_py, "modified", memory, code_db, src, llm_fn=None)

    notif_file = memory / "notifications" / "code_changes.md"
    assert notif_file.exists()
    content = notif_file.read_text()
    assert str(main_py) in content
    assert "modified" in content
    assert "Symbols updated:" in content

    print("✓ Notification written to memory")


def test_notify_with_real_llm(tmp_path):
    """Test notification with real LLM description generation."""
    src = tmp_path / "src"
    src.mkdir()
    main_py = src / "main.py"
    main_py.write_text("def calculate_sum(a, b):\n    return a + b")

    memory = tmp_path / "memory"
    code_db = tmp_path / "code_db"

    llm_fn = create_kimi_llm()

    # Notify change with LLM
    notify_code_change(main_py, "created", memory, code_db, src, llm_fn=llm_fn)

    # Check LLM description was generated
    symbols_file = code_db / "symbols" / "main.md"
    content = symbols_file.read_text()
    assert "(no description)" not in content
    assert "**Description:**" in content

    # Extract description
    lines = content.split("\n")
    desc_line = [l for l in lines if "**Description:**" in l][0]
    desc_text = desc_line.split("**Description:**")[1].strip()
    assert len(desc_text) > 0

    print(f"✓ LLM description generated: {desc_text}")


def test_notify_deleted_file(tmp_path):
    """Test notification when file is deleted."""
    src = tmp_path / "src"
    src.mkdir()
    main_py = src / "main.py"
    main_py.write_text("def hello():\n    pass")

    code_db = tmp_path / "code_db"
    memory = tmp_path / "memory"

    # Initial index
    build_index(src, tmp_path, llm_describe_fn=None)

    symbols_file = code_db / "symbols" / "main.md"
    assert symbols_file.exists()

    # Notify deletion
    notify_code_change(main_py, "deleted", memory, code_db, src, llm_fn=None)

    # Symbol file should be removed
    assert not symbols_file.exists()

    # Notification should be written
    notif_file = memory / "notifications" / "code_changes.md"
    assert notif_file.exists()
    content = notif_file.read_text()
    assert "deleted" in content

    print("✓ Deleted file handled correctly")


def test_multiple_notifications_append(tmp_path):
    """Test that multiple notifications are appended to the same file."""
    src = tmp_path / "src"
    src.mkdir()
    file1 = src / "file1.py"
    file2 = src / "file2.py"
    file1.write_text("def func1(): pass")
    file2.write_text("def func2(): pass")

    memory = tmp_path / "memory"
    code_db = tmp_path / "code_db"

    # First notification
    notify_code_change(file1, "created", memory, code_db, src, llm_fn=None)

    # Second notification
    notify_code_change(file2, "created", memory, code_db, src, llm_fn=None)

    # Check both notifications are in the file
    notif_file = memory / "notifications" / "code_changes.md"
    content = notif_file.read_text()
    assert str(file1) in content
    assert str(file2) in content
    assert content.count("##") >= 2  # At least 2 notification entries

    print("✓ Multiple notifications appended correctly")
