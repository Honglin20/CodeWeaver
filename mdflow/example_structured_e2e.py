"""End-to-end example with structured memory and real DeepSeek LLM."""
from langchain_openai import ChatOpenAI

from core.structured_compiler import StructuredWorkflowCompiler, GraphState
from core.tools import create_default_registry


def main():
    print("=== Structured Memory E2E Example ===\n")

    # Setup DeepSeek LLM
    llm = ChatOpenAI(
        model="deepseek-chat",
        openai_api_key="sk-c8694451b6c545818a49368ac3f388ea",
        openai_api_base="https://api.deepseek.com",
        temperature=0.7
    )
    print("✓ LLM configured (DeepSeek)\n")

    # Setup
    workflow_dir = "workflows/code_optimization"
    tool_registry = create_default_registry()
    print("✓ Tools initialized\n")

    # Compile workflow
    compiler = StructuredWorkflowCompiler(workflow_dir, llm, tool_registry)
    session_id = "demo_session_001"
    graph = compiler.compile(session_id)
    print(f"✓ Workflow compiled (session: {session_id})\n")

    # Execute
    print("=== Executing Workflow ===\n")
    initial_state = GraphState(
        workflow_dir=workflow_dir,
        session_id=session_id,
        routing_flag="",
        current_node=""
    )

    result = graph.invoke(initial_state)

    # Display results
    print("\n=== Results ===")
    print(f"Final routing: {result['routing_flag']}")
    print(f"Last node: {result['current_node']}")
    print(f"Session: {result['session_id']}")


if __name__ == "__main__":
    main()
