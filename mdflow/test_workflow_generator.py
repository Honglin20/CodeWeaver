"""Test workflow generator with real DeepSeek LLM."""
from langchain_openai import ChatOpenAI
from core.structured_compiler import StructuredWorkflowCompiler, GraphState
from core.tools import create_default_registry
from pathlib import Path
import tempfile
import shutil

def test_workflow_generation():
    print("=== Workflow Generator E2E Test ===\n")

    # Setup LLM
    llm = ChatOpenAI(
        model="deepseek-chat",
        openai_api_key="sk-c8694451b6c545818a49368ac3f388ea",
        openai_api_base="https://api.deepseek.com",
        temperature=0.7
    )

    # Create output directory
    output_dir = Path("test_output/generated_workflow")
    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True)

    # Prepare user intent in memory
    memory_dir = Path("workflows/workflow_generator/memory")
    memory_dir.mkdir(parents=True, exist_ok=True)

    user_intent = """我想要一个代码审查流程：
1. 先验证代码质量（运行测试）
2. 如果通过则进行人工审查
3. 审查通过后生成报告
4. 如果验证失败则直接结束
"""

    (memory_dir / "user_intent.md").write_text(user_intent, encoding='utf-8')
    print(f"✓ User intent saved\n")

    # Compile and execute generator workflow
    tool_registry = create_default_registry()
    compiler = StructuredWorkflowCompiler("workflows/workflow_generator", llm, tool_registry)
    graph = compiler.compile("gen_session_001")

    print("=== Executing Generator ===\n")
    result = graph.invoke(GraphState(
        workflow_dir="workflows/workflow_generator",
        session_id="gen_session_001",
        routing_flag="",
        current_node=""
    ))

    print(f"\n=== Generator Result ===")
    print(f"Final node: {result['current_node']}")
    print(f"Routing: {result['routing_flag']}")

    # Check generated files
    print(f"\n=== Checking Generated Files ===")
