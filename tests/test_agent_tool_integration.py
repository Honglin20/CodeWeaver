"""
Tests for agent-tool integration.

This module tests the integration between agents and tool execution,
ensuring that agents can call tools via LLM function calling and
receive results back.
"""
import json
import pytest
from pathlib import Path
from unittest.mock import MagicMock
from codeweaver.engine.node_factory import make_node
from codeweaver.parser.agent import AgentDef
from codeweaver.memory.manager import MemoryManager


def _agent_with_tools(name="test_agent", tools=None):
    """Create an agent definition with tools."""
    if tools is None:
        tools = ["run_command", "read_file"]
    return AgentDef(
        name=name,
        description="Test agent with tools",
        system_prompt="You are a helpful assistant with access to tools.",
        tools=tools
    )


def _mock_memory():
    """Create a mock memory manager."""
    m = MagicMock(spec=MemoryManager)
    m.load_agent_memory_bundle.return_value = "Previous context"
    return m


def test_agent_with_tools_receives_tool_schemas(tmp_path):
    """Test that agents with tools receive tool schemas in LLM call."""
    memory = _mock_memory()
    agent = _agent_with_tools(tools=["read_file"])

    captured_calls = []
    def capture_llm(messages, tools=None, **kwargs):
        captured_calls.append({"messages": messages, "tools": tools})
        return "Task completed"

    node = make_node(
        agent,
        memory,
        total_steps=1,
        llm_fn=capture_llm,
        project_root=str(tmp_path)
    )

    state = {
        "current_step": 0,
        "task_description": "Read a file",
        "status": "running",
        "iteration": 0,
        "memory_root": str(tmp_path),
        "error_count": 0
    }

    node(state)

    # Verify tool schemas were passed to LLM
    assert len(captured_calls) == 1
    assert captured_calls[0]["tools"] is not None
    assert len(captured_calls[0]["tools"]) > 0

    # Verify schema structure
    tool_schema = captured_calls[0]["tools"][0]
    assert tool_schema["type"] == "function"
    assert "function" in tool_schema
    assert "name" in tool_schema["function"]


def test_agent_executes_tool_when_llm_requests_it(tmp_path):
    """Test that agent executes tool when LLM requests it via function calling."""
    memory = _mock_memory()
    agent = _agent_with_tools(tools=["read_file"])

    # Create a test file
    test_file = tmp_path / "test.txt"
    test_file.write_text("Hello from file")

    call_count = [0]

    def mock_llm(messages, tools=None, **kwargs):
        call_count[0] += 1

        if call_count[0] == 1:
            # First call: LLM requests to use read_file tool
            return {
                "role": "assistant",
                "content": None,
                "tool_calls": [
                    {
                        "id": "call_123",
                        "type": "function",
                        "function": {
                            "name": "read_file",
                            "arguments": json.dumps({"path": "test.txt"})
                        }
                    }
                ]
            }
        else:
            # Second call: LLM uses tool result to complete task
            # Verify tool result is in messages
            tool_messages = [m for m in messages if m.get("role") == "tool"]
            assert len(tool_messages) == 1
            assert "Hello from file" in tool_messages[0]["content"]
            return "I read the file and it says: Hello from file"

    node = make_node(
        agent,
        memory,
        total_steps=1,
        llm_fn=mock_llm,
        project_root=str(tmp_path)
    )

    state = {
        "current_step": 0,
        "task_description": "Read test.txt",
        "status": "running",
        "iteration": 0,
        "memory_root": "/tmp",
        "error_count": 0
    }

    node(state)

    # Verify LLM was called twice (once for tool request, once after tool execution)
    assert call_count[0] == 2

    # Verify final response was written to memory
    memory.write_agent_context.assert_called_once()
    final_response = memory.write_agent_context.call_args[0][1]
    assert "Hello from file" in final_response


