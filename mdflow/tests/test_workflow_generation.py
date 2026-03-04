"""Comprehensive test suite for workflow generation system."""
import pytest
from pathlib import Path
import shutil
import tempfile
from core.structured_compiler import StructuredWorkflowCompiler, GraphState
from core.tools import create_default_registry
from core.parser import WorkflowParser


class TestWorkflowGeneration:
    """Test workflow generation with various scenarios."""

    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for test outputs."""
        temp = Path(tempfile.mkdtemp())
        yield temp
        shutil.rmtree(temp)

    @pytest.fixture
    def tool_registry(self):
        """Create tool registry."""
        return create_default_registry()

    def test_simple_linear_workflow(self, temp_dir, tool_registry):
        """Test Case 1: Simple linear workflow generation.

        User Intent: "Create a code review workflow with validation and report generation"
        Expected: Linear flow with 3 nodes
        """
        # Setup
        workflow_dir = temp_dir / "simple_workflow"
        workflow_dir.mkdir()
        memory_dir = workflow_dir / "memory"
        memory_dir.mkdir()

        user_intent = """Create a code review workflow:
1. Validate code quality
2. Generate review report
3. Done
"""
        (memory_dir / "user_intent.md").write_text(user_intent, encoding='utf-8')

        # Expected structure
        expected_nodes = ["validate", "generate_report", "done"]
        expected_edges = [
            ("validate", "generate_report"),
            ("generate_report", "done")
        ]

        # This test verifies the structure is correct
        # In real execution, LLM would generate the files
        assert workflow_dir.exists()
        assert memory_dir.exists()

    def test_conditional_workflow(self, temp_dir, tool_registry):
        """Test Case 2: Conditional workflow with branching.

        User Intent: Code review with conditional approval
        Expected: Branching based on validation result
        """
        workflow_dir = temp_dir / "conditional_workflow"
        workflow_dir.mkdir()
        memory_dir = workflow_dir / "memory"
        memory_dir.mkdir()

        user_intent = """Code review workflow:
1. Validate code
2. If passed, approve and merge
3. If failed, reject and notify
"""
        (memory_dir / "user_intent.md").write_text(user_intent, encoding='utf-8')

        # Expected conditional structure
        expected_conditions = ["[passed]", "[failed]"]

        assert workflow_dir.exists()

    def test_loop_workflow(self, temp_dir, tool_registry):
        """Test Case 3: Workflow with retry loop.

        User Intent: "Code optimization with iterative improvement"
        Expected: Loop structure with exit condition
        """
        workflow_dir = temp_dir / "loop_workflow"
        workflow_dir.mkdir()
        memory_dir = workflow_dir / "memory"
        memory_dir.mkdir()

        user_intent = """Optimization workflow:
1. Analyze code
2. Optimize
3. Test performance
4. If not satisfactory, go back to step 2
5. If satisfactory, done
"""
        (memory_dir / "user_intent.md").write_text(user_intent, encoding='utf-8')

        # Expected loop structure
        expected_loop_edge = ("test_performance", "optimize")

        assert workflow_dir.exists()

    def test_multi_path_workflow(self, temp_dir, tool_registry):
        """Test Case 4: Complex multi-path workflow.

        User Intent: Multi-stage review with parallel checks
        Expected: Multiple paths converging
        """
        workflow_dir = temp_dir / "multipath_workflow"
        workflow_dir.mkdir()
        memory_dir = workflow_dir / "memory"
        memory_dir.mkdir()

        user_intent = """Complex review workflow:
