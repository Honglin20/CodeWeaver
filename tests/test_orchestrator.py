import pytest
from pathlib import Path
from codeweaver.parser.workflow import WorkflowDef, StepDef
from codeweaver.parser.agent import AgentDef
from codeweaver.memory.manager import MemoryManager
from codeweaver.engine.orchestrator import Orchestrator, StepPlan


def make_registry():
    return {
        "structure-agent": AgentDef(
            name="structure-agent",
            description="Analyzes project structure",
            system_prompt="You analyze structure.",
        )
    }


def make_orchestrator(tmp_path, llm_fn):
    return Orchestrator(
        registry=make_registry(),
        memory=MemoryManager(tmp_path),
        llm_fn=llm_fn,
    )


def make_workflow(steps):
    return WorkflowDef(name="test", description="", entry_command=None, steps=steps)


def test_explicit_agent_respected(tmp_path):
    calls = []
    def llm_fn(msgs):
        calls.append(msgs)
        return "some goal summary"

    step = StepDef(index=0, title="Analyze", raw_text="Analyze structure", explicit_agents=["structure-agent"])
    orc = make_orchestrator(tmp_path, llm_fn)
    plans = orc.analyze(make_workflow([step]))

    assert plans[0].agents == ["structure-agent"]
    # llm may be called for goal but NOT for agent selection
    for call in calls:
        content = call[0]["content"]
        assert "Which agent" not in content


def test_llm_infers_agent_from_description(tmp_path):
    def llm_fn(msgs):
        content = msgs[0]["content"]
        if "Which agent" in content:
            return "structure-agent"
        return "Analyze the project structure."

    step = StepDef(index=0, title="Analyze", raw_text="Analyze structure", explicit_agents=[])
    orc = make_orchestrator(tmp_path, llm_fn)
    plans = orc.analyze(make_workflow([step]))

    assert plans[0].agents == ["structure-agent"]


def test_loop_detection(tmp_path):
    def llm_fn(msgs):
        content = msgs[0]["content"]
        if "loop/retry" in content:
            return "yes"
        return "Validate the results."

    step = StepDef(index=0, title="Validate Results", raw_text="Check outputs", explicit_agents=["structure-agent"])
    orc = make_orchestrator(tmp_path, llm_fn)
    plans = orc.analyze(make_workflow([step]))

    assert plans[0].is_loop is True


def test_parallel_step_detection(tmp_path):
    llm_fn = lambda msgs: "structure-agent"
    step = StepDef(index=0, title="Run", raw_text="Run tasks", parallel=True, explicit_agents=["structure-agent"])
    orc = make_orchestrator(tmp_path, llm_fn)
    plans = orc.analyze(make_workflow([step]))

    assert plans[0].parallel is True


def test_dependency_graph_construction(tmp_path):
    llm_fn = lambda msgs: "structure-agent"
    steps = [
        StepDef(index=0, title="Step A", raw_text="A", explicit_agents=["structure-agent"]),
        StepDef(index=1, title="Step B", raw_text="B", explicit_agents=["structure-agent"]),
        StepDef(index=2, title="Step C", raw_text="C", explicit_agents=["structure-agent"]),
    ]
    orc = make_orchestrator(tmp_path, llm_fn)
    plans = orc.analyze(make_workflow(steps))

    assert plans[0].depends_on == []
    assert plans[1].depends_on == [0]
    assert plans[2].depends_on == [1]


def test_analysis_written_to_memory(tmp_path):
    llm_fn = lambda msgs: "structure-agent"
    step = StepDef(index=0, title="Analyze", raw_text="Analyze structure", explicit_agents=["structure-agent"])
    orc = make_orchestrator(tmp_path, llm_fn)
    orc.analyze(make_workflow([step]))

    workflow_file = tmp_path / "workflow.md"
    assert workflow_file.exists()
    content = workflow_file.read_text()
    assert "# Workflow Analysis" in content
    assert "structure-agent" in content