def test_agent_handles_multiple_tool_calls(tmp_path):
    """Test that agent can handle multiple tool calls in sequence."""
    memory = _mock_memory()
    agent = _agent_with_tools(tools=["read_file", "run_command"])

    call_count = [0]

    def mock_llm(messages, tools=None, **kwargs):
        call_count[0] += 1

        if call_count[0] == 1:
            # First call: request read_file
            return {
                "role": "assistant",
                "content": None,
                "tool_calls": [
                    {
                        "id": "call_1",
                        "type": "function",
                        "function": {
                            "name": "read_file",
                            "arguments": json.dumps({"path": "config.txt"})
                        }
                    }
                ]
            }
        elif call_count[0] == 2:
            # Second call: request run_command
            return {
                "role": "assistant",
                "content": None,
                "tool_calls": [
                    {
                        "id": "call_2",
                        "type": "function",
                        "function": {
                            "name": "run_command",
                            "arguments": json.dumps({"cmd": "echo test", "cwd": "."})
                        }
                    }
                ]
            }
        else:
            # Third call: complete with results
            return "All tasks completed successfully"

    node = make_node(
        agent,
        memory,
        total_steps=1,
        llm_fn=mock_llm,
        project_root=str(tmp_path)
    )

    state = {
        "current_step": 0,
        "task_description": "Execute multiple tools",
        "status": "running",
        "iteration": 0,
        "memory_root": str(tmp_path),
        "error_count": 0
    }

    node(state)

    # Should have made 3 LLM calls
    assert call_count[0] == 3


def test_agent_respects_max_tool_iterations(tmp_path):
    """Test that agent stops after MAX_TOOL_ITERATIONS to prevent infinite loops."""
    memory = _mock_memory()
    agent = _agent_with_tools(tools=["read_file"])

    call_count = [0]

    def mock_llm(messages, tools=None, **kwargs):
        call_count[0] += 1
        # Always request a tool call (infinite loop scenario)
        return {
            "role": "assistant",
            "content": None,
            "tool_calls": [
                {
                    "id": f"call_{call_count[0]}",
                    "type": "function",
                    "function": {
                        "name": "read_file",
                        "arguments": json.dumps({"path": "test.txt"})
                    }
                }
            ]
        }

    node = make_node(
        agent,
        memory,
        total_steps=1,
        llm_fn=mock_llm,
        project_root=str(tmp_path)
    )

    state = {
        "current_step": 0,
        "task_description": "Test max iterations",
        "status": "running",
        "iteration": 0,
        "memory_root": str(tmp_path),
        "error_count": 0
    }

    node(state)

    # Should stop at MAX_TOOL_ITERATIONS (5)
    assert call_count[0] == 5


def test_agent_without_tools_works_normally(tmp_path):
    """Test that agents without tools continue to work as before."""
    memory = _mock_memory()
    agent = AgentDef(
        name="simple_agent",
        description="Agent without tools",
        system_prompt="You are helpful.",
        tools=[]  # No tools
    )

    captured_calls = []
    def capture_llm(messages, tools=None, **kwargs):
        captured_calls.append({"messages": messages, "tools": tools})
        return "Task completed"

    node = make_node(
        agent,
        memory,
        total_steps=1,
        llm_fn=capture_llm,
        project_root=str(tmp_path)
    )

    state = {
        "current_step": 0,
        "task_description": "Simple task",
        "status": "running",
        "iteration": 0,
        "memory_root": str(tmp_path),
        "error_count": 0
    }

    node(state)

    # Should make exactly one LLM call with no tools
    assert len(captured_calls) == 1
    assert captured_calls[0]["tools"] is None or len(captured_calls[0]["tools"]) == 0


def test_agent_handles_tool_execution_errors(tmp_path):
    """Test that agent handles tool execution errors gracefully."""
    memory = _mock_memory()
    agent = _agent_with_tools(tools=["read_file"])

    call_count = [0]

    def mock_llm(messages, tools=None, **kwargs):
        call_count[0] += 1

        if call_count[0] == 1:
            # Request to read non-existent file
            return {
                "role": "assistant",
                "content": None,
                "tool_calls": [
                    {
                        "id": "call_1",
                        "type": "function",
                        "function": {
                            "name": "read_file",
                            "arguments": json.dumps({"path": "nonexistent.txt"})
                        }
                    }
                ]
            }
        else:
            # LLM should receive error message and handle it
            tool_messages = [m for m in messages if m.get("role") == "tool"]
            assert len(tool_messages) == 1
            # Error should be in the tool message
            assert "error" in tool_messages[0]["content"].lower() or "not found" in tool_messages[0]["content"].lower()
            return "I couldn't read the file because it doesn't exist"

    node = make_node(
        agent,
        memory,
        total_steps=1,
        llm_fn=mock_llm,
        project_root=str(tmp_path)
    )

    state = {
        "current_step": 0,
        "task_description": "Read non-existent file",
        "status": "running",
        "iteration": 0,
        "memory_root": str(tmp_path),
        "error_count": 0
    }

    node(state)

    # Should complete despite tool error
    assert call_count[0] == 2


