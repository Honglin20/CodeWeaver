"""
Tool inference system for automatically determining which tools an agent needs.

This module analyzes agent descriptions and system prompts to infer required tools,
reducing manual configuration and improving agent flexibility.
"""

import re
from typing import Set


class ToolInferencer:
    """Infers required tools from agent description and system prompt."""

    # Keywords that suggest specific tools
    TOOL_KEYWORDS = {
        "read_file": [
            "read", "file", "content", "source", "code", "examine", "inspect",
            "analyze file", "check file", "view file"
        ],
        "list_files": [
            "list", "find files", "search files", "directory", "glob",
            "enumerate", "discover files", "scan directory"
        ],
        "run_command": [
            "execute", "run", "command", "shell", "bash", "script",
            "test", "compile", "build", "install"
        ],
        "build_code_tree": [
            "structure", "architecture", "hierarchy", "tree", "overview",
            "map project", "analyze structure", "project layout"
        ],
        "tool:select": [
            "user", "choose", "select", "option", "prompt", "ask",
            "interact", "decision", "choice", "present options"
        ]
    }

    # Tools that are commonly needed together
    TOOL_DEPENDENCIES = {
        "read_file": ["list_files"],  # If reading files, likely need to list them first
        "run_command": [],
        "build_code_tree": [],
        "tool:select": [],
        "list_files": []
    }

    def __init__(self):
        # Compile regex patterns for efficiency
        self.patterns = {}
        for tool, keywords in self.TOOL_KEYWORDS.items():
            pattern = r'\b(' + '|'.join(re.escape(kw) for kw in keywords) + r')\b'
            self.patterns[tool] = re.compile(pattern, re.IGNORECASE)

    def infer_tools(self, description: str, system_prompt: str, explicit_tools: list[str] | None = None) -> list[str]:
        """
        Infer required tools from agent description and system prompt.

        Args:
            description: Agent description
            system_prompt: Agent system prompt
            explicit_tools: Explicitly specified tools (takes precedence)

        Returns:
            List of inferred tool names
        """
        # If explicit tools provided, use them
        if explicit_tools:
            return explicit_tools

        # Combine description and system prompt for analysis
        text = f"{description} {system_prompt}"

        # Find matching tools
        inferred: Set[str] = set()
        for tool, pattern in self.patterns.items():
            if pattern.search(text):
                inferred.add(tool)
                # Add dependencies
                for dep in self.TOOL_DEPENDENCIES.get(tool, []):
                    inferred.add(dep)

        # Convert to sorted list for consistency
        return sorted(inferred)

    def suggest_tools(self, description: str, system_prompt: str) -> dict[str, list[str]]:
        """
        Suggest tools with explanations of why they were inferred.

        Args:
            description: Agent description
            system_prompt: Agent system prompt

        Returns:
            Dictionary mapping tool names to lists of matching keywords
        """
        text = f"{description} {system_prompt}"
        suggestions = {}

        for tool, pattern in self.patterns.items():
            matches = pattern.findall(text)
            if matches:
                suggestions[tool] = list(set(matches))  # Unique matches

        return suggestions


# Global instance
_inferencer = ToolInferencer()


def infer_agent_tools(description: str, system_prompt: str, explicit_tools: list[str] | None = None) -> list[str]:
    """
    Convenience function to infer tools for an agent.

    Args:
        description: Agent description
        system_prompt: Agent system prompt
        explicit_tools: Explicitly specified tools (takes precedence)

    Returns:
        List of inferred tool names
    """
    return _inferencer.infer_tools(description, system_prompt, explicit_tools)
