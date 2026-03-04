"""Workflow validation utilities."""
from pathlib import Path
from typing import List, Dict, Set
from dataclasses import dataclass
from .parser import parse_workflow_file
import frontmatter


@dataclass
class ValidationError:
    """Validation error with context."""
    severity: str  # 'error' or 'warning'
    message: str
    file_path: str
    line_number: int = 0
    suggestion: str = ""


class WorkflowValidator:
    """Validate workflow before execution."""

    def __init__(self, workflow_dir: Path):
        self.workflow_dir = Path(workflow_dir)
        self.errors: List[ValidationError] = []
        self.warnings: List[ValidationError] = []

    def validate(self) -> List[ValidationError]:
        """Run all validation checks."""
        self.errors = []
        self.warnings = []

        # Check flow.md exists
        flow_file = self.workflow_dir / "flow.md"
        if not flow_file.exists():
            self.errors.append(ValidationError(
                severity='error',
                message=f"flow.md not found",
                file_path=str(self.workflow_dir),
                suggestion=f"Create {flow_file} with workflow definition"
            ))
            return self.errors + self.warnings

        # Parse workflow
        try:
            workflow = parse_workflow_file(str(flow_file))
        except Exception as e:
            self.errors.append(ValidationError(
                severity='error',
                message=f"Failed to parse flow.md: {e}",
                file_path=str(flow_file),
                suggestion="Check YAML frontmatter and markdown syntax"
            ))
            return self.errors + self.warnings

        # Check agents directory
        agents_dir = self.workflow_dir / "agents"
        if not agents_dir.exists():
            self.errors.append(ValidationError(
                severity='error',
                message="agents/ directory not found",
                file_path=str(self.workflow_dir),
                suggestion=f"Create {agents_dir} and add agent definitions"
            ))
            return self.errors + self.warnings

        # Load available agents
        available_agents = set()
        for agent_file in agents_dir.glob("*.md"):
            try:
                post = frontmatter.load(agent_file)
                agent_name = post.metadata.get('name')
                if agent_name:
                    available_agents.add(agent_name)
            except Exception as e:
                self.errors.append(ValidationError(
                    severity='error',
                    message=f"Failed to parse agent file: {e}",
                    file_path=str(agent_file),
                    suggestion="Check YAML frontmatter syntax"
                ))

        # Validate nodes reference existing agents
        for node in workflow.nodes:
            if node.agent_name not in available_agents:
                self.errors.append(ValidationError(
                    severity='error',
                    message=f"Node '{node.name}' references unknown agent '{node.agent_name}'",
                    file_path=str(flow_file),
                    suggestion=f"Available agents: {', '.join(sorted(available_agents))}\n"
                              f"Create {agents_dir}/{node.agent_name}.md or fix agent reference"
                ))

        # Check for circular dependencies
        circular = self._detect_circular_dependencies(workflow)
        if circular:
            self.errors.append(ValidationError(
                severity='error',
                message=f"Circular dependency detected: {' -> '.join(circular)}",
                file_path=str(flow_file),
                suggestion="Remove circular edges to create a valid DAG"
            ))

        # Check for unreachable nodes
        unreachable = self._find_unreachable_nodes(workflow)
        if unreachable:
            self.warnings.append(ValidationError(
                severity='warning',
                message=f"Unreachable nodes: {', '.join(unreachable)}",
                file_path=str(flow_file),
                suggestion="Add edges to connect these nodes or remove them"
            ))

        # Check entry and end points exist
        node_names = {node.name for node in workflow.nodes}
        if workflow.entry_point not in node_names:
            self.errors.append(ValidationError(
                severity='error',
                message=f"Entry point '{workflow.entry_point}' not found in nodes",
                file_path=str(flow_file),
                suggestion=f"Available nodes: {', '.join(sorted(node_names))}"
            ))

        if workflow.end_point not in node_names:
            self.errors.append(ValidationError(
                severity='error',
                message=f"End point '{workflow.end_point}' not found in nodes",
                file_path=str(flow_file),
                suggestion=f"Available nodes: {', '.join(sorted(node_names))}"
            ))

        return self.errors + self.warnings

    def _detect_circular_dependencies(self, workflow) -> List[str]:
        """Detect circular dependencies using DFS."""
        graph = {}
        for node in workflow.nodes:
            graph[node.name] = []

        for edge in workflow.edges:
            if edge.source in graph:
                graph[edge.source].append(edge.target)

        visited = set()
        rec_stack = set()
        path = []

        def dfs(node):
            visited.add(node)
            rec_stack.add(node)
            path.append(node)

            for neighbor in graph.get(node, []):
                if neighbor not in visited:
                    result = dfs(neighbor)
                    if result:
                        return result
                elif neighbor in rec_stack:
                    # Found cycle
                    cycle_start = path.index(neighbor)
                    return path[cycle_start:] + [neighbor]

            path.pop()
            rec_stack.remove(node)
            return None

        for node in graph:
            if node not in visited:
                cycle = dfs(node)
                if cycle:
                    return cycle

        return []

    def _find_unreachable_nodes(self, workflow) -> Set[str]:
        """Find nodes unreachable from entry point."""
        reachable = set()
        to_visit = [workflow.entry_point]

        # Build adjacency list
        graph = {}
        for node in workflow.nodes:
            graph[node.name] = []

        for edge in workflow.edges:
            if edge.source in graph:
                graph[edge.source].append(edge.target)

        # BFS from entry point
        while to_visit:
            current = to_visit.pop(0)
            if current in reachable:
                continue
            reachable.add(current)
            to_visit.extend(graph.get(current, []))

        # Find unreachable
        all_nodes = {node.name for node in workflow.nodes}
        return all_nodes - reachable


def validate_workflow(workflow_dir: str) -> List[ValidationError]:
    """Validate workflow and return errors/warnings."""
    validator = WorkflowValidator(Path(workflow_dir))
    return validator.validate()


def print_validation_results(errors: List[ValidationError]) -> bool:
    """Print validation results and return True if no errors."""
    has_errors = False

    for error in errors:
        if error.severity == 'error':
            has_errors = True
            symbol = "✗"
            color = "\033[91m"  # Red
        else:
            symbol = "⚠"
            color = "\033[93m"  # Yellow

        reset = "\033[0m"

        print(f"{color}{symbol} {error.severity.upper()}{reset}: {error.message}")
        print(f"  File: {error.file_path}")
        if error.line_number:
            print(f"  Line: {error.line_number}")
        if error.suggestion:
            print(f"  Suggestion: {error.suggestion}")
        print()

    if not errors:
        print("✓ Workflow validation passed!")
        return True
    elif not has_errors:
        print("✓ Workflow validation passed with warnings")
        return True
    else:
        print(f"✗ Workflow validation failed with {sum(1 for e in errors if e.severity == 'error')} error(s)")
        return False
