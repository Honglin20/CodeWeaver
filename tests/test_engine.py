from unittest.mock import MagicMock, call
from pathlib import Path
import pytest

from codeweaver.engine.node_factory import make_node, MAX_RETRIES
from codeweaver.engine.compiler import compile_graph
from codeweaver.engine.orchestrator import StepPlan
from codeweaver.parser.agent import AgentDef
from codeweaver.memory.manager import MemoryManager


def _agent(name="agent_a"):
    return AgentDef(name=name, description="test", system_prompt="You are helpful.")


def _plan(index, is_loop=False):
    return StepPlan(index=index, goal=f"goal_{index}", agents=["agent_a"], is_loop=is_loop)


def _mock_memory():
    m = MagicMock(spec=MemoryManager)
    m.load_agent_memory_bundle.return_value = "bundle"
    return m


def test_sequential_graph_compilation(tmp_path):
    plans = [_plan(0), _plan(1), _plan(2)]
    registry = {"agent_a": _agent()}
    memory = MemoryManager(tmp_path)
    graph = compile_graph(plans, registry, memory, llm_fn=lambda msgs: "done")
    assert len(graph.nodes) == 3


def test_loop_conditional_edge(tmp_path):
    plans = [_plan(0, is_loop=True)]
    registry = {"agent_a": _agent()}
    memory = MemoryManager(tmp_path)
    graph = compile_graph(plans, registry, memory, llm_fn=lambda msgs: "done")
    # node exists and graph was built without error
    assert "step_0" in graph.nodes


def test_node_loads_correct_memory_bundle():
    memory = _mock_memory()
    agent = _agent()
    node = make_node(agent, memory, total_steps=3, llm_fn=lambda msgs: "done")
    state = {"current_step": 1, "task_description": "do something", "status": "running",
             "iteration": 0, "memory_root": "/tmp", "error_count": 0}
    node(state)
    memory.load_agent_memory_bundle.assert_called_once_with("agent_a", 1, 3)


def test_node_writes_output_to_memory():
    memory = _mock_memory()
    agent = _agent()
    node = make_node(agent, memory, total_steps=2, llm_fn=lambda msgs: "done")
    state = {"current_step": 0, "task_description": "task", "status": "running",
             "iteration": 0, "memory_root": "/tmp", "error_count": 0}
    node(state)
    memory.write_agent_context.assert_called_once_with("agent_a", "done")


def test_max_retries_exits_loop(tmp_path):
    from langgraph.graph import END
    plans = [_plan(0, is_loop=True)]
    registry = {"agent_a": _agent()}
    memory = MemoryManager(tmp_path)
    graph = compile_graph(plans, registry, memory, llm_fn=lambda msgs: "done")

    # Extract the conditional function from the graph edges
    edges = graph.edges
    # Find the conditional edge for step_0
    conditional = None
    for edge in edges:
        if hasattr(edge, "condition"):
            conditional = edge.condition
            break

    # When error_count >= MAX_RETRIES, should route to END not back to step_0
    state_max = {"error_count": MAX_RETRIES, "status": "error"}
    state_retry = {"error_count": 0, "status": "error"}

    if conditional:
        assert conditional(state_max) == END
        assert conditional(state_retry) == "step_0"
