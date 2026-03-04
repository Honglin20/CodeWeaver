"""Test workflow validation functionality."""
from pathlib import Path
import shutil
from core.validation import validate_workflow, print_validation_results


def test_valid_workflow():
    """Test validation of a valid workflow."""
    print("=== Test 1: Valid Workflow ===\n")

    workflow_dir = "workflows/workflow_generator"
    errors = validate_workflow(workflow_dir)

    print_validation_results(errors)
    print()


def test_missing_flow_file():
    """Test validation when flow.md is missing."""
    print("=== Test 2: Missing flow.md ===\n")

    test_dir = Path("test_output/invalid_workflow")
    test_dir.mkdir(parents=True, exist_ok=True)

    errors = validate_workflow(str(test_dir))
    print_validation_results(errors)

    shutil.rmtree(test_dir)
    print()


def test_missing_agent():
    """Test validation when referenced agent doesn't exist."""
    print("=== Test 3: Missing Agent Reference ===\n")

    test_dir = Path("test_output/missing_agent")
    agents_dir = test_dir / "agents"
    agents_dir.mkdir(parents=True, exist_ok=True)

    # Create flow.md with non-existent agent
    flow_content = """---
workflow_name: test
entry_point: start
end_point: done
---

# Test

## Nodes

### Node: start (agent: nonexistent_agent)
Start

### Node: done (agent: finisher)
Done

## Edges

start --> done
"""
    (test_dir / "flow.md").write_text(flow_content, encoding='utf-8')

    errors = validate_workflow(str(test_dir))
    print_validation_results(errors)

    shutil.rmtree(test_dir)
    print()


def test_circular_dependency():
    """Test detection of circular dependencies."""
    print("=== Test 4: Circular Dependency ===\n")

    test_dir = Path("test_output/circular")
    agents_dir = test_dir / "agents"
    agents_dir.mkdir(parents=True, exist_ok=True)

    # Create agents
    for agent_name in ['a', 'b', 'c']:
        agent_content = f"""---
name: {agent_name}
model: test
max_output_tokens: 100
memory_strategy: ultra_short
tools: []
---

Test agent
"""
        (agents_dir / f"{agent_name}.md").write_text(agent_content, encoding='utf-8')

    # Create flow with circular dependency: a -> b -> c -> a
    flow_content = """---
workflow_name: circular_test
entry_point: a
end_point: c
---

# Circular Test

## Nodes

### Node: a (agent: a)
Node A

### Node: b (agent: b)
Node B

### Node: c (agent: c)
Node C

## Edges

a --> b
b --> c
c --> a
"""
    (test_dir / "flow.md").write_text(flow_content, encoding='utf-8')

    errors = validate_workflow(str(test_dir))
    print_validation_results(errors)

    shutil.rmtree(test_dir)
    print()


def test_unreachable_nodes():
    """Test detection of unreachable nodes."""
    print("=== Test 5: Unreachable Nodes ===\n")

    test_dir = Path("test_output/unreachable")
    agents_dir = test_dir / "agents"
    agents_dir.mkdir(parents=True, exist_ok=True)

    # Create agents
    for agent_name in ['start', 'middle', 'orphan', 'done']:
        agent_content = f"""---
name: {agent_name}
model: test
max_output_tokens: 100
memory_strategy: ultra_short
tools: []
---

Test agent
"""
        (agents_dir / f"{agent_name}.md").write_text(agent_content, encoding='utf-8')

    # Create flow with unreachable node
    flow_content = """---
workflow_name: unreachable_test
entry_point: start
end_point: done
---

# Unreachable Test

## Nodes

### Node: start (agent: start)
Start

### Node: middle (agent: middle)
Middle

### Node: orphan (agent: orphan)
Orphan (unreachable)

### Node: done (agent: done)
Done

## Edges

start --> middle
middle --> done
"""
    (test_dir / "flow.md").write_text(flow_content, encoding='utf-8')

    errors = validate_workflow(str(test_dir))
    print_validation_results(errors)

    shutil.rmtree(test_dir)
    print()


if __name__ == "__main__":
    print("=" * 60)
    print("WORKFLOW VALIDATION TEST SUITE")
    print("=" * 60)
    print()

    test_valid_workflow()
    test_missing_flow_file()
    test_missing_agent()
    test_circular_dependency()
    test_unreachable_nodes()

    print("=" * 60)
    print("All validation tests completed!")
    print("=" * 60)
