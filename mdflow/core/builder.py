"""Meta-builder for automatic workflow and agent generation."""
from typing import Annotated, TypedDict, Literal
from pathlib import Path
import re

from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages, RemoveMessage
from langchain_core.messages import AnyMessage, SystemMessage, HumanMessage, AIMessage
from langchain_core.language_models import BaseChatModel

from .parser import parse_workflow_file
from .models import WorkflowConfig


class BuilderState(TypedDict):
    """State for meta-builder workflow."""
    user_requirement: str
    generated_workflow_md: str
    pending_agents: list[str]
    completed_agents_summary: str
    messages: Annotated[list[AnyMessage], add_messages]


def node_draft_workflow(state: BuilderState, llm: BaseChatModel) -> dict:
    """Generate workflow markdown from user requirements."""
    print("[node_draft_workflow] Generating workflow...")

    prompt = f"""Generate a workflow markdown file based on this requirement:
{state['user_requirement']}

Output YAML frontmatter with workflow_name, entry_point, end_point, then define nodes and edges.
Format:
---
workflow_name: name
entry_point: start
end_point: end
---

### Node: node_name (agent: agent_name)

node1 --> node2
"""

    messages = [HumanMessage(content=prompt)]
    response = llm.invoke(messages)
    workflow_md = response.content

    # Parse to extract agent names
    agent_pattern = r'### Node: \w+ \(agent: (\w+)\)'
    agents = list(set(re.findall(agent_pattern, workflow_md)))

    print(f"[node_draft_workflow] Found agents: {agents}")

    return {
        "generated_workflow_md": workflow_md,
        "pending_agents": agents,
        "messages": [AIMessage(content=f"Generated workflow with {len(agents)} agents")]
    }



def node_draft_agent(state: BuilderState, llm: BaseChatModel, output_dir: str = "agents") -> dict:
    """Generate agent markdown for the next pending agent."""
    if not state['pending_agents']:
        return {}

    agent_name = state['pending_agents'][0]
    print(f"[node_draft_agent] Generating agent: {agent_name}")

    prompt = f"""Generate agent configuration for: {agent_name}

Context:
- Workflow: {state['generated_workflow_md'][:200]}...
- Previously generated: {state['completed_agents_summary']}

Output YAML frontmatter with name, model, max_output_tokens, memory_strategy, tools, then system prompt.
Format:
---
name: {agent_name}
model: gpt-4
max_output_tokens: 2000
memory_strategy: full
tools: []
---

## System Prompt

You are {agent_name}...
"""

    messages = [HumanMessage(content=prompt)]
    response = llm.invoke(messages)
    agent_md = response.content

    # Write to disk
    Path(output_dir).mkdir(exist_ok=True)
    agent_file = Path(output_dir) / f"{agent_name}.md"
    agent_file.write_text(agent_md, encoding='utf-8')
    print(f"[node_draft_agent] Wrote {agent_file}")

    return {
        "messages": [AIMessage(content=f"Generated {agent_name}", id=f"agent_{agent_name}")]
    }


def node_compress_context(state: BuilderState) -> dict:
    """Compress context by removing old messages and updating summary."""
    if not state['pending_agents']:
        return {}

    agent_name = state['pending_agents'][0]
    print(f"[node_compress_context] Compressing context for {agent_name}")

    # Update summary
    new_summary = state['completed_agents_summary'] + f"\n- Generated {agent_name}"

    # Remove the large agent generation message
    messages_to_remove = [
        RemoveMessage(id=f"agent_{agent_name}")
    ]

    # Remove completed agent from pending
    new_pending = state['pending_agents'][1:]

    return {
        "completed_agents_summary": new_summary,
        "pending_agents": new_pending,
        "messages": messages_to_remove
    }


def should_continue(state: BuilderState) -> Literal["draft_agent", "__end__"]:
    """Route based on pending agents."""
    if state['pending_agents']:
        return "draft_agent"
    return "__end__"


def create_builder_graph(llm: BaseChatModel, output_dir: str = "agents"):
    """Create the meta-builder graph.
    
    Args:
        llm: Language model for generation
        output_dir: Directory to write agent files
        
    Returns:
        Compiled builder graph
    """
    graph = StateGraph(BuilderState)
    
    # Add nodes with llm bound
    graph.add_node("draft_workflow", lambda state: node_draft_workflow(state, llm))
    graph.add_node("draft_agent", lambda state: node_draft_agent(state, llm, output_dir))
    graph.add_node("compress_context", node_compress_context)
    
    # Add edges
    graph.add_edge(START, "draft_workflow")
    graph.add_edge("draft_workflow", "draft_agent")
    graph.add_edge("draft_agent", "compress_context")
    graph.add_conditional_edges("compress_context", should_continue)
    
    return graph.compile()
