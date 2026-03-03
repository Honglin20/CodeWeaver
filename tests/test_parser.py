import pytest
from pathlib import Path
from codeweaver.parser.workflow import parse_workflow

FIXTURE = Path(__file__).parent / "fixtures" / "optimizer.md"


@pytest.fixture
def wf():
    return parse_workflow(FIXTURE.read_text())


def test_frontmatter_metadata(wf):
    assert wf.name == "optimizer"
    assert wf.description == "Optimize a Python algorithm for performance"
    assert wf.entry_command == "python src/main.py"


def test_explicit_agent_extraction(wf):
    assert wf.steps[0].explicit_agents == ["structure-agent"]
    assert wf.steps[3].explicit_agents == ["runner-agent"]


def test_tool_extraction(wf):
    step2 = wf.steps[1]
    assert "select" in step2.explicit_tools


def test_parallel_step_detection(wf):
    assert wf.steps[1].parallel is True
    assert wf.steps[0].parallel is False


def test_nested_substeps(wf):
    step2 = wf.steps[1]
    assert len(step2.sub_steps) == 2
    assert step2.sub_steps[0].title == "List Files"
    assert step2.sub_steps[1].title == "Analyze Dependencies"


def test_natural_language_step_no_agent(wf):
    step3 = wf.steps[2]
    assert step3.explicit_agents == []
    assert step3.explicit_tools == []


# --- Task 2: Agent Definition Loader ---
from pathlib import Path
from codeweaver.parser.agent import load_agent, load_agent_registry

FIXTURES_AGENTS = Path(__file__).parent / "fixtures" / "agents"

def test_load_agent_yaml():
    agent = load_agent(FIXTURES_AGENTS / "structure-agent.yaml")
    assert agent.name == "structure-agent"
    assert agent.model == "gpt-4o"
    assert "read_file" in agent.tools
    assert "code_db/index.md" in agent.memory_read

def test_missing_optional_fields_use_defaults():
    agent = load_agent(FIXTURES_AGENTS / "minimal-agent.yaml")
    assert agent.model is None
    # Tools are now inferred automatically if not specified
    assert isinstance(agent.tools, list)
    assert agent.max_tokens == 4096

def test_invalid_yaml_raises_error(tmp_path):
    bad = tmp_path / "bad.yaml"
    bad.write_text("name: x\ndescription: y\n")  # missing system_prompt
    import pytest
    with pytest.raises(ValueError):
        load_agent(bad)

def test_load_all_agents_from_directory():
    registry = load_agent_registry(FIXTURES_AGENTS)
    assert "structure-agent" in registry
    assert "minimal-agent" in registry
