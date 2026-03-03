"""Context builder for agent execution."""

from codeweaver.parser.agent import AgentDef
from codeweaver.memory.manager import MemoryManager


class ContextBuilder:
    """Builds execution context for agents."""

    def build_messages(
        self,
        agent_def: AgentDef,
        memory: MemoryManager,
        state: dict,
        total_steps: int,
        step_goal: str = "",
        step_raw_text: str = ""
    ) -> list[dict]:
        """Build messages for LLM call."""
        bundle = memory.load_agent_memory_bundle(
            agent_def.name, state["current_step"], total_steps
        )

        context_parts = []
        if step_goal or step_raw_text:
            context_parts.append("# Current Step Context")
            if step_goal:
                context_parts.append(f"**Goal:** {step_goal}")
            if step_raw_text:
                context_parts.append(f"**Instructions:**\n{step_raw_text}")
            context_parts.append("")

        context_parts.append("# Memory Context")
        context_parts.append(bundle)

        if state.get("task_description"):
            context_parts.append(f"\n\nTask: {state['task_description']}")

        user_content = "\n".join(context_parts)

        return [
            {"role": "system", "content": agent_def.system_prompt},
            {"role": "user", "content": user_content},
        ]
