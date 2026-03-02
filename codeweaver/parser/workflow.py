from dataclasses import dataclass, field
import re
import frontmatter


@dataclass
class StepDef:
    index: int
    title: str
    raw_text: str
    explicit_agents: list[str] = field(default_factory=list)
    explicit_tools: list[str] = field(default_factory=list)
    parallel: bool = False
    sub_steps: list["StepDef"] = field(default_factory=list)


@dataclass
class WorkflowDef:
    name: str
    description: str
    entry_command: str | None
    steps: list[StepDef]


def _extract_agents(text: str) -> list[str]:
    return [m.group(1) for m in re.finditer(r'@([\w-]+):', text) if not m.group(1).startswith("tool")]


def _extract_tools(text: str) -> list[str]:
    return [m.group(1) for m in re.finditer(r'@tool:([\w-]+):', text)]


def _parse_step(index: int, title: str, raw_text: str, parallel: bool = False) -> StepDef:
    return StepDef(
        index=index,
        title=title,
        raw_text=raw_text,
        explicit_agents=_extract_agents(raw_text),
        explicit_tools=_extract_tools(raw_text),
        parallel=parallel,
    )


def parse_workflow(md_text: str) -> WorkflowDef:
    post = frontmatter.loads(md_text)
    meta = post.metadata
    content = post.content

    steps: list[StepDef] = []
    current_step: StepDef | None = None
    current_sub_lines: list[str] = []
    current_sub_title: str = ""
    current_sub_index: int = 0

    def flush_sub():
        if current_step is not None and current_sub_title:
            sub = _parse_step(current_sub_index, current_sub_title, "\n".join(current_sub_lines))
            current_step.sub_steps.append(sub)

    step_lines: list[str] = []

    def flush_step():
        nonlocal current_step
        if current_step is not None:
            flush_sub()
            current_step.raw_text = "\n".join(step_lines)
            current_step.explicit_agents = _extract_agents(current_step.raw_text)
            current_step.explicit_tools = _extract_tools(current_step.raw_text)
            steps.append(current_step)

    in_sub = False

    for line in content.splitlines():
        h2 = re.match(r'^## Step (\d+)(\s*\(parallel\))?\s*:\s*(.+)', line)
        h3 = re.match(r'^### Step (\w+)\s*:\s*(.+)', line)

        if h2:
            flush_step()
            idx = int(h2.group(1))
            parallel = bool(h2.group(2))
            title = h2.group(3).strip()
            current_step = StepDef(index=idx, title=title, raw_text="", parallel=parallel)
            step_lines = []
            in_sub = False
            current_sub_lines = []
            current_sub_title = ""
        elif h3 and current_step is not None:
            flush_sub()
            current_sub_index = h3.group(1)
            current_sub_title = h3.group(2).strip()
            current_sub_lines = []
            in_sub = True
        elif current_step is not None:
            if in_sub:
                current_sub_lines.append(line)
            step_lines.append(line)

    flush_step()

    return WorkflowDef(
        name=meta.get("name", ""),
        description=meta.get("description", ""),
        entry_command=meta.get("entry_command"),
        steps=steps,
    )
