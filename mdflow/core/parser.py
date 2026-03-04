"""Markdown parser for agent and workflow configurations."""
import re
from pathlib import Path
from typing import Dict, Any, List
import frontmatter

from .models import AgentConfig, WorkflowConfig, WorkflowNode, WorkflowEdge


class ParserConfigurationError(Exception):
    """Raised when configuration parsing fails."""
    pass


def parse_agent_file(file_path: str) -> AgentConfig:
    """Parse agent markdown file into AgentConfig.

    Args:
        file_path: Path to agent markdown file

    Returns:
        AgentConfig object

    Raises:
        ParserConfigurationError: If file is invalid or missing required fields
    """
    try:
        path = Path(file_path)
        if not path.exists():
            raise ParserConfigurationError(f"Agent file not found: {file_path}")

        with open(path, 'r', encoding='utf-8') as f:
            post = frontmatter.load(f)

        # Extract YAML frontmatter
        metadata = post.metadata

        # Validate required fields
        if 'name' not in metadata:
            raise ParserConfigurationError(f"Missing required field 'name' in {file_path}")
        if 'model' not in metadata:
            raise ParserConfigurationError(f"Missing required field 'model' in {file_path}")

        # Extract system prompt from markdown content
        content = post.content
        system_prompt = _extract_system_prompt(content)

        # Build AgentConfig
        return AgentConfig(
            name=metadata['name'],
            model=metadata['model'],
            max_output_tokens=metadata.get('max_output_tokens', 2000),
            memory_strategy=metadata.get('memory_strategy', 'full'),
            tools=metadata.get('tools', []),
            system_prompt=system_prompt
        )

    except ParserConfigurationError:
        raise
    except Exception as e:
        raise ParserConfigurationError(f"Failed to parse agent file {file_path}: {str(e)}")


def _extract_system_prompt(content: str) -> str:
    """Extract system prompt from markdown content."""
    # Look for ## System Prompt section
    match = re.search(r'^##\s+System\s+Prompt\s*$', content, re.MULTILINE | re.IGNORECASE)
    if match:
        # Extract everything after this heading
        start = match.end()
        # Find next heading or end of content
        next_heading = re.search(r'^##\s+', content[start:], re.MULTILINE)
        if next_heading:
            return content[start:start + next_heading.start()].strip()
        return content[start:].strip()

    # If no specific section, return all content
    return content.strip()


def parse_workflow_file(file_path: str) -> WorkflowConfig:
    """Parse workflow markdown file into WorkflowConfig.

    Args:
        file_path: Path to workflow markdown file

    Returns:
        WorkflowConfig object

    Raises:
        ParserConfigurationError: If file is invalid or missing required fields
    """
    try:
        path = Path(file_path)
        if not path.exists():
            raise ParserConfigurationError(f"Workflow file not found: {file_path}")

        with open(path, 'r', encoding='utf-8') as f:
            post = frontmatter.load(f)

        metadata = post.metadata

        # Validate required fields
        required = ['workflow_name', 'entry_point', 'end_point']
        for field in required:
            if field not in metadata:
                raise ParserConfigurationError(f"Missing required field '{field}' in {file_path}")

        # Parse nodes and edges from content
        nodes = _parse_nodes(post.content)
        edges = _parse_edges(post.content)

        return WorkflowConfig(
            workflow_name=metadata['workflow_name'],
            entry_point=metadata['entry_point'],
            end_point=metadata['end_point'],
            nodes=nodes,
            edges=edges
        )

    except ParserConfigurationError:
        raise
    except Exception as e:
        raise ParserConfigurationError(f"Failed to parse workflow file {file_path}: {str(e)}")


def _parse_nodes(content: str) -> List[WorkflowNode]:
    """Parse node definitions from markdown content."""
    nodes = []
    # Match: ### Node: node_name (agent: agent_name)
    pattern = r'^###\s+Node:\s+(\w+)\s+\(agent:\s+(\w+)\)(?:\s*-\s*(.+))?$'

    for match in re.finditer(pattern, content, re.MULTILINE):
        node_name = match.group(1)
        agent_name = match.group(2)
        description = match.group(3).strip() if match.group(3) else None

        nodes.append(WorkflowNode(
            name=node_name,
            agent_name=agent_name,
            description=description
        ))

    return nodes


def _parse_edges(content: str) -> List[WorkflowEdge]:
    """Parse edge definitions from markdown content."""
    edges = []
    # Match: A --> B : [condition] or A --> B
    pattern = r'(\w+)\s*-->\s*(\w+)(?:\s*:\s*\[([^\]]+)\])?'

    for match in re.finditer(pattern, content):
        source = match.group(1)
        target = match.group(2)
        condition = match.group(3).strip() if match.group(3) else None

        edges.append(WorkflowEdge(
            source=source,
            target=target,
            condition=condition
        ))

    return edges