def test_agent_with_string_response_from_llm(tmp_path):
    """Test backward compatibility when LLM returns string instead of dict."""
    memory = _mock_memory()
    agent = _agent_with_tools(tools=["read_file"])

    def mock_llm(messages, tools=None, **kwargs):
        # Return simple string (no tool calls)
        return "Task completed without tools"

    node = make_node(
        agent,
        memory,
        total_steps=1,
        llm_fn=mock_llm,
        project_root=str(tmp_path)
    )

    state = {
        "current_step": 0,
        "task_description": "Simple task",
        "status": "running",
        "iteration": 0,
        "memory_root": str(tmp_path),
        "error_count": 0
    }

    result = node(state)

    # Should work normally
    assert result["status"] == "running"
    memory.write_agent_context.assert_called_once_with("test_agent", "Task completed without tools")


def test_agent_validates_tool_authorization(tmp_path):
    """Test that agent rejects unauthorized tool calls."""
    memory = _mock_memory()
    # Agent only has read_file, not run_command
    agent = _agent_with_tools(tools=["read_file"])

    call_count = [0]

    def mock_llm(messages, tools=None, **kwargs):
        call_count[0] += 1

        if call_count[0] == 1:
            # Try to call unauthorized tool
            return {
                "role": "assistant",
                "content": None,
                "tool_calls": [
                    {
                        "id": "call_1",
                        "type": "function",
                        "function": {
                            "name": "run_command",  # Not in allowed tools
                            "arguments": json.dumps({"cmd": "echo test", "cwd": "."})
                        }
                    }
                ]
            }
        else:
            # LLM should receive error about unauthorized tool
            tool_messages = [m for m in messages if m.get("role") == "tool"]
            assert len(tool_messages) == 1
            assert "not in the allowed tools list" in tool_messages[0]["content"]
            return "I cannot execute that command"

    node = make_node(
        agent,
        memory,
        total_steps=1,
        llm_fn=mock_llm,
        project_root=str(tmp_path)
    )

    state = {
        "current_step": 0,
        "task_description": "Test tool authorization",
        "status": "running",
        "iteration": 0,
        "memory_root": str(tmp_path),
        "error_count": 0
    }

    node(state)

    # Should complete with error message
    assert call_count[0] == 2


def test_agent_handles_non_serializable_tool_results(tmp_path):
    """Test that agent handles non-JSON-serializable tool results."""
    memory = _mock_memory()
    agent = _agent_with_tools(tools=["read_file"])

    # Create a test file
    test_file = tmp_path / "test.txt"
    test_file.write_text("test content")

    call_count = [0]

    def mock_llm(messages, tools=None, **kwargs):
        call_count[0] += 1

        if call_count[0] == 1:
            return {
                "role": "assistant",
                "content": None,
                "tool_calls": [
                    {
                        "id": "call_1",
                        "type": "function",
                        "function": {
                            "name": "read_file",
                            "arguments": json.dumps({"path": "test.txt"})
                        }
                    }
                ]
            }
        else:
            # Should receive tool result even if it had serialization issues
            tool_messages = [m for m in messages if m.get("role") == "tool"]
            assert len(tool_messages) == 1
            # Content should be valid JSON
            content = json.loads(tool_messages[0]["content"])
            assert "success" in content
            return "Task completed"

    node = make_node(
        agent,
        memory,
        total_steps=1,
        llm_fn=mock_llm,
        project_root=str(tmp_path)
    )

    state = {
        "current_step": 0,
        "task_description": "Test serialization",
        "status": "running",
        "iteration": 0,
        "memory_root": str(tmp_path),
        "error_count": 0
    }

    node(state)

    assert call_count[0] == 2

