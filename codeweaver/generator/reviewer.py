from pathlib import Path
from rich.console import Console
from rich.syntax import Syntax
from codeweaver.parser.agent import AgentDef
from typing import Callable
import yaml

console = Console()

def review_agents(
    agents: list[AgentDef],
    agents_dir: Path,
    prompt_fn: Callable[[str, list[str]], str] | None = None,
) -> list[AgentDef]:
    """
    For each agent: display YAML, ask user to accept/skip.
    Accepted agents are written to agents_dir/<name>.yaml.
    Returns list of accepted AgentDefs.
    """
    if prompt_fn is None:
        import questionary
        prompt_fn = lambda q, choices: questionary.select(q, choices=choices).ask()

    agents_dir.mkdir(parents=True, exist_ok=True)
    accepted = []

    for agent in agents:
        # Convert AgentDef to YAML
        agent_dict = {
            "name": agent.name,
            "description": agent.description,
            "system_prompt": agent.system_prompt,
        }
        if agent.tools:
            agent_dict["tools"] = agent.tools
        if agent.memory_read or agent.memory_write:
            agent_dict["memory"] = {}
            if agent.memory_read:
                agent_dict["memory"]["read"] = agent.memory_read
            if agent.memory_write:
                agent_dict["memory"]["write"] = agent.memory_write
        if agent.model:
            agent_dict["model"] = agent.model
        if agent.max_tokens != 4096:
            agent_dict["max_tokens"] = agent.max_tokens

        yaml_content = yaml.dump(agent_dict, sort_keys=False, default_flow_style=False)

        # Display YAML with syntax highlighting
        console.print(f"\n[bold]Agent: {agent.name}[/bold]")
        syntax = Syntax(yaml_content, "yaml", theme="monokai", line_numbers=False)
        console.print(syntax)

        # Ask user
        choice = prompt_fn(f"Accept {agent.name}?", ["accept", "skip"])

        if choice == "accept":
            # Write to file
            yaml_path = agents_dir / f"{agent.name}.yaml"
            yaml_path.write_text(yaml_content)
            accepted.append(agent)

    return accepted
