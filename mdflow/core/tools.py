"""Tool registry for agent capabilities."""
from typing import Callable, Dict, List
from langchain_core.tools import tool
from pathlib import Path
from .logging_config import get_logger

logger = get_logger(__name__)


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
        logger.debug(f"Registered tool: {name}")

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
                logger.warning(f"Tool '{name}' not found in registry")
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


@tool
def write_file(file_path: str, content: str) -> str:
    """Write content to file.

    Args:
        file_path: Path to write to
        content: Content to write

    Returns:
        Success message
    """
    path = Path(file_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding='utf-8')
    return f"File written: {file_path}"


@tool
def read_file(file_path: str) -> str:
    """Read file content.

    Args:
        file_path: Path to read from

    Returns:
        File content
    """
    return Path(file_path).read_text(encoding='utf-8')


def create_default_registry() -> ToolRegistry:
    """Create registry with default tools."""
    registry = ToolRegistry()
    registry.register("mock_test_runner", mock_test_runner)
    registry.register("mock_file_reader", mock_file_reader)
    registry.register("write_file", write_file)
    registry.register("read_file", read_file)
    return registry
