"""Workflow compiler that converts configurations to LangGraph."""
from typing import Annotated, TypedDict, Callable
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langchain_core.messages import AnyMessage, AIMessage

from .models import WorkflowConfig, AgentConfig
from .memory import MemoryManager


class GraphState(TypedDict):
    """Global state for workflow execution."""
    messages: Annotated[list[AnyMessage], add_messages]
    routing_flag: str
    current_agent: str


class WorkflowCompiler:
    """Compiles workflow configurations into executable LangGraph."""

    def __init__(self, memory_manager: MemoryManager):
        """Initialize compiler.

        Args:
            memory_manager: Memory manager instance
        """
        self.memory_manager = memory_manager

    def _create_node_func(self, agent_config: AgentConfig,
                         mock_routing: str = "default") -> Callable:
        """Create node function for an agent.

        Args:
            agent_config: Agent configuration
            mock_routing: Mock routing flag for testing

        Returns:
            Node function compatible with LangGraph
        """
        def node_func(state: GraphState) -> dict:
            print(f"[{agent_config.name}] Executing with system_prompt: "
                  f"{agent_config.system_prompt[:50]}...")

            # Mock memory operations
            if agent_config.memory_strategy == "medium_term":
                self.memory_manager.append_medium_term_log(
                    agent_config.name,
                    f"Executed at step with routing: {mock_routing}"
                )

            # Create mock response
            mock_message = AIMessage(content=f"{agent_config.name} execution mock")

            return {
                "messages": [mock_message],
                "routing_flag": mock_routing,
                "current_agent": agent_config.name
            }

        return node_func

    def compile(self, workflow: WorkflowConfig, agents: dict[str, AgentConfig],
                mock_routing_map: dict[str, str] = None):
        """Compile workflow into executable LangGraph.

        Args:
            workflow: Workflow configuration
            agents: Dictionary of agent configurations
            mock_routing_map: Optional routing flags for testing

        Returns:
            Compiled LangGraph
        """
        if mock_routing_map is None:
            mock_routing_map = {}

        graph = StateGraph(GraphState)

        # Add nodes
        for node in workflow.nodes:
            agent_config = agents.get(node.agent_name)
            if not agent_config:
                raise ValueError(f"Agent '{node.agent_name}' not found")

            mock_routing = mock_routing_map.get(node.name, "default")
            node_func = self._create_node_func(agent_config, mock_routing)
            graph.add_node(node.name, node_func)

        # Add edges
        for edge in workflow.edges:
            if edge.condition is None or edge.condition == "default":
                graph.add_edge(edge.source, edge.target)
            else:
                # Conditional edge
                def route_func(state: GraphState, target=edge.target,
                              condition=edge.condition) -> str:
                    if state.get("routing_flag") == condition:
                        return target
                    return END

                graph.add_conditional_edges(edge.source, route_func)

        # Set entry and exit
        graph.add_edge(START, workflow.entry_point)
        graph.add_edge(workflow.end_point, END)

        return graph.compile()

