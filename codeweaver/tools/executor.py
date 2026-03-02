import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

from codeweaver.tools.filesystem import run_command, read_file, list_files


@dataclass
class ToolResult:
    """Result of a tool execution."""
    success: bool
    output: Optional[Any] = None
    error: Optional[str] = None


class ToolExecutor:
    """
    Safe tool execution system with path validation and sandboxing.

    Wraps existing filesystem tools with security checks to prevent
    directory traversal attacks and ensure operations stay within
    the project root.
    """

    def __init__(self, project_root: str):
        """
        Initialize the ToolExecutor.

        Args:
            project_root: Absolute path to the project root directory.
                         All tool operations are restricted to this directory.
        """
        self.project_root = Path(project_root).resolve()

    def execute(self, tool_name: str, **kwargs) -> ToolResult:
        """
        Execute a tool with the given arguments.

        Args:
            tool_name: Name of the tool to execute (run_command, read_file, list_files)
            **kwargs: Tool-specific arguments

        Returns:
            ToolResult with success status, output, and error information
        """
        try:
            if tool_name == "run_command":
                return self._execute_run_command(**kwargs)
            elif tool_name == "read_file":
                return self._execute_read_file(**kwargs)
            elif tool_name == "list_files":
                return self._execute_list_files(**kwargs)
            else:
                return ToolResult(
                    success=False,
                    output=None,
                    error=f"Unknown tool: {tool_name}"
                )
        except Exception as e:
            return ToolResult(
                success=False,
                output=None,
                error=str(e)
            )

    def _execute_run_command(self, cmd: str, cwd: str, timeout: int = 60) -> ToolResult:
        """Execute run_command with cwd validation."""
        # Validate cwd is within project root
        cwd_path = Path(cwd).resolve()

        if not self._is_within_project(cwd_path):
            return ToolResult(
                success=False,
                output=None,
                error=f"Working directory is outside project root: {cwd_path}"
            )

        try:
            output = run_command(cmd=cmd, cwd=str(cwd_path), timeout=timeout)
            return ToolResult(success=True, output=output, error=None)
        except subprocess.TimeoutExpired as e:
            return ToolResult(
                success=False,
                output=None,
                error=f"Command timeout after {timeout} seconds"
            )
        except Exception as e:
            return ToolResult(success=False, output=None, error=str(e))

    def _execute_read_file(self, path: str) -> ToolResult:
        """Execute read_file with path validation."""
        # Resolve path relative to project root
        if Path(path).is_absolute():
            file_path = Path(path).resolve()
        else:
            file_path = (self.project_root / path).resolve()

        if not self._is_within_project(file_path):
            return ToolResult(
                success=False,
                output=None,
                error=f"File path is outside project root: {file_path}"
            )

        try:
            content = read_file(str(file_path))
            return ToolResult(success=True, output=content, error=None)
        except FileNotFoundError:
            return ToolResult(
                success=False,
                output=None,
                error=f"File not found: {file_path}"
            )
        except Exception as e:
            return ToolResult(success=False, output=None, error=str(e))

    def _execute_list_files(self, directory: str, pattern: str = "**/*.py") -> ToolResult:
        """Execute list_files with directory validation."""
        # Resolve directory relative to project root
        if Path(directory).is_absolute():
            dir_path = Path(directory).resolve()
        else:
            dir_path = (self.project_root / directory).resolve()

        if not self._is_within_project(dir_path):
            return ToolResult(
                success=False,
                output=None,
                error=f"Directory is outside project root: {dir_path}"
            )

        try:
            files = list_files(str(dir_path), pattern=pattern)
            return ToolResult(success=True, output=files, error=None)
        except Exception as e:
            return ToolResult(success=False, output=None, error=str(e))

    def _is_within_project(self, path: Path) -> bool:
        """
        Check if a path is within the project root.

        Args:
            path: Resolved absolute path to check

        Returns:
            True if path is within project root, False otherwise
        """
        try:
            path.relative_to(self.project_root)
            return True
        except ValueError:
            return False

    def get_tool_schemas(self) -> list[dict]:
        """
        Get OpenAI function calling schemas for all available tools.

        Returns:
            List of tool schemas in OpenAI function calling format
        """
        return [
            {
                "type": "function",
                "function": {
                    "name": "run_command",
                    "description": "Execute a shell command safely within the project directory. Returns stdout, stderr, return code, and execution time.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "cmd": {
                                "type": "string",
                                "description": "The shell command to execute (e.g., 'ls -la', 'python script.py')"
                            },
                            "cwd": {
                                "type": "string",
                                "description": "Working directory for command execution (must be within project root)"
                            },
                            "timeout": {
                                "type": "integer",
                                "description": "Command timeout in seconds (default: 60)",
                                "default": 60
                            }
                        },
                        "required": ["cmd", "cwd"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "read_file",
                    "description": "Read the contents of a file within the project directory. Paths are resolved relative to project root.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "path": {
                                "type": "string",
                                "description": "Path to the file to read (relative to project root or absolute within project)"
                            }
                        },
                        "required": ["path"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "list_files",
                    "description": "List files in a directory matching a glob pattern. Directory must be within project root.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "directory": {
                                "type": "string",
                                "description": "Directory to search (relative to project root or absolute within project)"
                            },
                            "pattern": {
                                "type": "string",
                                "description": "Glob pattern to match files (e.g., '*.py', '**/*.txt')",
                                "default": "**/*.py"
                            }
                        },
                        "required": ["directory"]
                    }
                }
            }
        ]
