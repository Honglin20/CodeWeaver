from typing import Callable
from codeweaver.parser.agent import AgentDef
from codeweaver.memory.manager import MemoryManager

MAX_RETRIES = 3


def make_node(
    agent_def: AgentDef,
    memory: MemoryManager,
    total_steps: int,
    llm_fn: Callable | None = None,
    step_goal: str = "",
    step_raw_text: str = "",
) -> Callable:
    """Returns a LangGraph node function for the given agent."""

    def node(state: dict) -> dict:
        bundle = memory.load_agent_memory_bundle(
            agent_def.name, state["current_step"], total_steps
        )

        # Build structured context with step information
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

        messages = [
            {"role": "system", "content": agent_def.system_prompt},
            {"role": "user", "content": user_content},
        ]
        if llm_fn is not None:
            response = llm_fn(messages)
        else:
            import litellm
            resp = litellm.completion(
                model=agent_def.model or "gpt-4o", messages=messages
            )
            response = resp.choices[0].message.content
        memory.write_agent_context(agent_def.name, response)
        return {**state, "status": "running", "current_step": state["current_step"]}

    return node
