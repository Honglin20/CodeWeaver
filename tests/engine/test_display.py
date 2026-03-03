import pytest
from codeweaver.engine.display import ExecutionDisplay, StepInfo


def test_display_initialization():
    display = ExecutionDisplay()
    assert display is not None
    assert display.current_step == 0
    assert display.total_steps == 0


def test_start_workflow_shows_overview(capsys):
    display = ExecutionDisplay()
    steps = [
        StepInfo(index=1, goal="Analyze project", agents=["structure-agent"]),
        StepInfo(index=2, goal="Get user input", agents=["interact-agent"])
    ]
    display.start_workflow("test-workflow", steps)

    captured = capsys.readouterr()
    assert "Workflow:" in captured.out
    assert "test-workflow" in captured.out
    assert "Analyze project" in captured.out
    assert "Get user input" in captured.out
    assert "structure-agent" in captured.out
    assert "interact-agent" in captured.out
    assert display.total_steps == 2


def test_start_workflow_with_empty_agents(capsys):
    display = ExecutionDisplay()
    steps = [
        StepInfo(index=1, goal="Simple task")
    ]
    display.start_workflow("test-workflow", steps)

    captured = capsys.readouterr()
    assert "Simple task" in captured.out
    assert display.total_steps == 1


def test_start_step_shows_progress(capsys):
    display = ExecutionDisplay()
    display.total_steps = 3
    display.start_step(1, "Analyze project", ["structure-agent"])

    captured = capsys.readouterr()
    assert "Step 1/3:" in captured.out
    assert "Analyze project" in captured.out
    # Note: Rich console strips markup, so we just verify the step info is shown
    assert display.current_step == 1


def test_start_step_with_empty_agents(capsys):
    display = ExecutionDisplay()
    display.total_steps = 2
    display.start_step(1, "Simple task", [])

    captured = capsys.readouterr()
    assert "Step 1/2:" in captured.out
    assert "Simple task" in captured.out


def test_report_tool_call(capsys):
    display = ExecutionDisplay()
    display.report_tool_call("read_file", "path='test.py'")

    captured = capsys.readouterr()
    assert "read_file" in captured.out
    assert "path='test.py'" in captured.out


def test_report_tool_result_success(capsys):
    display = ExecutionDisplay()
    display.report_tool_result("read_file", success=True)

    captured = capsys.readouterr()
    assert "✓" in captured.out
    assert "read_file" in captured.out


def test_report_tool_result_failure(capsys):
    display = ExecutionDisplay()
    display.report_tool_result("read_file", success=False, error="File not found")

    captured = capsys.readouterr()
    assert "⚠" in captured.out
    assert "read_file" in captured.out
    assert "File not found" in captured.out


def test_complete_step_shows_summary(capsys):
    display = ExecutionDisplay()
    display.complete_step(1, "Project analyzed successfully")

    captured = capsys.readouterr()
    assert "✓ Step 1 complete:" in captured.out
    assert "Project analyzed successfully" in captured.out


def test_complete_workflow_success(capsys):
    display = ExecutionDisplay()
    display.complete_workflow(success=True)

    captured = capsys.readouterr()
    assert "✓ Workflow completed" in captured.out


def test_complete_workflow_failure(capsys):
    display = ExecutionDisplay()
    display.complete_workflow(success=False, error="Agent failed")

    captured = capsys.readouterr()
    assert "✗ Workflow failed:" in captured.out
    assert "Agent failed" in captured.out
