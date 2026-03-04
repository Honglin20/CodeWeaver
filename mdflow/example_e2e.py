"""End-to-end example using real DeepSeek LLM."""
from langchain_openai import ChatOpenAI

from core.parser import parse_agent_file, parse_workflow_file
from core.memory import MemoryManager
from core.tools import create_default_registry
from core.real_compiler import RealWorkflowCompiler, GraphState


def main():
    print("=== MDFlow End-to-End Example ===\n")

    # Setup DeepSeek LLM
    llm = ChatOpenAI(
        model="deepseek-chat",
        openai_api_key="sk-c8694451b6c545818a49368ac3f388ea",
        openai_api_base="https://api.deepseek.com",
        temperature=0.7
    )
    print("✓ LLM configured (DeepSeek)\n")

    # Setup components
    memory = MemoryManager("./memory")
    tool_registry = create_default_registry()
    print("✓ Memory and tools initialized\n")

    # Parse workflow and agents
    workflow = parse_workflow_file("workflows/code_review.md")
    print(f"✓ Loaded workflow: {workflow.workflow_name}")
    print(f"  Nodes: {[n.name for n in workflow.nodes]}")
    print(f"  Edges: {len(workflow.edges)}\n")

    agents = {
        "code_reviewer": parse_agent_file("agents/code_reviewer.md"),
        "code_fixer": parse_agent_file("agents/code_fixer.md")
    }
    print(f"✓ Loaded {len(agents)} agents\n")

    # Compile workflow
    compiler = RealWorkflowCompiler(memory, llm, tool_registry)
    graph = compiler.compile(workflow, agents)
    print("✓ Workflow compiled\n")

    # Execute workflow
    print("=== Executing Workflow ===\n")

    from langchain_core.messages import HumanMessage

    initial_state = GraphState(
        messages=[
            HumanMessage(content="Please review the file 'example.py' using the mock_file_reader tool.")
        ],
        routing_flag="",
        current_agent=""
    )

    result = graph.invoke(initial_state)

    # Display results
    print("\n=== Results ===")
    print(f"Final routing: {result['routing_flag']}")
    print(f"Last agent: {result['current_agent']}")
    print(f"Total messages: {len(result['messages'])}\n")

    print("=== Conversation ===")
    for i, msg in enumerate(result['messages'], 1):
        msg_type = msg.__class__.__name__
        content = msg.content[:100] + "..." if len(msg.content) > 100 else msg.content
        print(f"{i}. [{msg_type}] {content}\n")


if __name__ == "__main__":
    main()
