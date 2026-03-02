# codeweaver/generator/analyzer.py
from dataclasses import dataclass
from codeweaver.parser.workflow import WorkflowDef, StepDef
from codeweaver.parser.agent import AgentDef
from typing import Callable

@dataclass
class StepAnalysis:
    step_index: int
    step_title: str
    goal: str
    required_capability: str
    matched_agent: str | None
    gap: bool

@dataclass
class AnalysisTree:
    workflow_name: str
    workflow_description: str
    steps: list[StepAnalysis]

    @property
    def gaps(self) -> list[StepAnalysis]:
        return [s for s in self.steps if s.gap]

    def to_markdown(self) -> str:
        """Generate tree-structured markdown for workflow_analysis.md"""
        lines = [
            f"# Workflow Analysis: {self.workflow_name}",
            "",
            "## Meta",
            f"- Name: {self.workflow_name}",
            f"- Description: {self.workflow_description}",
            f"- Total steps: {len(self.steps)}",
            f"- Gaps found: {len(self.gaps)}",
            "",
            "## Step Tree",
            ""
        ]

        for step in self.steps:
            lines.append(f"### Step {step.step_index}: {step.step_title}")
            lines.append(f"- Goal: {step.goal}")
            lines.append(f"- Required capability: {step.required_capability}")

            if step.matched_agent:
                lines.append(f"- Matched agent: {step.matched_agent} ✓")
            else:
                lines.append(f"- Matched agent: MISSING ✗")
                lines.append(f"- Gap: needs agent with capability \"{step.required_capability}\"")

            lines.append("")

        return "\n".join(lines)

class WorkflowAnalyzer:
    def __init__(self, registry: dict[str, AgentDef], llm_fn: Callable[[list[dict]], str]):
        self.registry = registry
        self.llm_fn = llm_fn

    def analyze(self, workflow: WorkflowDef) -> AnalysisTree:
        """Analyze workflow and identify gaps."""
        steps = []

        for step in workflow.steps:
            # Extract goal
            goal = self._extract_goal(step)

            # Extract required capability
            capability = self._extract_capability(step, goal)

            # Match agent
            if step.explicit_agents:
                # Use explicit agent directly
                matched_agent = step.explicit_agents[0]
                gap = False
            else:
                # Try to match from registry
                matched_agent = self._match_agent(capability)
                gap = matched_agent is None

            analysis = StepAnalysis(
                step_index=step.index,
                step_title=step.title,
                goal=goal,
                required_capability=capability,
                matched_agent=matched_agent,
                gap=gap
            )
            steps.append(analysis)

        return AnalysisTree(
            workflow_name=workflow.name,
            workflow_description=workflow.description,
            steps=steps
        )

    def _extract_goal(self, step: StepDef) -> str:
        """Extract one-sentence goal from step using LLM."""
        messages = [
            {
                "role": "user",
                "content": f"Extract a one sentence goal for this workflow step:\nTitle: {step.title}\nText: {step.raw_text}\n\nRespond with just the goal sentence."
            }
        ]
        return self.llm_fn(messages)

    def _extract_capability(self, step: StepDef, goal: str) -> str:
        """Extract required capability from step using LLM."""
        messages = [
            {
                "role": "user",
                "content": f"What capability is required for this step?\nGoal: {goal}\nStep: {step.raw_text}\n\nRespond with a short capability description."
            }
        ]
        return self.llm_fn(messages)

    def _match_agent(self, capability: str) -> str | None:
        """Match capability to existing agent in registry using LLM."""
        if not self.registry:
            return None

        agent_list = "\n".join([
            f"- {name}: {agent.description}"
            for name, agent in self.registry.items()
        ])

        messages = [
            {
                "role": "user",
                "content": f"Which agent best matches this capability: {capability}\n\nAvailable agents:\n{agent_list}\n\nRespond with the agent name or NONE if no match."
            }
        ]

        response = self.llm_fn(messages)

        if response == "NONE" or response not in self.registry:
            return None

        return response
