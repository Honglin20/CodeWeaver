from dataclasses import dataclass, field
from pathlib import Path
import yaml
from codeweaver.engine.tool_inference import infer_agent_tools


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
    """Load and validate agent definition from YAML file."""
    try:
        data = yaml.safe_load(Path(path).read_text())
    except yaml.YAMLError as e:
        raise ValueError(f"Invalid YAML in {path}: {e}")
    except FileNotFoundError:
        raise ValueError(f"Agent file not found: {path}")

    # Validate required fields
    required_fields = ["name", "description", "system_prompt"]
    missing_fields = [field for field in required_fields if not data.get(field)]
    if missing_fields:
        raise ValueError(
            f"Agent YAML {path} missing required fields: {', '.join(missing_fields)}\n"
            f"Required fields: name, description, system_prompt"
        )

    # Validate field types
    if not isinstance(data["name"], str) or not data["name"].strip():
        raise ValueError(f"Agent YAML {path}: 'name' must be a non-empty string")

    if not isinstance(data["description"], str) or not data["description"].strip():
        raise ValueError(f"Agent YAML {path}: 'description' must be a non-empty string")

    if not isinstance(data["system_prompt"], str) or not data["system_prompt"].strip():
        raise ValueError(f"Agent YAML {path}: 'system_prompt' must be a non-empty string")

    # Validate optional fields
    if "tools" in data and not isinstance(data["tools"], list):
        raise ValueError(f"Agent YAML {path}: 'tools' must be a list")

    if "model" in data and not isinstance(data["model"], str):
        raise ValueError(f"Agent YAML {path}: 'model' must be a string")

    if "max_tokens" in data and not isinstance(data["max_tokens"], int):
        raise ValueError(f"Agent YAML {path}: 'max_tokens' must be an integer")

    memory = data.get("memory", {})
    if not isinstance(memory, dict):
        raise ValueError(f"Agent YAML {path}: 'memory' must be a dictionary")

    # Get explicit tools or infer them
    explicit_tools = data.get("tools", [])
    if not explicit_tools:
        # Infer tools from description and system prompt
        inferred_tools = infer_agent_tools(
            description=data["description"],
            system_prompt=data["system_prompt"]
        )
        tools = inferred_tools
    else:
        tools = explicit_tools

    return AgentDef(
        name=data["name"],
        description=data["description"],
        system_prompt=data["system_prompt"],
        tools=tools,
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
