"""Tests for structured memory manager."""
import pytest
import tempfile
from pathlib import Path
import json

from core.structured_memory import MemoryManager


class TestMemoryManager:
    """Test structured memory manager."""

    def test_ultra_short_memory(self):
        """Test ultra-short context retrieval."""
        with tempfile.TemporaryDirectory() as tmpdir:
            workflow_dir = Path(tmpdir) / "workflow"
            workflow_dir.mkdir()

            # Create agent with context_file
            agents_dir = workflow_dir / "agents"
            agents_dir.mkdir()

            agent_file = agents_dir / "validator.md"
            agent_file.write_text("""---
name: validator
model: gpt-4
context_file: memory/ultra_short/context.md
---

## System Prompt
Test prompt
""")

            # Create context file
            context_dir = workflow_dir / "memory" / "ultra_short"
            context_dir.mkdir(parents=True)
            context_file = context_dir / "context.md"
            context_file.write_text("Validation rules here")

            # Test retrieval
            memory = MemoryManager(str(workflow_dir), "session_1")
            context = memory.get_ultra_short_context("validator")

            assert context == "Validation rules here"

    def test_short_term_memory(self):
        """Test short-term memory with sliding window."""
        with tempfile.TemporaryDirectory() as tmpdir:
            memory = MemoryManager(tmpdir, "session_1")

            # Append entries
            for i in range(15):
                memory.append_short_term({"step": i, "summary": f"Step {i}"})

            # Should only keep last 10
            entries = memory.get_short_term(max_entries=10)
            assert len(entries) == 10
            assert entries[0]["step"] == 5
            assert entries[-1]["step"] == 14

    def test_short_term_session_isolation(self):
        """Test that different sessions have separate files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            mem1 = MemoryManager(tmpdir, "session_1")
            mem2 = MemoryManager(tmpdir, "session_2")

            mem1.append_short_term({"data": "session1"})
            mem2.append_short_term({"data": "session2"})

            entries1 = mem1.get_short_term()
            entries2 = mem2.get_short_term()

            assert len(entries1) == 1
            assert len(entries2) == 1
            assert entries1[0]["data"] == "session1"
            assert entries2[0]["data"] == "session2"

    def test_medium_term_memory(self):
        """Test medium-term task logs."""
        with tempfile.TemporaryDirectory() as tmpdir:
            memory = MemoryManager(tmpdir, "session_1")

            memory.append_medium_term("Task 1 completed")
            memory.append_medium_term("Task 2 completed")

            recent = memory.get_medium_term_recent(n=2)
            assert len(recent) == 2
            assert recent[0]["summary"] == "Task 1 completed"
            assert recent[1]["summary"] == "Task 2 completed"

    def test_long_term_memory_search(self):
        """Test long-term memory search."""
        with tempfile.TemporaryDirectory() as tmpdir:
            memory = MemoryManager(tmpdir, "session_1")

            # Create meta file
            meta_dir = Path(tmpdir) / "memory" / "long_term"
            meta_dir.mkdir(parents=True)
            meta_file = meta_dir / "system_meta.md"
            meta_file.write_text("""# System Knowledge

- [arch_001] System architecture overview
- [api_002] API design patterns
""")

            results = memory.search_long_term("architecture")
            assert len(results) == 1
            assert results[0]["id"] == "arch_001"
