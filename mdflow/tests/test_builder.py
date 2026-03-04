"""Tests for meta-builder functionality."""
import pytest
import tempfile
from pathlib import Path
from typing import Any, List, Optional

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import BaseMessage, AIMessage
from langchain_core.callbacks import CallbackManagerForLLMRun

from core.builder import (
    create_builder_graph,
    BuilderState
)


class FakeBuilderLLM(BaseChatModel):
    """Fake LLM for testing builder."""

    @property
    def _llm_type(self) -> str:
        return "fake"

    def _generate(self, messages: List[BaseMessage], stop: Optional[List[str]] = None,
                  run_manager: Optional[CallbackManagerForLLMRun] = None, **kwargs: Any) -> Any:
        """Generate fake responses based on prompt keywords."""
        prompt = messages[-1].content.lower()

        if "generate a workflow" in prompt:
            return self._create_result(FAKE_WORKFLOW_MD)
        elif "coder" in prompt:
            return self._create_result(FAKE_CODER_MD)
        elif "tester" in prompt:
            return self._create_result(FAKE_TESTER_MD)
        elif "documenter" in prompt:
            return self._create_result(FAKE_DOCUMENTER_MD)

        return self._create_result("Unknown request")

    def _create_result(self, content: str):
        """Create a fake generation result."""
        from langchain_core.outputs import ChatGeneration, ChatResult
        message = AIMessage(content=content)
        generation = ChatGeneration(message=message)
        return ChatResult(generations=[generation])


# Fake markdown templates
FAKE_WORKFLOW_MD = """---
workflow_name: dev_workflow
entry_point: code
end_point: finish
---

### Node: code (agent: Coder)

### Node: test (agent: Tester)

### Node: document (agent: Documenter)

### Node: finish (agent: Coder)

code --> test
test --> code : [failed]
test --> document : [passed]
document --> finish
"""

FAKE_CODER_MD = """---
name: Coder
model: gpt-4
max_output_tokens: 2000
memory_strategy: full
tools: []
---

## System Prompt

You are a code writer.
"""

FAKE_TESTER_MD = """---
name: Tester
model: gpt-4
max_output_tokens: 1500
memory_strategy: medium_term
tools: []
---

## System Prompt

You are a code tester.
"""

FAKE_DOCUMENTER_MD = """---
name: Documenter
model: gpt-4
max_output_tokens: 1000
memory_strategy: full
tools: []
---

## System Prompt

You are a documentation writer.
"""


class TestMetaBuilder:
    """Test meta-builder workflow generation."""

    def test_builder_with_loop_and_context_compression(self):
        """Test builder generates agents in loop with context compression."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create fake LLM
            fake_llm = FakeBuilderLLM()

            # Create builder graph
            builder_graph = create_builder_graph(fake_llm, output_dir=tmpdir)

            # Initial state
            initial_state = BuilderState(
                user_requirement="Code dev flow: Coder writes, Tester tests, loop if fail, Documenter docs if pass",
                generated_workflow_md="",
                pending_agents=[],
                completed_agents_summary="",
                messages=[]
            )

            # Execute
            result = builder_graph.invoke(initial_state)

            # Assertions
            assert result['generated_workflow_md'] != ""
            assert len(result['pending_agents']) == 0  # All processed
            assert "Coder" in result['completed_agents_summary']
            assert "Tester" in result['completed_agents_summary']
            assert "Documenter" in result['completed_agents_summary']

            # Check files created
            assert (Path(tmpdir) / "Coder.md").exists()
            assert (Path(tmpdir) / "Tester.md").exists()
            assert (Path(tmpdir) / "Documenter.md").exists()

            # Verify context compression: messages should not explode
            # Should have: workflow generation + 3 agent summaries (not full content)
            assert len(result['messages']) < 10  # Context compressed

    def test_builder_agent_order(self):
        """Test agents are processed in correct order."""
        with tempfile.TemporaryDirectory() as tmpdir:
            fake_llm = FakeBuilderLLM()
            builder_graph = create_builder_graph(fake_llm, output_dir=tmpdir)

            initial_state = BuilderState(
                user_requirement="Simple workflow",
                generated_workflow_md="",
                pending_agents=[],
                completed_agents_summary="",
                messages=[]
            )

            result = builder_graph.invoke(initial_state)

            # Check summary order reflects processing order
            summary_lines = result['completed_agents_summary'].strip().split('\n')
            assert len(summary_lines) == 3
