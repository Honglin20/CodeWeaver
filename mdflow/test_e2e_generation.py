"""End-to-end test for workflow generation with mock LLM."""
from pathlib import Path
import shutil
from core.structured_compiler import StructuredWorkflowCompiler, GraphState
from core.tools import create_default_registry
from core.parser import WorkflowParser


class MockLLM:
    """Mock LLM for testing without API calls."""

    def __init__(self):
        self.call_count = 0

    def invoke(self, messages, **kwargs):
        """Mock LLM response based on agent context."""
        self.call_count += 1

        # Extract agent context from messages
        content = str(messages)

        # Intent parser response
        if "intent_parser" in content or "解析用户的 workflow 意图" in content:
            return type('obj', (object,), {
                'content': """# Workflow Intent Analysis

## Workflow Name
code_review_workflow

## Nodes
- **validate_code**: Run code quality checks
  - memory: ultra_short
  - tools: mock_test_runner
- **review_report**: Generate review report
  - memory: short_term
  - tools: write_file
- **done**: Complete workflow
  - memory: ultra_short
  - tools: []

## Flow
validate_code --> review_report : [passed]
validate_code --> done : [failed]
review_report --> done

<ROUTING_FLAG>parsed</ROUTING_FLAG>
"""
            })()

        # Skeleton builder response
        elif "skeleton_builder" in content or "生成完整的 flow.md" in content:
            return type('obj', (object,), {
                'content': """---
workflow_name: code_review_workflow
entry_point: validate_code
end_point: done
---

# Code Review Workflow

## Nodes

### Node: validate_code (agent: validator)
Run code quality checks

### Node: review_report (agent: reporter)
Generate review report

### Node: done (agent: finisher)
Complete workflow

## Edges

validate_code --> review_report : [passed]
validate_code --> done : [failed]
review_report --> done

<ROUTING_FLAG>generated</ROUTING_FLAG>
"""
            })()

        # Agent builder response
        elif "agent_builder" in content or "生成 agent.md 配置" in content:
            return type('obj', (object,), {
                'content': """Generated agent configurations for all nodes.

<ROUTING_FLAG>completed</ROUTING_FLAG>
"""
            })()

        # Default response
        return type('obj', (object,), {
            'content': "<ROUTING_FLAG>success</ROUTING_FLAG>"
        })()

    def bind_tools(self, tools):
        """Mock tool binding."""
        return self


def test_workflow_generation_e2e():
    """Test complete workflow generation pipeline."""
    print("=== E2E Workflow Generation Test ===\n")

    # Setup
    output_dir = Path("test_output/e2e_generation")
    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True)

    # Prepare user intent
    memory_dir = Path("workflows/workflow_generator/memory")
    memory_dir.mkdir(parents=True, exist_ok=True)

    user_intent = """我想要一个代码审查流程：
1. 验证代码质量
2. 如果通过则生成审查报告
3. 如果失败则直接结束
"""

    (memory_dir / "user_intent.md").write_text(user_intent, encoding='utf-8')
    print(f"✓ User intent saved to {memory_dir / 'user_intent.md'}\n")

    # Create mock LLM and tool registry
    mock_llm = MockLLM()
    tool_registry = create_default_registry()

    # Compile workflow generator
    print("=== Compiling Workflow Generator ===")
    compiler = StructuredWorkflowCompiler(
        "workflows/workflow_generator",
        mock_llm,
        tool_registry
    )
    graph = compiler.compile("e2e_test_session")
    print("✓ Workflow generator compiled\n")

    # Execute generator
    print("=== Executing Generator ===")
    result = graph.invoke(GraphState(
        workflow_dir="workflows/workflow_generator",
        session_id="e2e_test_session",
        routing_flag="",
        current_node=""
    ))

    print(f"\n=== Execution Result ===")
    print(f"Final node: {result['current_node']}")
    print(f"Routing flag: {result['routing_flag']}")
    print(f"LLM calls made: {mock_llm.call_count}")

    # Verify generated files
    print(f"\n=== Verification ===")

    checks = {
        "Intent analysis exists": (memory_dir / "intent_analysis.md").exists(),
        "Flow.md generated": False,  # Would be in target workflow dir
        "Agents generated": False,   # Would be in target workflow dir
        "Generator completed": result['current_node'] == 'done'
    }

    for check, passed in checks.items():
        status = "✓" if passed else "✗"
        print(f"{status} {check}")

    all_passed = all(checks.values())
    print(f"\n{'✓ All checks passed!' if all_passed else '⚠ Some checks need manual verification'}")

    return all_passed


