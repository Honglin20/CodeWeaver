from dataclasses import dataclass, field
from pathlib import Path
import yaml


@dataclass
class AgentDef:
    name: str
    description: str
    system_prompt: str
    tools: list[str] = field(default_factory=list)
    memory_read: list[str] = field(default_factory=list)
    memory_write: list[str] = field(default_factory=list)
    model: str | None = None
    max_tokens: int = 4096


def load_agent(path: str | Path) -> AgentDef:
    data = yaml.safe_load(Path(path).read_text())
    for key in ("name", "description", "system_prompt"):
        if not data.get(key):
            raise ValueError(f"Agent YAML missing required field: '{key}'")
    memory = data.get("memory", {})
    return AgentDef(
        name=data["name"],
        description=data["description"],
        system_prompt=data["system_prompt"],
        tools=data.get("tools", []),
        memory_read=memory.get("read", []),
        memory_write=memory.get("write", []),
        model=data.get("model"),
        max_tokens=data.get("max_tokens", 4096),
    )


def load_agent_registry(directory: str | Path) -> dict[str, AgentDef]:
    """Load agents from directory, merging with built-in agents."""
    registry = {}

    # First load built-in agents
    builtin_dir = Path(__file__).parent.parent / "builtin_agents"
    if builtin_dir.exists():
        for path in builtin_dir.glob("*.yaml"):
            agent = load_agent(path)
            registry[agent.name] = agent

    # Then load project-specific agents (can override built-ins)
    project_dir = Path(directory)
    if project_dir.exists():
        for path in project_dir.glob("*.yaml"):
            agent = load_agent(path)
            registry[agent.name] = agent

    return registry
