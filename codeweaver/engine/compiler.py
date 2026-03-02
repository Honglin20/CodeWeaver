from typing import TypedDict
from langgraph.graph import StateGraph, END
from codeweaver.engine.orchestrator import StepPlan
from codeweaver.engine.node_factory import make_node, MAX_RETRIES
from codeweaver.parser.agent import AgentDef
from codeweaver.memory.manager import MemoryManager


class WorkflowState(TypedDict):
    current_step: int
    iteration: int
    status: str
    memory_root: str
    error_count: int
    task_description: str


def compile_graph(
    plans: list[StepPlan],
    agent_registry: dict[str, AgentDef],
    memory: MemoryManager,
    llm_fn=None,
) -> StateGraph:
    graph = StateGraph(WorkflowState)
    total_steps = len(plans)

    for plan in plans:
        node_name = f"step_{plan.index}"
        if plan.agents and plan.agents[0] in agent_registry:
            agent_def = agent_registry[plan.agents[0]]
            node_fn = make_node(agent_def, memory, total_steps, llm_fn)
        else:
            def node_fn(state: dict) -> dict:
                return state
        graph.add_node(node_name, node_fn)

    if plans:
        # Set entry point to first step's actual index
        graph.set_entry_point(f"step_{plans[0].index}")

    for i, plan in enumerate(plans):
        node_name = f"step_{plan.index}"
        is_last = i == len(plans) - 1
        next_node = f"step_{plans[i + 1].index}" if not is_last else END

        if plan.is_loop:
            def make_condition(loop_node, nxt):
                def condition(state: dict) -> str:
                    if state["error_count"] < MAX_RETRIES and state["status"] == "error":
                        return loop_node
                    return nxt
                return condition
            graph.add_conditional_edges(
                node_name,
                make_condition(node_name, next_node),
                {node_name: node_name, next_node: next_node},
            )
        else:
            graph.add_edge(node_name, next_node)

    return graph
