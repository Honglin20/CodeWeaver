"""Tests for structured compiler integration."""
import pytest
import tempfile
from pathlib import Path

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import BaseMessage, AIMessage
from langchain_core.callbacks import CallbackManagerForLLMRun
from langchain_core.outputs import ChatGeneration, ChatResult
from typing import Any, List, Optional

from core.structured_compiler import StructuredWorkflowCompiler, GraphState
from core.tools import create_default_registry


class FakeLLM(BaseChatModel):
    """Fake LLM for testing."""

    def __init__(self, response_text: str, **kwargs):
        super().__init__(**kwargs)
        object.__setattr__(self, '_response_text', response_text)

    @property
    def _llm_type(self) -> str:
        return "fake"

    def bind_tools(self, tools, **kwargs):
        return self

    def _generate(self, messages: List[BaseMessage], stop: Optional[List[str]] = None,
                  run_manager: Optional[CallbackManagerForLLMRun] = None, **kwargs: Any) -> ChatResult:
        response = AIMessage(content=self._response_text)
        return ChatResult(generations=[ChatGeneration(message=response)])


class TestStructuredCompiler:
    """Test structured compiler with memory integration."""

    def test_ultra_short_memory_workflow(self):
        """Test workflow with ultra-short memory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            workflow_dir = Path(tmpdir) / "workflow"
            workflow_dir.mkdir()

            # Create flow.md
            (workflow_dir / "flow.md").write_text("""---
workflow_name: test
entry_point: validate
end_point: validate
---

### Node: validate (agent: validator)
""")

            # Create agent
            agents_dir = workflow_dir / "agents"
            agents_dir.mkdir()
            (agents_dir / "validator.md").write_text("""---
name: validator
model: gpt-4
memory_strategy: ultra_short
context_file: memory/ultra_short/context.md
tools: []
---

Validate code
""")

            # Create context
            context_dir = workflow_dir / "memory" / "ultra_short"
            context_dir.mkdir(parents=True)
            (context_dir / "context.md").write_text("Rules: check syntax")

            # Compile and execute
            fake_llm = FakeLLM("Validation passed <ROUTING_FLAG>passed</ROUTING_FLAG>")
            tool_registry = create_default_registry()
            
            compiler = StructuredWorkflowCompiler(str(workflow_dir), fake_llm, tool_registry)
            graph = compiler.compile("session_test")
            
            result = graph.invoke(GraphState(
                workflow_dir=str(workflow_dir),
                session_id="session_test",
                routing_flag="",
                current_node=""
            ))
            
            assert result["routing_flag"] == "passed"
            assert result["current_node"] == "validator"
