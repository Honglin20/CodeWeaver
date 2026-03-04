"""Tests for workflow compiler."""
import pytest
import tempfile
from pathlib import Path

from core.compiler import WorkflowCompiler, GraphState
from core.memory import MemoryManager
from core.models import WorkflowConfig, WorkflowNode, WorkflowEdge, AgentConfig


class TestWorkflowCompiler:
    """Test workflow compilation and execution."""

    def test_simple_linear_workflow(self):
        """Test compiling and executing a simple linear workflow."""
        # Create temporary workspace
        with tempfile.TemporaryDirectory() as tmpdir:
            # Setup memory manager
            memory_manager = MemoryManager(tmpdir)

            # Create agent configs
            agents = {
                "planner": AgentConfig(
                    name="planner",
                    model="gpt-4",
                    system_prompt="You are a planning agent.",
                    memory_strategy="full"
                ),
                "executor": AgentConfig(
                    name="executor",
                    model="gpt-4",
                    system_prompt="You are an execution agent.",
                    memory_strategy="medium_term"
                )
            }

            # Create workflow config
            workflow = WorkflowConfig(
                workflow_name="simple_workflow",
                entry_point="plan",
                end_point="execute",
                nodes=[
                    WorkflowNode(name="plan", agent_name="planner"),
                    WorkflowNode(name="execute", agent_name="executor")
                ],
                edges=[
                    WorkflowEdge(source="plan", target="execute")
                ]
            )

            # Compile workflow
            compiler = WorkflowCompiler(memory_manager)
            compiled_graph = compiler.compile(workflow, agents)

            # Execute workflow
            initial_state = GraphState(
                messages=[],
                routing_flag="",
                current_agent=""
            )
            result = compiled_graph.invoke(initial_state)

            # Assertions
            assert len(result["messages"]) == 2
            assert "planner execution mock" in result["messages"][0].content
            assert "executor execution mock" in result["messages"][1].content
            assert result["current_agent"] == "executor"

            # Check memory log was created
            log_file = Path(tmpdir) / "executor_log.txt"
            assert log_file.exists()

    def test_conditional_workflow(self):
        """Test workflow with conditional edges."""
        with tempfile.TemporaryDirectory() as tmpdir:
            memory_manager = MemoryManager(tmpdir)

            agents = {
                "checker": AgentConfig(
                    name="checker",
                    model="gpt-4",
                    system_prompt="Check conditions."
                ),
                "handler_a": AgentConfig(
                    name="handler_a",
                    model="gpt-4",
                    system_prompt="Handle case A."
                )
            }

            workflow = WorkflowConfig(
                workflow_name="conditional_workflow",
                entry_point="check",
                end_point="handle",
                nodes=[
                    WorkflowNode(name="check", agent_name="checker"),
                    WorkflowNode(name="handle", agent_name="handler_a")
                ],
                edges=[
                    WorkflowEdge(source="check", target="handle", condition="pass")
                ]
            )

            compiler = WorkflowCompiler(memory_manager)
            mock_routing = {"check": "pass", "handle": "pass"}
            compiled_graph = compiler.compile(workflow, agents, mock_routing)

            initial_state = GraphState(messages=[], routing_flag="", current_agent="")
            result = compiled_graph.invoke(initial_state)

            assert len(result["messages"]) == 2
            assert result["routing_flag"] == "pass"

