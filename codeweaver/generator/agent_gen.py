import yaml
import re
from pathlib import Path
from codeweaver.parser.agent import AgentDef
from codeweaver.generator.analyzer import StepAnalysis
from typing import Callable

AVAILABLE_TOOLS = ["run_command", "read_file", "list_files", "tool:select", "tool:debugger"]


def generate_agent(
    gap: StepAnalysis,
    llm_fn: Callable[[list[dict]], str],
    output_dir: Path,
) -> AgentDef:
    """
    Generate an AgentDef for a gap step, write YAML to output_dir/<name>.yaml.
    Returns the generated AgentDef.
    """
    # Build prompt for LLM
    messages = _build_generation_prompt(gap)

    # Call LLM
    response = llm_fn(messages)

    # Parse response
    parsed = _parse_llm_response(response)

    # Create AgentDef
    agent = AgentDef(
        name=parsed["name"],
        description=parsed["description"],
        system_prompt=parsed["system_prompt"],
        tools=parsed.get("tools", []),
    )

    # Write YAML to output_dir
    output_path = output_dir / f"{agent.name}.yaml"
    yaml_data = {
        "name": agent.name,
        "description": agent.description,
        "system_prompt": agent.system_prompt,
    }
    if agent.tools:
        yaml_data["tools"] = agent.tools

    with open(output_path, "w") as f:
        yaml.dump(yaml_data, f, default_flow_style=False, sort_keys=False)

    return agent


def _build_generation_prompt(gap: StepAnalysis) -> list[dict]:
    """Build the LLM messages for agent generation."""
    tools_list = "\n".join([f"  - {tool}" for tool in AVAILABLE_TOOLS])

    content = f"""Given this workflow step that needs an agent:

Step: {gap.step_title}
Goal: {gap.goal}
Required capability: {gap.required_capability}

Generate an agent definition with this structure:
1. Name (kebab-case, descriptive)
2. Description (one sentence)
3. System prompt (based on responsibilities)
4. Tools needed (from: {", ".join(AVAILABLE_TOOLS)})

Respond with YAML in this format:
```yaml
name: agent-name
description: One sentence description
system_prompt: |
  Detailed system prompt explaining the agent's role and responsibilities.
tools:
  - run_command
  - read_file
```
"""

    return [{"role": "user", "content": content}]


def _parse_llm_response(response: str) -> dict:
    """
    Parse LLM response into {name, description, system_prompt, tools}.
    LLM response format (YAML block):
    ```yaml
    name: validator-agent
    description: Validates optimization results
    system_prompt: |
      You are a validation specialist...
    tools:
      - run_command
      - read_file
    ```
    """
    # Try to extract YAML from code fences
    yaml_match = re.search(r"```(?:yaml)?\s*\n(.*?)\n```", response, re.DOTALL)

    if yaml_match:
        yaml_content = yaml_match.group(1)
    else:
        # No fences, assume entire response is YAML
        yaml_content = response.strip()

    # Parse YAML
    parsed = yaml.safe_load(yaml_content)

    return parsed
