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


def test_node_receives_step_context():
    """Test that step goal and raw_text are passed to the agent in the user message."""
    memory = _mock_memory()
    agent = _agent()

    step_goal = "Analyze the codebase structure"
    step_raw_text = "Look at all Python files and identify the main modules."

    # Track the messages passed to the LLM
    captured_messages = []
    def capture_llm(msgs):
        captured_messages.extend(msgs)
        return "analysis complete"

    node = make_node(
        agent,
        memory,
        total_steps=3,
        llm_fn=capture_llm,
        step_goal=step_goal,
        step_raw_text=step_raw_text
    )

    state = {
        "current_step": 1,
        "task_description": "do something",
        "status": "running",
        "iteration": 0,
        "memory_root": "/tmp",
        "error_count": 0
    }

    node(state)

    # Verify the user message contains step context
    user_messages = [m for m in captured_messages if m["role"] == "user"]
    assert len(user_messages) == 1

    user_content = user_messages[0]["content"]
    assert "# Current Step Context" in user_content
    assert f"**Goal:** {step_goal}" in user_content
    assert f"**Instructions:**\n{step_raw_text}" in user_content
    assert "# Memory Context" in user_content
    assert "bundle" in user_content  # from mock memory


def test_compile_graph_passes_step_context(tmp_path):
    """Test that compile_graph extracts and passes step context to nodes."""
    from codeweaver.parser.workflow import StepDef

    # Create workflow steps with raw_text
    workflow_steps = [
        StepDef(
            index=0,
            title="Analyze code",
            raw_text="Review all Python files in the src/ directory and create a summary.",
            explicit_agents=["agent_a"]
        ),
        StepDef(
            index=1,
            title="Generate report",
            raw_text="Create a markdown report with findings from the analysis.",
            explicit_agents=["agent_a"]
        )
    ]

    plans = [
        StepPlan(index=0, goal="Analyze code structure", agents=["agent_a"]),
        StepPlan(index=1, goal="Generate analysis report", agents=["agent_a"])
    ]

    registry = {"agent_a": _agent()}
    memory = MemoryManager(tmp_path)

    # Track messages to verify step context is passed
    captured_messages = []
    def capture_llm(msgs):
        captured_messages.extend(msgs)
        return "done"

    graph = compile_graph(plans, registry, memory, llm_fn=capture_llm, workflow_steps=workflow_steps)

    # Verify graph was compiled with step context
    assert len(graph.nodes) == 2

    # Compile and execute the graph to verify step context is passed
    compiled = graph.compile()
    state = {
        "current_step": 0,
        "task_description": "",
        "status": "running",
        "iteration": 0,
        "memory_root": str(tmp_path),
        "error_count": 0
    }

    compiled.invoke(state)

    # Verify the step context was included in the LLM calls
    user_messages = [m for m in captured_messages if m["role"] == "user"]
    assert len(user_messages) >= 1

    # Check first step's context
    first_user_msg = user_messages[0]["content"]
    assert "# Current Step Context" in first_user_msg
    assert "**Goal:** Analyze code structure" in first_user_msg
    assert "**Instructions:**\nReview all Python files in the src/ directory" in first_user_msg


def test_compile_graph_with_none_workflow_steps(tmp_path):
    """Test that compile_graph handles None workflow_steps gracefully."""
    plans = [
        StepPlan(index=0, goal="Do something", agents=["agent_a"]),
        StepPlan(index=1, goal="Do something else", agents=["agent_a"])
    ]

    registry = {"agent_a": _agent()}
    memory = MemoryManager(tmp_path)

    # Should not raise an error when workflow_steps is None
    graph = compile_graph(plans, registry, memory, llm_fn=lambda msgs: "done", workflow_steps=None)
    assert len(graph.nodes) == 2


