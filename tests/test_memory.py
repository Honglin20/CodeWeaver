from pathlib import Path
import pytest
from codeweaver.memory.manager import MemoryManager


def mm(tmp_path) -> MemoryManager:
    return MemoryManager(tmp_path)


def test_write_and_read_step_full(tmp_path):
    m = mm(tmp_path)
    m.write_step_full(0, "hello")
    assert m.read_step(0, full=True) == "hello"


def test_iteration_creates_new_dir(tmp_path):
    m = mm(tmp_path)
    m.write_step_full(1, "iter1", iteration=1)
    m.write_step_full(1, "iter2", iteration=2)
    assert (tmp_path / "steps" / "step_1" / "iter_1" / "full.md").exists()
    assert (tmp_path / "steps" / "step_1" / "iter_2" / "full.md").exists()


def test_compress_step_creates_meta(tmp_path):
    m = mm(tmp_path)
    m.compress_step(2, 0, "summary text")
    assert (tmp_path / "steps" / "step_2" / "meta.md").read_text() == "summary text"


def test_load_agent_memory_bundle_structure(tmp_path):
    m = mm(tmp_path)
    m.write_agent_context("bot", "ctx")
    m.append_agent_history("bot", "hist")
    m.write_step_full(0, "step0full")
    m.compress_step(1, 0, "step1meta")
    bundle = m.load_agent_memory_bundle("bot", current_step=0, total_steps=2)
    assert "ctx" in bundle
    assert "hist" in bundle
    assert "step0full" in bundle
    assert "step1meta" in bundle


def test_inactive_steps_return_meta_only(tmp_path):
    m = mm(tmp_path)
    m.compress_step(3, 0, "meta only")
    assert m.read_step(3, full=False) == "meta only"
    assert m.read_step(3, full=True) == ""  # no full.md written


def test_append_agent_history_accumulates(tmp_path):
    m = mm(tmp_path)
    m.append_agent_history("agent", "first")
    m.append_agent_history("agent", "second")
    content = (tmp_path / "agents" / "agent" / "history.md").read_text()
    assert "first" in content
    assert "second" in content
