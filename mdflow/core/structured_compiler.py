"""Structured workflow compiler with MemoryManager integration."""
from typing import Annotated, TypedDict, Callable
from pathlib import Path

from langgraph.graph import StateGraph, START, END
from langchain_core.messages import SystemMessage
from langchain_core.language_models import BaseChatModel
from langchain_core.tools import tool

from .models import AgentConfig
from .structured_memory import MemoryManager
from .tools import ToolRegistry
from .parser import parse_workflow_file
import frontmatter
import re
import json


class GraphState(TypedDict):
    """Simplified state with memory paths."""
    workflow_dir: str
    session_id: str
    routing_flag: str
    current_node: str


class StructuredWorkflowCompiler:
    """Compiler using structured memory."""

    def __init__(self, workflow_dir: str, llm: BaseChatModel,
                 tool_registry: ToolRegistry):
        self.workflow_dir = Path(workflow_dir)
        self.llm = llm
        self.tool_registry = tool_registry

    def _create_node_func(self, agent_config: AgentConfig, 
                         memory: MemoryManager) -> Callable:
        """Create node function with memory integration."""
        def node_func(state: GraphState) -> dict:
            agent_name = agent_config.name
            
            # Build context based on memory strategy
            context_parts = []
            
            if agent_config.memory_strategy == "ultra_short":
                context = memory.get_ultra_short_context(agent_name)
                if context:
                    context_parts.append(f"## Context\n{context}")
            
            elif agent_config.memory_strategy == "short_term":
                entries = memory.get_short_term(max_entries=10)
                if entries:
                    context_parts.append("## Recent History")
                    for entry in entries:
                        context_parts.append(f"- {entry.get('summary', '')}")
            
            elif agent_config.memory_strategy == "medium_term":
                tasks = memory.get_medium_term_recent(n=5)
                if tasks:
                    context_parts.append("## Recent Tasks")
                    for task in tasks:
                        context_parts.append(f"- {task.get('summary', '')}")
            
            # Get tools
            tools = self.tool_registry.get_tools(agent_config.tools)
            
            # Add long-term search tool if needed
            if "search_long_term" in agent_config.tools:
                @tool
                def search_long_term_memory(query: str) -> str:
                    """Search long-term memory."""
                    results = memory.search_long_term(query)
                    return json.dumps(results, ensure_ascii=False)
                
                tools.append(search_long_term_memory)
            
            # Build prompt
            full_context = "\n\n".join(context_parts)
            prompt = f"{agent_config.system_prompt}\n\n{full_context}\n\n输出路由：<ROUTING_FLAG>flag</ROUTING_FLAG>"
            
            # Call LLM
            llm_with_tools = self.llm.bind_tools(tools) if tools else self.llm
            response = llm_with_tools.invoke([SystemMessage(content=prompt)])
            
            # Extract routing flag
            match = re.search(r'<ROUTING_FLAG>(\w+)</ROUTING_FLAG>', response.content)
            routing_flag = match.group(1) if match else "default"
            
            # Write to memory based on strategy
            if agent_config.memory_strategy == "short_term":
                memory.append_short_term({
                    "node": agent_name,
                    "summary": response.content[:100]
                })
            elif agent_config.memory_strategy == "medium_term":
                memory.append_medium_term(f"{agent_name}: {response.content[:100]}")
            
            return {
                "routing_flag": routing_flag,
                "current_node": agent_name
            }
        
        return node_func

    def compile(self, session_id: str):
        """Compile workflow with structured memory."""
        # Parse flow.md
        flow_file = self.workflow_dir / "flow.md"
        workflow = parse_workflow_file(str(flow_file))
        
        # Create memory manager
        memory = MemoryManager(str(self.workflow_dir), session_id)
        
        # Load agents
        agents = {}
        agents_dir = self.workflow_dir / "agents"
        for agent_file in agents_dir.glob("*.md"):
            post = frontmatter.load(agent_file)
            agent_config = AgentConfig(
                name=post.metadata['name'],
                model=post.metadata['model'],
                max_output_tokens=post.metadata.get('max_output_tokens', 2000),
                memory_strategy=post.metadata.get('memory_strategy', 'full'),
                tools=post.metadata.get('tools', []),
                system_prompt=post.content
            )
            agents[agent_config.name] = agent_config
        
        # Build graph
        graph = StateGraph(GraphState)
        
        # Add nodes
        for node in workflow.nodes:
            agent_config = agents.get(node.agent_name)
            if not agent_config:
                raise ValueError(f"Agent '{node.agent_name}' not found")
            
            node_func = self._create_node_func(agent_config, memory)
            graph.add_node(node.name, node_func)
        
        # Add edges (grouped by source)
        from collections import defaultdict
        conditional_edges = defaultdict(dict)
        
        for edge in workflow.edges:
            if edge.condition is None or edge.condition == "default":
                graph.add_edge(edge.source, edge.target)
            else:
                conditional_edges[edge.source][edge.condition] = edge.target
        
        # Add conditional edges
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