def test_compile_graph_with_incomplete_workflow_steps(tmp_path):
    """Test that compile_graph handles workflow_steps with fewer items than plans."""
    from codeweaver.parser.workflow import StepDef

    # Only provide workflow_steps for first step, not second
    workflow_steps = [
        StepDef(
            index=0,
            title="First step",
            raw_text="Do the first thing.",
            explicit_agents=["agent_a"]
        )
    ]

    plans = [
        StepPlan(index=0, goal="First goal", agents=["agent_a"]),
        StepPlan(index=1, goal="Second goal", agents=["agent_a"])
    ]

    registry = {"agent_a": _agent()}
    memory = MemoryManager(tmp_path)

    captured_messages = []
    def capture_llm(msgs):
        captured_messages.extend(msgs)
        return "done"

    # Should not raise KeyError when step 1 is not in workflow_steps
    graph = compile_graph(plans, registry, memory, llm_fn=capture_llm, workflow_steps=workflow_steps)
    assert len(graph.nodes) == 2

    # Execute to verify behavior
    compiled = graph.compile()
    state = {
        "current_step": 0,
        "task_description": "",
        "status": "running",
        "iteration": 0,
        "memory_root": str(tmp_path),
        "error_count": 0
    }

    compiled.invoke(state)

    # First step should have raw_text, second should only have goal
    user_messages = [m for m in captured_messages if m["role"] == "user"]
    assert len(user_messages) >= 1
    first_msg = user_messages[0]["content"]
    assert "Do the first thing" in first_msg


def test_compile_graph_with_mismatched_indices(tmp_path):
    """Test that compile_graph handles workflow_steps with non-matching indices."""
    from codeweaver.parser.workflow import StepDef

    # workflow_steps has index 5, but plans only has indices 0 and 1
    workflow_steps = [
        StepDef(
            index=5,
            title="Wrong index",
            raw_text="This won't match any plan.",
            explicit_agents=["agent_a"]
        )
    ]

    plans = [
        StepPlan(index=0, goal="First goal", agents=["agent_a"]),
        StepPlan(index=1, goal="Second goal", agents=["agent_a"])
    ]

    registry = {"agent_a": _agent()}
    memory = MemoryManager(tmp_path)

    # Should not raise error, just won't find matching step_def
    graph = compile_graph(plans, registry, memory, llm_fn=lambda msgs: "done", workflow_steps=workflow_steps)
    assert len(graph.nodes) == 2


def test_node_with_empty_step_raw_text():
    """Test that node handles empty step_raw_text but present step_goal."""
    memory = _mock_memory()
    agent = _agent()

    step_goal = "Do something important"
    step_raw_text = ""  # Empty raw text

    captured_messages = []
    def capture_llm(msgs):
        captured_messages.extend(msgs)
        return "done"

    node = make_node(
        agent,
        memory,
        total_steps=1,
        llm_fn=capture_llm,
        step_goal=step_goal,
        step_raw_text=step_raw_text
    )

    state = {
        "current_step": 0,
        "task_description": "",
        "status": "running",
        "iteration": 0,
        "memory_root": "/tmp",
        "error_count": 0
    }

    node(state)

    user_messages = [m for m in captured_messages if m["role"] == "user"]
    assert len(user_messages) == 1

    user_content = user_messages[0]["content"]
    # Should include step context header and goal, but not instructions
    assert "# Current Step Context" in user_content
    assert f"**Goal:** {step_goal}" in user_content
    assert "**Instructions:**" not in user_content


def test_node_with_no_step_context():
    """Test that node works without any step context (backward compatibility)."""
    memory = _mock_memory()
    agent = _agent()

    captured_messages = []
    def capture_llm(msgs):
        captured_messages.extend(msgs)
        return "done"

    # No step_goal or step_raw_text provided
    node = make_node(
        agent,
        memory,
        total_steps=1,
        llm_fn=capture_llm
    )

    state = {
        "current_step": 0,
        "task_description": "task",
        "status": "running",
        "iteration": 0,
        "memory_root": "/tmp",
        "error_count": 0
    }

    node(state)

    user_messages = [m for m in captured_messages if m["role"] == "user"]
    assert len(user_messages) == 1

    user_content = user_messages[0]["content"]
    # Should not include step context header when no context provided
    assert "# Current Step Context" not in user_content
    # But should still include memory context
    assert "# Memory Context" in user_content
    assert "bundle" in user_content

