import logging
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

from codeweaver.tools.filesystem import run_command, read_file, list_files

logger = logging.getLogger(__name__)


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
        logger.info(f"ToolExecutor initialized with project root: {self.project_root}")

    def execute(self, tool_name: str, **kwargs) -> ToolResult:
        """
        Execute a tool with the given arguments.

        Args:
            tool_name: Name of the tool to execute (run_command, read_file, list_files)
            **kwargs: Tool-specific arguments

        Returns:
            ToolResult with success status, output, and error information
        """
        logger.info(f"Executing tool: {tool_name}")
        try:
            if tool_name == "run_command":
                return self._execute_run_command(**kwargs)
            elif tool_name == "read_file":
                return self._execute_read_file(**kwargs)
            elif tool_name == "list_files":
                return self._execute_list_files(**kwargs)
            else:
                logger.warning(f"Unknown tool requested: {tool_name}")
                return ToolResult(
                    success=False,
                    output=None,
                    error=f"Unknown tool: {tool_name}"
                )
        except Exception as e:
            logger.error(f"Tool execution failed: {tool_name}", exc_info=True)
            return ToolResult(
                success=False,
                output=None,
                error=str(e)
            )

    def _execute_run_command(self, cmd: str, cwd: str, timeout: int = 60) -> ToolResult:
        """Execute run_command with cwd validation."""
        # Resolve and validate cwd path
        try:
            cwd_path = self._resolve_path(cwd)
        except (ValueError, RuntimeError) as e:
            logger.warning(f"Path validation failed for cwd: {cwd}")
            return ToolResult(
                success=False,
                output=None,
                error=self._sanitize_error_message(str(e))
            )

        # Log command execution for security auditing
        logger.info(f"Executing command: {cmd} in {self._get_relative_path(cwd_path)}")

        try:
            output = run_command(cmd=cmd, cwd=str(cwd_path), timeout=timeout)
            return ToolResult(success=True, output=output, error=None)
        except subprocess.TimeoutExpired as e:
            logger.warning(f"Command timeout: {cmd}")
            return ToolResult(
                success=False,
                output=None,
                error=f"Command timeout after {timeout} seconds"
            )
        except Exception as e:
            logger.error(f"Command execution failed: {cmd}", exc_info=True)
            return ToolResult(success=False, output=None, error=str(e))

    def _execute_read_file(self, path: str) -> ToolResult:
        """Execute read_file with path validation."""
        # Resolve and validate file path
        try:
            file_path = self._resolve_path(path)
        except (ValueError, RuntimeError) as e:
            logger.warning(f"Path validation failed for read_file: {path}")
            return ToolResult(
                success=False,
                output=None,
                error=self._sanitize_error_message(str(e))
            )

        try:
            content = read_file(str(file_path))
            logger.debug(f"Read file: {self._get_relative_path(file_path)}")
            return ToolResult(success=True, output=content, error=None)
        except FileNotFoundError:
            return ToolResult(
                success=False,
                output=None,
                error=f"File not found: {self._get_relative_path(file_path)}"
            )
        except Exception as e:
            logger.error(f"Failed to read file: {path}", exc_info=True)
            return ToolResult(success=False, output=None, error=str(e))

    def _execute_list_files(self, directory: str, pattern: str = "**/*.py") -> ToolResult:
        """Execute list_files with directory validation."""
        # Resolve and validate directory path
        try:
            dir_path = self._resolve_path(directory)
        except (ValueError, RuntimeError) as e:
            logger.warning(f"Path validation failed for list_files: {directory}")
            return ToolResult(
                success=False,
                output=None,
                error=self._sanitize_error_message(str(e))
            )

        try:
            files = list_files(str(dir_path), pattern=pattern)
            logger.debug(f"Listed files in: {self._get_relative_path(dir_path)}")
            return ToolResult(success=True, output=files, error=None)
        except Exception as e:
            logger.error(f"Failed to list files in: {directory}", exc_info=True)
            return ToolResult(success=False, output=None, error=str(e))

    def _resolve_path(self, path: str) -> Path:
        """
        Resolve a path relative to project root and validate it's within project.

        This method handles both absolute and relative paths, checks for symlinks,
        and ensures the resolved path is within the project root.

        Args:
            path: Path to resolve (absolute or relative to project root)

        Returns:
            Resolved absolute Path object

        Raises:
            ValueError: If path is outside project root
            RuntimeError: If path contains symlinks (security risk)
        """
        path_obj = Path(path)

        # Handle absolute vs relative paths
        if path_obj.is_absolute():
            resolved_path = path_obj.resolve()
        else:
            resolved_path = (self.project_root / path).resolve()

        # Check for symlinks before validation (security check)
        # We need to check if any component in the path is a symlink
        try:
            current = Path(path) if path_obj.is_absolute() else self.project_root / path
            # Walk up the path checking each component
            parts_to_check = current.parts if current.is_absolute() else (self.project_root / current).parts
            check_path = Path(parts_to_check[0]) if current.is_absolute() else Path("/")

            for part in parts_to_check[1:] if current.is_absolute() else parts_to_check:
                check_path = check_path / part
                if check_path.exists() and check_path.is_symlink():
                    logger.warning(f"Symlink detected in path: {path}")
                    raise RuntimeError(f"Path contains symlink: {self._get_relative_path(check_path)}")
        except (OSError, RuntimeError) as e:
            if isinstance(e, RuntimeError):
                raise
            # If we can't check (path doesn't exist yet), continue with validation
            pass

        # Validate path is within project root
        if not self._is_within_project(resolved_path):
            raise ValueError(f"Path is outside project root: {self._get_relative_path(resolved_path)}")

        return resolved_path

    def _get_relative_path(self, path: Path) -> str:
        """
        Get path relative to project root for display purposes.

        Args:
            path: Absolute path to convert

        Returns:
            String representation of path relative to project root,
            or absolute path if not within project
        """
        try:
            return str(path.relative_to(self.project_root))
        except ValueError:
            # Path is outside project root, return as-is
            return str(path)

    def _sanitize_error_message(self, error: str) -> str:
        """
        Sanitize error messages to show only relative paths.

        This prevents information disclosure of full system paths.

        Args:
            error: Original error message

        Returns:
            Sanitized error message with relative paths
        """
        # Replace any occurrence of the project root with a relative indicator
        sanitized = error.replace(str(self.project_root), "<project_root>")
        return sanitized

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
