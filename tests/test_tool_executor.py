import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from codeweaver.tools.executor import ToolExecutor, ToolResult


@pytest.fixture
def project_root(tmp_path):
    """Create a temporary project root with some test files."""
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "main.py").write_text("print('hello')")
    (tmp_path / "data.txt").write_text("test data")
    return tmp_path


@pytest.fixture
def executor(project_root):
    """Create a ToolExecutor instance."""
    return ToolExecutor(project_root=str(project_root))


def test_tool_executor_runs_command(executor, project_root):
    """Test that run_command executes successfully."""
    result = executor.execute("run_command", cmd="echo hello", cwd=str(project_root))

    assert isinstance(result, ToolResult)
    assert result.success is True
    assert "hello" in result.output["stdout"]
    assert result.error is None


def test_tool_executor_reads_file(executor, project_root):
    """Test that read_file returns file contents."""
    result = executor.execute("read_file", path="data.txt")

    assert isinstance(result, ToolResult)
    assert result.success is True
    assert result.output == "test data"
    assert result.error is None


def test_tool_executor_lists_files(executor, project_root):
    """Test that list_files returns matching files."""
    result = executor.execute("list_files", directory="src", pattern="*.py")

    assert isinstance(result, ToolResult)
    assert result.success is True
    assert isinstance(result.output, list)
    assert any("main.py" in f for f in result.output)
    assert result.error is None


def test_tool_executor_handles_unknown_tool(executor):
    """Test that unknown tools return error."""
    result = executor.execute("unknown_tool", arg="value")

    assert isinstance(result, ToolResult)
    assert result.success is False
    assert result.output is None
    assert "Unknown tool" in result.error


def test_run_command_validates_cwd_within_project(executor, tmp_path):
    """Test that run_command rejects cwd outside project root."""
    outside_dir = tmp_path.parent / "outside"
    outside_dir.mkdir(exist_ok=True)

    result = executor.execute("run_command", cmd="echo test", cwd=str(outside_dir))

    assert result.success is False
    assert "outside project root" in result.error.lower()


def test_run_command_validates_cwd_traversal_attack(executor, project_root):
    """Test that run_command prevents directory traversal."""
    result = executor.execute("run_command", cmd="echo test", cwd=str(project_root / ".." / ".."))

    assert result.success is False
    assert "outside project root" in result.error.lower()


def test_read_file_resolves_relative_paths(executor, project_root):
    """Test that read_file resolves paths relative to project root."""
    result = executor.execute("read_file", path="data.txt")

    assert result.success is True
    assert result.output == "test data"


def test_read_file_prevents_directory_traversal(executor, project_root):
    """Test that read_file prevents reading outside project root."""
    result = executor.execute("read_file", path="../../../etc/passwd")

    assert result.success is False
    assert "outside project root" in result.error.lower()


def test_read_file_handles_nonexistent_file(executor):
    """Test that read_file handles missing files gracefully."""
    result = executor.execute("read_file", path="nonexistent.txt")

    assert result.success is False
    assert result.error is not None


def test_list_files_resolves_relative_paths(executor, project_root):
    """Test that list_files resolves directory relative to project root."""
    result = executor.execute("list_files", directory="src", pattern="*.py")

    assert result.success is True
    assert len(result.output) > 0


def test_list_files_prevents_directory_traversal(executor):
    """Test that list_files prevents listing outside project root."""
    result = executor.execute("list_files", directory="../..", pattern="*")

    assert result.success is False
    assert "outside project root" in result.error.lower()


def test_run_command_handles_timeout(executor, project_root):
    """Test that run_command handles timeouts gracefully."""
    result = executor.execute("run_command", cmd="sleep 10", cwd=str(project_root), timeout=1)

    assert result.success is False
    assert "timeout" in result.error.lower()


def test_get_tool_schemas_returns_openai_format(executor):
    """Test that get_tool_schemas returns OpenAI function calling format."""
    schemas = executor.get_tool_schemas()

    assert isinstance(schemas, list)
    assert len(schemas) == 3  # run_command, read_file, list_files

    for schema in schemas:
        assert schema["type"] == "function"
        assert "function" in schema
        assert "name" in schema["function"]
        assert "description" in schema["function"]
        assert "parameters" in schema["function"]
        assert schema["function"]["parameters"]["type"] == "object"
        assert "properties" in schema["function"]["parameters"]
        assert "required" in schema["function"]["parameters"]


def test_run_command_schema_structure(executor):
    """Test that run_command schema has correct structure."""
    schemas = executor.get_tool_schemas()
    run_cmd_schema = next(s for s in schemas if s["function"]["name"] == "run_command")

    params = run_cmd_schema["function"]["parameters"]
    assert "cmd" in params["properties"]
    assert "cwd" in params["properties"]
    assert "timeout" in params["properties"]
    assert "cmd" in params["required"]
    assert "cwd" in params["required"]


def test_read_file_schema_structure(executor):
    """Test that read_file schema has correct structure."""
    schemas = executor.get_tool_schemas()
    read_file_schema = next(s for s in schemas if s["function"]["name"] == "read_file")

    params = read_file_schema["function"]["parameters"]
    assert "path" in params["properties"]
    assert "path" in params["required"]


def test_list_files_schema_structure(executor):
    """Test that list_files schema has correct structure."""
    schemas = executor.get_tool_schemas()
    list_files_schema = next(s for s in schemas if s["function"]["name"] == "list_files")

    params = list_files_schema["function"]["parameters"]
    assert "directory" in params["properties"]
    assert "pattern" in params["properties"]
    assert "directory" in params["required"]


def test_tool_result_dataclass_structure():
    """Test ToolResult dataclass structure."""
    # Success case
    result = ToolResult(success=True, output="data", error=None)
    assert result.success is True
    assert result.output == "data"
    assert result.error is None

    # Error case
    result = ToolResult(success=False, output=None, error="error message")
    assert result.success is False
    assert result.output is None
    assert result.error == "error message"
