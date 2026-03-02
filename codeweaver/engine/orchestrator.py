from dataclasses import dataclass, field
from typing import Callable
from codeweaver.parser.workflow import WorkflowDef, StepDef
from codeweaver.parser.agent import AgentDef
from codeweaver.memory.manager import MemoryManager

_LOOP_KEYWORDS = {"validate", "verify", "check", "retry", "fix"}


@dataclass
class StepPlan:
    index: int
    goal: str
    agents: list[str] = field(default_factory=list)
    tools: list[str] = field(default_factory=list)
    parallel: bool = False
    depends_on: list[int] = field(default_factory=list)
    is_loop: bool = False
    loop_exit_condition: str | None = None


class Orchestrator:
    def __init__(
        self,
        registry: dict[str, AgentDef],
        memory: MemoryManager,
        llm_fn: Callable[[list[dict]], str],
    ):
        self.registry = registry
        self.memory = memory
        self.llm_fn = llm_fn

    def _goal(self, step: StepDef) -> str:
        if step.raw_text and step.raw_text.strip() != step.title:
            return self.llm_fn([
                {"role": "user", "content": (
                    f"Summarize this step in one sentence.\n"
                    f"Title: {step.title}\n"
                    f"Details: {step.raw_text}"
                )}
            ])
        return step.title

    def _agents(self, step: StepDef, goal: str) -> list[str]:
        if step.explicit_agents:
            return step.explicit_agents
        agent_list = "\n".join(
            f"- {name}: {a.description}" for name, a in self.registry.items()
        )
        response = self.llm_fn([
            {"role": "user", "content": (
                f"Step goal: {goal}\n\n"
                f"Available agents:\n{agent_list}\n\n"
                "Which agent(s) from the list should handle this step? "
                "Reply with agent names only, comma-separated."
            )}
        ])
        return [n.strip() for n in response.split(",") if n.strip() in self.registry]

    def _is_loop(self, step: StepDef) -> bool:
        text = (step.title + " " + step.raw_text).lower()
        if not any(kw in text for kw in _LOOP_KEYWORDS):
            return False
        response = self.llm_fn([
            {"role": "user", "content": (
                f"Step: {step.title}\n{step.raw_text}\n\n"
                "Does this step involve a loop/retry pattern? Reply yes or no."
            )}
        ])
        return response.strip().lower().startswith("yes")

    def analyze(self, workflow: WorkflowDef) -> list[StepPlan]:
        plans: list[StepPlan] = []
        for step in workflow.steps:
            goal = self._goal(step)
            agents = self._agents(step, goal)
            is_loop = self._is_loop(step)
            depends_on = [step.index - 1] if step.index > 0 else []
            plans.append(StepPlan(
                index=step.index,
                goal=goal,
                agents=agents,
                tools=list(step.explicit_tools),
                parallel=step.parallel,
                depends_on=depends_on,
                is_loop=is_loop,
            ))

        lines = ["# Workflow Analysis\n"]
        for p in plans:
            lines.append(f"## Step {p.index + 1}: {p.goal}")
            lines.append(f"- Goal: {p.goal}")
            lines.append(f"- Agents: {', '.join(p.agents) if p.agents else 'none'}")
            lines.append(f"- Tools: {', '.join(p.tools) if p.tools else 'none'}")
            lines.append(f"- Parallel: {'true' if p.parallel else 'false'}")
            lines.append(f"- Loop: {'true' if p.is_loop else 'false'}")
            lines.append("")

        self.memory.write_workflow_state("\n".join(lines))
        return plans
