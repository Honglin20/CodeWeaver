from typing import Callable
from codeweaver.parser.agent import AgentDef
from codeweaver.memory.manager import MemoryManager

MAX_RETRIES = 3


def make_node(
    agent_def: AgentDef,
    memory: MemoryManager,
    total_steps: int,
    llm_fn: Callable | None = None,
) -> Callable:
    """Returns a LangGraph node function for the given agent."""

    def node(state: dict) -> dict:
        bundle = memory.load_agent_memory_bundle(
            agent_def.name, state["current_step"], total_steps
        )
        messages = [
            {"role": "system", "content": agent_def.system_prompt},
            {"role": "user", "content": bundle + "\n\nTask: " + state.get("task_description", "")},
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
