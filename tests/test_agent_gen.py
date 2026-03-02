import yaml
from pathlib import Path
from codeweaver.generator.agent_gen import generate_agent, _parse_llm_response
from codeweaver.generator.analyzer import StepAnalysis

MOCK_LLM_RESPONSE = """
```yaml
name: validator-agent
description: Validates optimization results by comparing output against baseline
system_prompt: |
  You are a validation specialist. Run the entry command, compare output
  against baseline, and report whether the optimization goal was achieved.
tools:
  - run_command
  - read_file
```
"""

def make_gap():
    return StepAnalysis(
        step_index=5,
        step_title="Validate",
        goal="Verify optimization correctness",
        required_capability="output validation",
        matched_agent=None,
        gap=True,
    )

def test_generate_agent_returns_agentdef(tmp_path):
    llm = lambda msgs: MOCK_LLM_RESPONSE
    agent = generate_agent(make_gap(), llm, tmp_path)
    assert agent.name == "validator-agent"
    assert "validat" in agent.description.lower()  # "Validates" contains "validat"
    assert "run_command" in agent.tools

def test_generate_agent_writes_yaml(tmp_path):
    llm = lambda msgs: MOCK_LLM_RESPONSE
    generate_agent(make_gap(), llm, tmp_path)
    yaml_file = tmp_path / "validator-agent.yaml"
    assert yaml_file.exists()
    data = yaml.safe_load(yaml_file.read_text())
    assert data["name"] == "validator-agent"

def test_parse_llm_response_extracts_yaml():
    result = _parse_llm_response(MOCK_LLM_RESPONSE)
    assert result["name"] == "validator-agent"
    assert result["tools"] == ["run_command", "read_file"]

def test_parse_llm_response_handles_no_fences():
    """LLM sometimes returns YAML without code fences."""
    raw = "name: test-agent\ndescription: test\nsystem_prompt: you are a test\ntools:\n  - read_file\n"
    result = _parse_llm_response(raw)
    assert result["name"] == "test-agent"

def test_generated_yaml_has_required_fields(tmp_path):
    llm = lambda msgs: MOCK_LLM_RESPONSE
    generate_agent(make_gap(), llm, tmp_path)
    data = yaml.safe_load((tmp_path / "validator-agent.yaml").read_text())
    for field in ["name", "description", "system_prompt"]:
        assert field in data, f"Missing field: {field}"