def test_generated_workflow_parseable():
    """Test that generated workflow can be parsed."""
    print("\n=== Testing Generated Workflow Parsing ===\n")

    # Create a sample generated workflow
    test_dir = Path("test_output/parseable_test")
    test_dir.mkdir(parents=True, exist_ok=True)

    flow_content = """---
workflow_name: test_workflow
entry_point: start
end_point: done
---

# Test Workflow

## Nodes

### Node: start (agent: starter)
Start node

### Node: process (agent: processor)
Process node

### Node: done (agent: finisher)
End node

## Edges

start --> process
process --> done
"""

    (test_dir / "flow.md").write_text(flow_content, encoding='utf-8')

    # Parse it
    parser = WorkflowParser()
    workflow = parser.parse_workflow(test_dir / "flow.md")

    # Verify
    checks = {
        "Workflow name parsed": workflow.workflow_name == "test_workflow",
        "Entry point correct": workflow.entry_point == "start",
        "End point correct": workflow.end_point == "done",
        "All nodes parsed": len(workflow.nodes) == 3,
        "All edges parsed": len(workflow.edges) == 2
    }

    for check, passed in checks.items():
        status = "✓" if passed else "✗"
        print(f"{status} {check}")

    all_passed = all(checks.values())
    print(f"\n{'✓ Generated workflow is parseable!' if all_passed else '✗ Parsing f'}")

    return all_passed


def test_generated_agent_parseable():
    """Test that generated agent can be parsed."""
    print("\n=== Testing Generated Agent Parsing ===\n")

    # Create a sample generated agent
    test_dir = Path("test_output/agent_test")
    agents_dir = test_dir / "agents"
    agents_dir.mkdir(parents=True, exist_ok=True)

    agent_content = """---
name: test_agent
model: deepseek-chat
max_output_tokens: 2000
memory_strategy: short_term
tools:
  - read_file
  - write_file
---

## 任务
Test agent

## 输出
<ROUTING_FLAG>success</ROUTING_FLAG>
"""

    (agents_dir / "test_agent.md").write_text(agent_content, encoding='utf-8')

    # Parse it
    parser = WorkflowParser()
    agent = parser.parse_agent(agents_dir / "test_agent.md")

    # Verify
    checks = {
        "Agent name parsed": agent.name == "test_agent",
        "Model parsed": agent.model == "deepseek-chat",
        "Memory strategy parsed": agent.memory_strategy == "short_term",
        "Tools parsed": len(agent.tools) == 2,
        "Prompt content exists": len(agent.prompt_content) > 0
    }

    for check, passed in checks.items():
        status = "✓" if passed else "✗"
        print(f"{status} {check}")

    all_passed = all(checks.values())
    print(f"\n{'✓ Generated agent is parseable!' if all_passed else '✗ Parsing failed'}")

    return all_passed


if __name__ == "__main__":
    print("=" * 60)
    print("WORKFLOW GENERATION E2E TEST SUITE")
    print("=" * 60)

    results = []

    # Test 1: E2E generation
    results.append(("E2E Generation", test_workflow_generation_e2e()))

    # Test 2: Generated workflow parsing
    results.append(("Workflow Parsing", test_generated_workflow_parseable()))

    # Test 3: Generated agent parsing
    results.append(("Agent Parsing", test_generated_agent_parseable()))

    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)

    for test_name, passed in results:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{status}: {test_name}")

    total_passed = sum(1 for _, passed in results if passed)
    print(f"\nTotal: {total_passed}/{len(results)} tests passed")

    if total_passed == len(results):
        print("\n🎉 All tests passed!")
    else:
        print(f"\n⚠ {len(results) - total_passed} test(s) failed")
