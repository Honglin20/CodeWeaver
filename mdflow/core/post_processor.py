"""Post-processing layer for workflow generation output normalization."""
import re
from typing import Dict, List, Tuple
from dataclasses import dataclass


@dataclass
class NormalizationResult:
    """Result of normalization process."""
    content: str
    changes_made: List[str]
    warnings: List[str]


class WorkflowOutputNormalizer:
    """Normalize LLM output to ensure consistent format."""

    def __init__(self):
        self.changes_made = []
        self.warnings = []

    def normalize(self, content: str) -> NormalizationResult:
        """Normalize workflow generation output.

        Args:
            content: Raw LLM output

        Returns:
            NormalizationResult with normalized content and metadata
        """
        self.changes_made = []
        self.warnings = []

        normalized = content

        # Step 1: Normalize condition format
        normalized = self._normalize_conditions(normalized)

        # Step 2: Normalize node names
        normalized = self._normalize_node_names(normalized)

        # Step 3: Normalize memory strategies
        normalized = self._normalize_memory_strategies(normalized)

        # Step 4: Validate structure
        self._validate_structure(normalized)

        return NormalizationResult(
            content=normalized,
            changes_made=self.changes_made,
            warnings=self.warnings
        )

    def _normalize_conditions(self, content: str) -> str:
        """Normalize condition format to use brackets.

        Converts:
        - "validate --> review : 验证通过" → "validate --> review : [passed]"
        - "test --> retry : failed" → "test --> retry : [failed]"
        - "check --> next : 性能<10%" → "check --> next : [retry]"
        """
        # Extract flow section
        if "## Flow" not in content:
            return content

        flow_start = content.index("## Flow")
        flow_end = len(content)
        if "<ROUTING_FLAG>" in content[flow_start:]:
            flow_end = flow_start + content[flow_start:].index("<ROUTING_FLAG>")

        before_flow = content[:flow_start]
        flow_section = content[flow_start:flow_end]
        after_flow = content[flow_end:]

        # Process each line with arrows
        lines = flow_section.split('\n')
        normalized_lines = []

        for line in lines:
            if '-->' in line and ':' in line:
                normalized_line = self._normalize_condition_line(line)
                if normalized_line != line:
                    self.changes_made.append(f"Normalized condition: {line.strip()} → {normalized_line.strip()}")
                normalized_lines.append(normalized_line)
            else:
                normalized_lines.append(line)

        return before_flow + '\n'.join(normalized_lines) + after_flow

    def _normalize_condition_line(self, line: str) -> str:
        """Normalize a single condition line."""
        # Split by arrow and colon
        if '-->' not in line or ':' not in line:
            return line

        parts = line.split('-->')
        if len(parts) != 2:
            return line

        source = parts[0].strip()
        target_and_condition = parts[1].split(':', 1)
        if len(target_and_condition) != 2:
            return line

        target = target_and_condition[0].strip()
        condition = target_and_condition[1].strip()

        # Check if already in bracket format
        if condition.startswith('[') and condition.endswith(']'):
            return line

        # Map common patterns to standard conditions
        normalized_condition = self._map_condition(condition)

        # Reconstruct line
        indent = len(line) - len(line.lstrip())
        return ' ' * indent + f"{source} --> {target} : {normalized_condition}"

    def _map_condition(self, condition: str) -> str:
        """Map various condition formats to standard bracket format."""
        condition_lower = condition.lower()

        # Remove quotes if present
        condition = condition.strip('"\'')

        # Mapping rules
        mappings = {
            # Success/failure patterns
            r'(通过|passed|success|成功|ok)': '[passed]',
            r'(失败|failed|failure|错误|error)': '[failed]',

            # Confirmation patterns
            r'(确认|confirmed|approved|批准)': '[confirmed]',
            r'(拒绝|rejected|denied)': '[rejected]',

            # Retry/complete patterns
            r'(重试|retry|again|继续)': '[retry]',
            r'(完成|complete|done|finished)': '[complete]',

            # Timeout patterns
            r'(超时|timeout|expired)': '[timeout]',

            # Conditional expressions - check for comparison operators
            r'(<|不足|小于)': '[retry]',
            r'(>=|达标|大于等于)': '[complete]',
        }

        for pattern, replacement in mappings.items():
            if re.search(pattern, condition, re.IGNORECASE):
                return replacement

        # If no mapping found, try to extract English word
        english_words = re.findall(r'[a-zA-Z]+', condition)
        if english_words:
            word = english_words[0].lower()
            if word in ['passed', 'failed', 'confirmed', 'rejected', 'retry', 'complete', 'timeout', 'error', 'success']:
                return f'[{word}]'

        # Default: wrap in brackets
        self.warnings.append(f"Could not map condition '{condition}', using default [default]")
        return '[default]'

    def _normalize_node_names(self, content: str) -> str:
        """Ensure node names use English and underscores."""
        # This is complex and risky, so we just warn for now
        if "## Nodes" in content:
            nodes_section = content[content.index("## Nodes"):]
            if "<ROUTING_FLAG>" in nodes_section:
                nodes_section = nodes_section[:nodes_section.index("<ROUTING_FLAG>")]

            # Check for Chinese in node names
            node_lines = [line for line in nodes_section.split('\n') if line.strip().startswith('- **')]
            for line in node_lines:
                match = re.search(r'\*\*([^*]+)\*\*', line)
                if match:
                    node_name = match.group(1)
                    if re.search(r'[\u4e00-\u9fff]', node_name):
                        self.warnings.append(f"Node name contains Chinese characters: {node_name}")

        return content

    def _normalize_memory_strategies(self, content: str) -> str:
        """Normalize memory strategy values."""
        valid_strategies = ['ultra_short', 'short_term', 'medium_term']

        # Find all memory strategy lines
        lines = content.split('\n')
        normalized_lines = []

        for line in lines:
            if 'memory:' in line.lower():
                # Extract memory value
                match = re.search(r'memory:\s*([^\n]+)', line, re.IGNORECASE)
                if match:
                    memory_value = match.group(1).strip()

                    # Check if valid
                    if memory_value not in valid_strategies:
                        # Try to map
                        if '短' in memory_value or 'short' in memory_value.lower():
                            if '超' in memory_value or 'ultra' in memory_value.lower():
                                new_value = 'ultra_short'
                            else:
                                new_value = 'short_term'
                        elif '中' in memory_value or 'medium' in memory_value.lower():
                            new_value = 'medium_term'
                        elif '长' in memory_value or 'long' in memory_value.lower():
                            new_value = 'medium_term'
                        else:
                            new_value = 'short_term'  # Default

                        line = line.replace(memory_value, new_value)
                        self.changes_made.append(f"Normalized memory strategy: {memory_value} → {new_value}")

                normalized_lines.append(line)
            else:
                normalized_lines.append(line)

        return '\n'.join(normalized_lines)

    def _validate_structure(self, content: str) -> None:
        """Validate the structure and add warnings."""
        required_sections = [
            "# Workflow Intent Analysis",
            "## Workflow Name",
            "## Nodes",
            "## Flow"
        ]

        for section in required_sections:
            if section not in content:
                self.warnings.append(f"Missing required section: {section}")

        # Check for routing flag
        if "<ROUTING_FLAG>" not in content:
            self.warnings.append("Missing <ROUTING_FLAG> marker")

        # Check for at least one node
        if "- **" not in content:
            self.warnings.append("No nodes found")

        # Check for at least one edge
        if "-->" not in content:
            self.warnings.append("No edges found")


def normalize_workflow_output(content: str) -> NormalizationResult:
    """Convenience function to normalize workflow output.

    Args:
        content: Raw LLM output

    Returns:
        NormalizationResult with normalized content
    """
    normalizer = WorkflowOutputNormalizer()
    return normalizer.normalize(content)
