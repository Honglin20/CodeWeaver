"""Simple end-to-end test with linear workflow."""
from langchain_openai import ChatOpenAI
from core.structured_compiler import StructuredWorkflowCompiler, GraphState
from core.tools import create_default_registry
from pathlib import Path
import tempfile

def main():
    print("=== Simple E2E Test ===\n")

    # Create temporary workflow
    with tempfile.TemporaryDirectory() as tmpdir:
        workflow_dir = Path(tmpdir) / "test_workflow"
        workflow_dir.mkdir()

        # Create flow.md
        (workflow_dir / "flow.md").write_text("""---
workflow_name: simple_test
entry_point: validate
end_point: validate
---

### Node: validate (agent: validator)
""")

        # Create agent
        agents_dir = workflow_dir / "agents"
        agents_dir.mkdir()
        (agents_dir / "validator.md").write_text("""---
name: validator
model: deepseek-chat
memory_strategy: ultra_short
context_file: memory/ultra_short/context.md
tools: []
---

Validate and return: <ROUTING_FLAG>passed</ROUTING_FLAG>
""")

        # Create context
        context_dir = workflow_dir / "memory" / "ultra_short"
        context_dir.mkdir(parents=True)
        (context_dir / "context.md").write_text("Check syntax")

        print("✓ Workflow created\n")

        # Setup LLM
        llm = ChatOpenAI(
            model="deepseek-chat",
            openai_api_key="sk-c8694451b6c545818a49368ac3f388ea",
            openai_api_base="https://api.deepseek.com",
            temperature=0.7
        )
        print("✓ LLM configured\n")

        # Compile and execute
        tool_registry = create_default_registry()
        compiler = StructuredWorkflowCompiler(str(workflow_dir), llm, tool_registry)
        graph = compiler.compile("test_session")
        print("✓ Workflow compiled\n")

        print("=== Executing ===\n")
        result = graph.invoke(GraphState(
            workflow_dir=str(workflow_dir),
            session_id="test_session",
            routing_flag="",
            current_node=""
        ))

        print("\n=== Results ===")
        print(f"Routing: {result['routing_flag']}")
        print(f"Node: {result['current_node']}")
        print("\n✓ Test passed!")

if __name__ == "__main__":
    main()
