"""Tool registry for agent capabilities."""
from typing import Callable, Dict, List
from langchain_core.tools import tool


class ToolRegistry:
    """Registry for managing agent tools."""

    def __init__(self):
        """Initialize empty registry."""
        self._tools: Dict[str, Callable] = {}

    def register(self, name: str, tool_callable: Callable):
        """Register a tool.

        Args:
            name: Tool identifier
            tool_callable: Tool function (should be decorated with @tool)
        """
        self._tools[name] = tool_callable
        print(f"[ToolRegistry] Registered tool: {name}")

    def get_tools(self, names: List[str]) -> List[Callable]:
        """Get tools by names.

        Args:
            names: List of tool names

        Returns:
            List of tool callables
        """
        tools = []
        for name in names:
            if name in self._tools:
                tools.append(self._tools[name])
            else:
                print(f"[ToolRegistry] Warning: Tool '{name}' not found")
        return tools


# Built-in test tools
@tool
def mock_test_runner(test_suite: str) -> str:
    """Run a test suite and return results.

    Args:
        test_suite: Name of the test suite to run

    Returns:
        Test results
    """
    return f"Test suite '{test_suite}' passed: 10/10 tests"


@tool
def mock_file_reader(file_path: str) -> str:
    """Read a file and return its content.

    Args:
        file_path: Path to the file

    Returns:
        File content
    """
    return f"Content of {file_path}: Mock file data"


def create_default_registry() -> ToolRegistry:
    """Create registry with default tools."""
    registry = ToolRegistry()
    registry.register("mock_test_runner", mock_test_runner)
    registry.register("mock_file_reader", mock_file_reader)
    return registry
