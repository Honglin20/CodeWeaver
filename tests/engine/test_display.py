import pytest
from codeweaver.engine.display import ExecutionDisplay, StepInfo


def test_display_initialization():
    display = ExecutionDisplay()
    assert display is not None


def test_start_workflow_shows_overview():
    display = ExecutionDisplay()
    steps = [
        StepInfo(index=1, goal="Analyze project", agents=["structure-agent"]),
        StepInfo(index=2, goal="Get user input", agents=["interact-agent"])
    ]
    # Should not raise
    display.start_workflow("test-workflow", steps)


def test_start_step_shows_progress():
    display = ExecutionDisplay()
    display.start_step(1, "Analyze project", ["structure-agent"])
    # Should not raise


def test_complete_step_shows_summary():
    display = ExecutionDisplay()
    display.complete_step(1, "Project analyzed successfully")
    # Should not raise
