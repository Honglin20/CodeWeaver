import pytest
from unittest.mock import MagicMock, patch
from langgraph.types import Command
from codeweaver.tools.interactive import InteractiveToolHandler
from codeweaver.tools.executor import ToolExecutor, ToolResult


class TestInteractiveToolHandler:
    """Tests for InteractiveToolHandler class."""

    def test_handle_select_creates_command_with_interrupt(self):
        """Test that handle_select returns a Command with interrupt data."""
        handler = InteractiveToolHandler()

        result = handler.handle_select(
            prompt="Choose an option:",
            options=["Option A", "Option B", "Option C"]
        )

        assert isinstance(result, Command)
        assert result.graph == Command.PARENT
        assert "__interrupt__" in result.update

        interrupt_data = result.update["__interrupt__"]
        assert interrupt_data["type"] == "select"
        assert interrupt_data["prompt"] == "Choose an option:"
        assert interrupt_data["options"] == ["Option A", "Option B", "Option C"]

    def test_handle_select_validates_minimum_options(self):
        """Test that handle_select requires at least 2 options."""
        handler = InteractiveToolHandler()

        # Test with 0 options
        with pytest.raises(ValueError, match="at least 2 options"):
            handler.handle_select(prompt="Choose:", options=[])

        # Test with 1 option
        with pytest.raises(ValueError, match="at least 2 options"):
            handler.handle_select(prompt="Choose:", options=["Only one"])

    def test_handle_select_accepts_exactly_two_options(self):
        """Test that handle_select accepts exactly 2 options."""
        handler = InteractiveToolHandler()

        result = handler.handle_select(
            prompt="Yes or No?",
            options=["Yes", "No"]
        )

        assert isinstance(result, Command)
        assert len(result.update["__interrupt__"]["options"]) == 2

    def test_handle_select_validates_empty_prompt(self):
        """Test that handle_select requires a non-empty prompt."""
        handler = InteractiveToolHandler()

        with pytest.raises(ValueError, match="prompt cannot be empty"):
            handler.handle_select(prompt="", options=["A", "B"])

        with pytest.raises(ValueError, match="prompt cannot be empty"):
            handler.handle_select(prompt="   ", options=["A", "B"])

    def test_handle_select_validates_option_types(self):
        """Test that handle_select validates option types."""
        handler = InteractiveToolHandler()

        # Options must be strings
        with pytest.raises(TypeError, match="must be strings"):
            handler.handle_select(prompt="Choose:", options=["A", 123, "C"])


class TestToolExecutorIntegration:
    """Tests for tool_select integration with ToolExecutor."""

    @pytest.fixture
    def executor(self, tmp_path):
        """Create a ToolExecutor instance."""
        return ToolExecutor(project_root=str(tmp_path))

    def test_tool_executor_has_tool_select(self, executor):
        """Test that ToolExecutor can execute tool_select."""
        result = executor.execute(
            "tool_select",
            prompt="Choose an option:",
            options=["Option A", "Option B"]
        )

        # tool_select returns a Command, not a ToolResult
        # The executor should handle this specially
        assert isinstance(result, (Command, ToolResult))

    def test_tool_select_in_schemas(self, executor):
        """Test that tool_select appears in OpenAI function schemas."""
        schemas = executor.get_tool_schemas()

        # Should now have 4 tools: run_command, read_file, list_files, tool_select
        assert len(schemas) == 4

        # Find tool_select schema
        tool_select_schema = next(
            (s for s in schemas if s["function"]["name"] == "tool_select"),
            None
        )

        assert tool_select_schema is not None
        assert tool_select_schema["type"] == "function"

        func = tool_select_schema["function"]
        assert func["name"] == "tool_select"
        assert "present" in func["description"].lower() or "choice" in func["description"].lower()

        params = func["parameters"]
        assert params["type"] == "object"
        assert "prompt" in params["properties"]
        assert "options" in params["properties"]
        assert params["properties"]["options"]["type"] == "array"
        assert "prompt" in params["required"]
        assert "options" in params["required"]

    def test_tool_select_schema_describes_minimum_options(self, executor):
        """Test that tool_select schema mentions minimum options requirement."""
        schemas = executor.get_tool_schemas()
        tool_select_schema = next(
            s for s in schemas if s["function"]["name"] == "tool_select"
        )

        options_prop = tool_select_schema["function"]["parameters"]["properties"]["options"]
        # Should have minItems constraint
        assert "minItems" in options_prop
        assert options_prop["minItems"] == 2

    def test_tool_executor_validates_tool_select_options(self, executor):
        """Test that executor validates tool_select options."""
        # Should fail with less than 2 options
        result = executor.execute(
            "tool_select",
            prompt="Choose:",
            options=["Only one"]
        )

        assert isinstance(result, ToolResult)
        assert result.success is False
        assert "at least 2 options" in result.error

    def test_tool_executor_returns_command_for_valid_select(self, executor):
        """Test that executor returns Command for valid tool_select."""
        result = executor.execute(
            "tool_select",
            prompt="Choose an option:",
            options=["A", "B", "C"]
        )

        # For interactive tools, executor should return the Command directly
        # or wrap it in a special way
        assert isinstance(result, (Command, ToolResult))

        if isinstance(result, Command):
            assert result.graph == Command.PARENT
            assert "__interrupt__" in result.update
        elif isinstance(result, ToolResult):
            # If wrapped in ToolResult, the output should be the Command
            assert result.success is True
            assert isinstance(result.output, Command)
