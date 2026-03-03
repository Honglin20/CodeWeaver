from typing import TypedDict
from langgraph.graph import StateGraph, END
from codeweaver.engine.orchestrator import StepPlan
from codeweaver.engine.node_factory import make_node, MAX_RETRIES
from codeweaver.parser.agent import AgentDef
from codeweaver.parser.workflow import StepDef
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
    workflow_steps: list[StepDef] | None = None,
    project_root: str = ".",
) -> StateGraph:
    graph = StateGraph(WorkflowState)
    total_steps = len(plans)

    # Create a mapping from step index to StepDef for quick lookup
    step_map = {}
    if workflow_steps:
        step_map = {step.index: step for step in workflow_steps}

    for plan in plans:
        node_name = f"step_{plan.index}"
        if plan.agents and plan.agents[0] in agent_registry:
            agent_def = agent_registry[plan.agents[0]]

            # Extract step context from workflow_steps if available
            step_goal = plan.goal
            step_raw_text = ""
            step_def = step_map.get(plan.index)
            if step_def:
                step_raw_text = step_def.raw_text

            node_fn = make_node(
                agent_def,
                memory,
                total_steps,
                llm_fn,
                step_goal=step_goal,
                step_raw_text=step_raw_text,
                project_root=project_root
            )
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
