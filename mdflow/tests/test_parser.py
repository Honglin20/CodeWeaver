"""Tests for parser functionality."""
import pytest
import tempfile
from pathlib import Path

from core.parser import (
    parse_agent_file,
    parse_workflow_file,
    ParserConfigurationError
)
from core.models import AgentConfig, WorkflowConfig


# Test fixtures as strings
VALID_AGENT_MD = """---
name: test_agent
model: gpt-4
max_output_tokens: 1000
memory_strategy: sliding_window
tools:
  - search
  - calculator
---

# Test Agent

## System Prompt

You are a helpful assistant that can search and calculate.
"""

AGENT_MISSING_MODEL = """---
name: test_agent
max_output_tokens: 1000
---

## System Prompt

Test prompt.
"""

VALID_WORKFLOW_MD = """---
workflow_name: test_workflow
entry_point: start
end_point: end
---

# Test Workflow

### Node: start (agent: planner)

### Node: process (agent: worker) - Process the data

### Node: end (agent: summarizer)

## Flow

start --> process : [condition_a]
process --> end
"""


class TestAgentParser:
    """Test agent file parsing."""

    def test_parse_valid_agent(self):
        """Test parsing a valid agent file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
            f.write(VALID_AGENT_MD)
            f.flush()
            temp_path = f.name

        try:
            config = parse_agent_file(temp_path)

            assert config.name == "test_agent"
            assert config.model == "gpt-4"
            assert config.max_output_tokens == 1000
            assert config.memory_strategy == "sliding_window"
            assert config.tools == ["search", "calculator"]
            assert "helpful assistant" in config.system_prompt
        finally:
            Path(temp_path).unlink()

    def test_parse_agent_missing_model(self):
        """Test that missing model field raises error."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
            f.write(AGENT_MISSING_MODEL)
            f.flush()
            temp_path = f.name

        try:
            with pytest.raises(ParserConfigurationError, match="Missing required field 'model'"):
                parse_agent_file(temp_path)
        finally:
            Path(temp_path).unlink()

    def test_parse_agent_file_not_found(self):
        """Test that non-existent file raises error."""
        with pytest.raises(ParserConfigurationError, match="Agent file not found"):
            parse_agent_file("/nonexistent/path.md")


class TestWorkflowParser:
    """Test workflow file parsing."""

    def test_parse_valid_workflow(self):
        """Test parsing a valid workflow with nodes and edges."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
            f.write(VALID_WORKFLOW_MD)
            f.flush()
            temp_path = f.name

        try:
            config = parse_workflow_file(temp_path)

            assert config.workflow_name == "test_workflow"
            assert config.entry_point == "start"
            assert config.end_point == "end"

            # Check nodes
            assert len(config.nodes) == 3
            assert config.nodes[0].name == "start"
            assert config.nodes[0].agent_name == "planner"
            assert config.nodes[1].name == "process"
            assert config.nodes[1].agent_name == "worker"
            assert config.nodes[1].description == "Process the data"

            # Check edges
            assert len(config.edges) == 2
            assert config.edges[0].source == "start"
            assert config.edges[0].target == "process"
            assert config.edges[0].condition == "condition_a"
            assert config.edges[1].source == "process"
            assert config.edges[1].target == "end"
            assert config.edges[1].condition is None
        finally:
            Path(temp_path).unlink()
    def test_parse_workflow_missing_required_field(self):
        """Test that missing required field raises error."""
        invalid_workflow = """---
workflow_name: test
entry_point: start
---
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
            f.write(invalid_workflow)
            f.flush()
            temp_path = f.name

        try:
            with pytest.raises(ParserConfigurationError, match="Missing required field 'end_point'"):
                parse_workflow_file(temp_path)
        finally:
            Path(temp_path).unlink()

    def test_parse_workflow_edge_regex(self):
        """Test edge parsing with various formats."""
        workflow_with_edges = """---
workflow_name: test
entry_point: a
end_point: d
---

a --> b
b-->c : [check_status]
c  -->  d  :  [final_check]
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
            f.write(workflow_with_edges)
            f.flush()
            temp_path = f.name

        try:
            config = parse_workflow_file(temp_path)

            assert len(config.edges) == 3
            assert config.edges[0].source == "a"
            assert config.edges[0].target == "b"
            assert config.edges[0].condition is None
            assert config.edges[1].condition == "check_status"
            assert config.edges[2].condition == "final_check"
        finally:
            Path(temp_path).unlink()
