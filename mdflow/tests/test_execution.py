"""Tests for real execution engine with LLM and tools."""
import pytest
import tempfile
from typing import Any, List, Optional

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import BaseMessage, AIMessage, ToolCall
from langchain_core.callbacks import CallbackManagerForLLMRun
from langchain_core.outputs import ChatGeneration, ChatResult

from core.real_compiler import RealWorkflowCompiler, GraphState
from core.memory import MemoryManager
from core.tools import create_default_registry
from core.models import WorkflowConfig, WorkflowNode, WorkflowEdge, AgentConfig


class FakeToolLLM(BaseChatModel):
    """Fake LLM that can return tool calls."""

    def __init__(self, responses: List[AIMessage], **kwargs):
        super().__init__(**kwargs)
        object.__setattr__(self, '_responses', responses)
        object.__setattr__(self, '_call_count', 0)

    @property
    def _llm_type(self) -> str:
        return "fake-tool"

    def bind_tools(self, tools, **kwargs):
        """Bind tools (no-op for fake LLM)."""
        return self

    def _generate(self, messages: List[BaseMessage], stop: Optional[List[str]] = None,
                  run_manager: Optional[CallbackManagerForLLMRun] = None, **kwargs: Any) -> ChatResult:
        """Return pre-configured responses."""
        response = self._responses[self._call_count]
        object.__setattr__(self, '_call_count', self._call_count + 1)
        return ChatResult(generations=[ChatGeneration(message=response)])


class TestRealExecution:
    """Test real execution with LLM and tools."""

    def test_execution_with_tool_calls(self):
        """Test agent executes tools and extracts routing flag."""
        with tempfile.TemporaryDirectory() as tmpdir:
            memory = MemoryManager(tmpdir)
            tool_registry = create_default_registry()

            # Fake LLM with tool call then final response
            responses = [
                AIMessage(
                    content="Running tests",
                    tool_calls=[{
                        "name": "mock_test_runner",
                        "args": {"test_suite": "unit_tests"},
                        "id": "call_1"
                    }]
                ),
                AIMessage(content="Tests passed! <ROUTING_FLAG>passed</ROUTING_FLAG>")
            ]
            fake_llm = FakeToolLLM(responses=responses)

            agent = AgentConfig(
                name="tester",
                model="gpt-4",
                system_prompt="You are a test runner.",
                tools=["mock_test_runner"]
            )

            workflow = WorkflowConfig(
                workflow_name="test_workflow",
                entry_point="test",
                end_point="test",
                nodes=[WorkflowNode(name="test", agent_name="tester")],
                edges=[]
            )

            compiler = RealWorkflowCompiler(memory, fake_llm, tool_registry)
            graph = compiler.compile(workflow, {"tester": agent})

            result = graph.invoke(GraphState(messages=[], routing_flag="", current_agent=""))

            # Verify routing flag extracted
            assert result["routing_flag"] == "passed"
            
            # Verify tool was called
            tool_msgs = [m for m in result["messages"] if hasattr(m, 'type') and m.type == "tool"]
            assert len(tool_msgs) == 1
            assert "passed" in tool_msgs[0].content

    def test_routing_flag_extraction(self):
        """Test routing flag extraction without tools."""
        with tempfile.TemporaryDirectory() as tmpdir:
            memory = MemoryManager(tmpdir)
            tool_registry = create_default_registry()

            responses = [
                AIMessage(content="Check failed <ROUTING_FLAG>failed</ROUTING_FLAG>")
            ]
            fake_llm = FakeToolLLM(responses=responses)

            agent = AgentConfig(
                name="checker",
                model="gpt-4",
                system_prompt="You check things.",
                tools=[]
            )

            workflow = WorkflowConfig(
                workflow_name="check_workflow",
                entry_point="check",
                end_point="check",
                nodes=[WorkflowNode(name="check", agent_name="checker")],
                edges=[]
            )

            compiler = RealWorkflowCompiler(memory, fake_llm, tool_registry)
            graph = compiler.compile(workflow, {"checker": agent})

            result = graph.invoke(GraphState(messages=[], routing_flag="", current_agent=""))

            assert result["routing_flag"] == "failed"
            assert "failed" in result["messages"][-1].content