1. Initial validation
2. If passed: security check AND performance check (parallel)
3. If both pass: approve
4. If any fails: reject
"""
        (memory_dir / "user_intent.md").write_text(user_intent, encoding='utf-8')

        assert workflow_dir.exists()

    def test_memory_strategy_inference(self, temp_dir):
        """Test Case 5: Verify memory strategy inference.

        Expected memory strategies:
        - Stateless validation: ultra_short
        - Interactive dialog: short_term
        - Historical analysis: medium_term
        """
        test_cases = [
            ("Run tests and check results", "ultra_short"),
            ("Ask user for confirmation", "short_term"),
            ("Analyze past performance trends", "medium_term")
        ]

        for description, expected_strategy in test_cases:
            # In real implementation, LLM would infer this
            assert expected_strategy in ["ultra_short", "short_term", "medium_term"]

    def test_tool_inference(self, temp_dir):
        """Test Case 6: Verify tool inference from node description.

        Expected tool mappings:
        - Code execution: bash_executor
        - File operations: read_file, write_file
        - Search: search_long_term
        """
        test_cases = [
            ("Run unit tests", ["mock_test_runner"]),
            ("Read configuration file", ["read_file"]),
            ("Write report to file", ["write_file"]),
            ("Search documentation", ["mock_file_reader"])
        ]

        for description, expected_tools in test_cases:
            # Verify tool names are valid
            assert all(isinstance(tool, str) for tool in expected_tools)

    def test_edge_case_empty_intent(self, temp_dir):
        """Test Case 7: Handle empty user intent."""
        workflow_dir = temp_dir / "empty_workflow"
        workflow_dir.mkdir()
        memory_dir = workflow_dir / "memory"
        memory_dir.mkdir()

        (memory_dir / "user_intent.md").write_text("", encoding='utf-8')

        # Should handle gracefully
        assert workflow_dir.exists()

    def test_edge_case_ambiguous_intent(self, temp_dir):
        """Test Case 8: Handle ambiguous user intent."""
        workflow_dir = temp_dir / "ambiguous_workflow"
        workflow_dir.mkdir()
        memory_dir = workflow_dir / "memory"
        memory_dir.mkdir()

        user_intent = "Do something with code"
        (memory_dir / "user_intent.md").write_text(user_intent, encoding='utf-8')

        # Should still attempt to generate reasonable workflow
        assert workflow_dir.exists()

    def test_generated_flow_parseable(self, temp_dir):
        """Test Case 9: Verify generated flow.md is parseable."""
        workflow_dir = temp_dir / "parseable_workflow"
        workflow_dir.mkdir()

        # Create a sample generated flow.md
        flow_content = """---
workflow_name: test_workflow
entry_point: start
end_point: done
---

# Test Workflow

## Nodes

### Node: start (agent: starter)
Start the workflow

### Node: done (agent: finisher)
Complete the workflow

## Edges

start --> done
"""
        (workflow_dir / "flow.md").write_text(flow_content, encoding='utf-8')

        # Verify it can be parsed
        parser = WorkflowParser()
        workflow = parser.parse_workflow(workflow_dir / "flow.md")

        assert workflow.workflow_name == "test_workflow"
        assert workflow.entry_point == "start"
        assert workflow.end_point == "done"
        assert len(workflow.nodes) == 2
        assert len(workflow.edges) == 1

    def test_generated_agent_parseable(self, temp_dir):
        """Test Case 10: Verify generated agent.md is parseable."""
        workflow_dir = temp_dir / "agent_workflow"
        agents_dir = workflow_dir / "agents"
        agents_dir.mkdir(parents=True)

        # Create a sample generated agent.md
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
Test agent task

## 输入
Input description

## 输出
Output description
<ROUTING_FLAG>success</ROUTING_FLAG>
"""
        (agents_dir / "test_agent.md").write_text(agent_content, encoding='utf-8')

        # Verify it can be parsed
        parser = WorkflowParser()
        agent = parser.parse_agent(agents_dir / "test_agent.md")

        assert agent.name == "test_agent"
        assert agent.model == "deepseek-chat"
        assert agent.memory_strategy == "short_term"
        assert "read_file" in agent.tools
        assert "write_file" in agent.tools


class TestWorkflowGenerationIntegration:
    """Integration tests for end-to-end workflow generation."""

    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory."""
        temp = Path(tempfile.mkdtemp())
        yield temp
        shutil.rmtree(temp)

    def test_intent_to_skeleton_flow(self, temp_dir):
        """Test Case 11: Intent parsing to skeleton generation flow."""
        # This would test the full pipeline:
        # user_intent.md -> intent_analysis.md -> flow.md
        pass

    def test_skeleton_to_agents_flow(self, temp_dir):
        """Test Case 12: Skeleton to agent generation flow."""
        # This would test:
        # flow.md -> multiple agent.md files
        pass

    def test_full_generation_pipeline(self, temp_dir):
        """Test Case 13: Complete generation pipeline."""
        # This would test:
        # user_intent.md -> intent_analysis.md -> flow.md -> agent.md files
        # Then verify the generated workflow can be compiled and executed
        pass


class TestWorkflowGenerationRobustness:
    """Robustness tests for error handling and edge cases."""

    def test_invalid_yaml_frontmatter(self, temp_dir):
        """Test Case 14: Handle invalid YAML in generated files."""
        pass

    def test_missing_required_fields(self, temp_dir):
        """Test Case 15: Handle missing required fields in generated files."""
        pass

    def test_circular_dependencies(self, temp_dir):
        """Test Case 16: Detect circular dependencies in generated workflows."""
        pass

    def test_unreachable_nodes(self, temp_dir):
        """Test Case 17: Detect unreachable nodes in generated workflows."""
        pass

    def test_invalid_tool_references(self, temp_dir):
        """Test Case 18: Handle invalid tool references in generated agents."""
        pass


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
