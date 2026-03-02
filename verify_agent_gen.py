#!/usr/bin/env python3
"""Quick verification script for agent_gen.py"""

import sys
import tempfile
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

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

def test_parse():
    print("Testing _parse_llm_response...")
    result = _parse_llm_response(MOCK_LLM_RESPONSE)
    assert result["name"] == "validator-agent"
    assert result["tools"] == ["run_command", "read_file"]
    print("✓ Parse test passed")

def test_parse_no_fences():
    print("Testing _parse_llm_response without fences...")
    raw = "name: test-agent\ndescription: test\nsystem_prompt: you are a test\ntools:\n  - read_file\n"
    result = _parse_llm_response(raw)
    assert result["name"] == "test-agent"
    print("✓ Parse without fences test passed")

def test_generate():
    print("Testing generate_agent...")
    gap = StepAnalysis(
        step_index=5,
        step_title="Validate",
        goal="Verify optimization correctness",
        required_capability="output validation",
        matched_agent=None,
        gap=True,
    )

    llm = lambda msgs: MOCK_LLM_RESPONSE

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        agent = generate_agent(gap, llm, tmp_path)

        assert agent.name == "validator-agent"
        assert "validation" in agent.description.lower()
        assert "run_command" in agent.tools

        yaml_file = tmp_path / "validator-agent.yaml"
        assert yaml_file.exists()

        print("✓ Generate agent test passed")

if __name__ == "__main__":
    test_parse()
    test_parse_no_fences()
    test_generate()
    print("\n✓ All verification tests passed!")
