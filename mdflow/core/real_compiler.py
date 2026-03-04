"""Real execution compiler with LLM and tool support."""
import re
from typing import Annotated, TypedDict, Callable

from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langchain_core.messages import AnyMessage, AIMessage, SystemMessage, ToolMessage
from langchain_core.language_models import BaseChatModel

from .models import WorkflowConfig, AgentConfig
from .memory import MemoryManager
from .tools import ToolRegistry


class GraphState(TypedDict):
    """Global state for workflow execution."""
    messages: Annotated[list[AnyMessage], add_messages]
    routing_flag: str
    current_agent: str


class RealWorkflowCompiler:
    """Compiles workflows with real LLM and tool execution."""

    def __init__(self, memory_manager: MemoryManager, llm: BaseChatModel,
                 tool_registry: ToolRegistry):
        """Initialize compiler.

        Args:
            memory_manager: Memory manager instance
            llm: Language model for agent execution
            tool_registry: Tool registry for agent capabilities
        """
        self.memory_manager = memory_manager
        self.llm = llm
        self.tool_registry = tool_registry

    def _create_node_func(self, agent_config: AgentConfig) -> Callable:
        """Create node function with real LLM execution.

        Args:
            agent_config: Agent configuration

        Returns:
            Node function compatible with LangGraph
        """
        def node_func(state: GraphState) -> dict:
            print(f"[{agent_config.name}] Executing...")

            # Get tools for this agent
            tools = self.tool_registry.get_tools(agent_config.tools)

            # Bind tools to LLM
            if tools:
                llm_with_tools = self.llm.bind_tools(tools)
            else:
                llm_with_tools = self.llm

            # Add routing instruction to system prompt
            enhanced_prompt = agent_config.system_prompt + (
                "\n\nIMPORTANT: At the end of your response, output your routing decision "
                "using this exact format: <ROUTING_FLAG>flag_name</ROUTING_FLAG>"
            )

            # Construct messages
            messages = [SystemMessage(content=enhanced_prompt)] + state["messages"]

            # First LLM call
            response = llm_with_tools.invoke(messages)

            # Collect new messages to return
            new_messages = []

            # Handle tool calls
            if hasattr(response, 'tool_calls') and response.tool_calls:
                print(f"[{agent_config.name}] Executing {len(response.tool_calls)} tool(s)")

                # Add AI message with tool calls
                messages.append(response)
                new_messages.append(response)

                # Execute each tool
                for tool_call in response.tool_calls:
                    tool_name = tool_call['name']
                    tool_args = tool_call['args']

                    # Find and execute tool
                    for tool in tools:
                        if tool.name == tool_name:
                            result = tool.invoke(tool_args)
                            tool_msg = ToolMessage(
                                content=str(result),
                                tool_call_id=tool_call['id']
                            )
                            messages.append(tool_msg)
                            new_messages.append(tool_msg)
                            break

                # Second LLM call to observe tool results
                response = llm_with_tools.invoke(messages)

            # Add final response
            new_messages.append(response)

            # Extract routing flag
            routing_flag = _extract_routing_flag(response.content)

            # Memory operations
            if agent_config.memory_strategy == "medium_term":
                self.memory_manager.append_medium_term_log(
                    agent_config.name,
                    f"Executed with routing: {routing_flag}"
                )

            return {
                "messages": new_messages,
                "routing_flag": routing_flag,
                "current_agent": agent_config.name
            }

        return node_func

    def compile(self, workflow: WorkflowConfig, agents: dict[str, AgentConfig]):
        """Compile workflow into executable LangGraph.

        Args:
            workflow: Workflow configuration
            agents: Dictionary of agent configurations

        Returns:
            Compiled LangGraph
        """
        graph = StateGraph(GraphState)

        # Add nodes
        for node in workflow.nodes:
            agent_config = agents.get(node.agent_name)
            if not agent_config:
                raise ValueError(f"Agent '{node.agent_name}' not found")

            node_func = self._create_node_func(agent_config)
            graph.add_node(node.name, node_func)

        # Add edges - group by source for conditional edges
        from collections import defaultdict
        conditional_edges = defaultdict(dict)

        for edge in workflow.edges:
            if edge.condition is None or edge.condition == "default":
                graph.add_edge(edge.source, edge.target)
            else:
                # Collect conditional edges by source
                conditional_edges[edge.source][edge.condition] = edge.target

        # Add grouped conditional edges
        for source, condition_map in conditional_edges.items():
            def make_router(cond_map):
                def route_func(state: GraphState) -> str:
                    flag = state.get("routing_flag", "default")
                    return cond_map.get(flag, END)
                return route_func

            graph.add_conditional_edges(source, make_router(condition_map))

        # Set entry and exit
        graph.add_edge(START, workflow.entry_point)
        graph.add_edge(workflow.end_point, END)

        return graph.compile()


def _extract_routing_flag(content: str) -> str:
    """Extract routing flag from LLM response.

    Args:
        content: LLM response content

    Returns:
        Extracted flag or 'default'
    """
    match = re.search(r'<ROUTING_FLAG>(\w+)</ROUTING_FLAG>', content)
    if match:
        return match.group(1)
    return "default"
