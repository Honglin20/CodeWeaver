import pytest
import yaml
from pathlib import Path
from unittest.mock import patch, MagicMock
from codeweaver.engine.executor import WorkflowExecutor
from codeweaver.parser.workflow import WorkflowDef, StepDef


def make_workflow():
    step = StepDef(index=0, title="Do something", raw_text="Do something")
    return WorkflowDef(name="test-workflow", description="", entry_command=None, steps=[step])


def make_executor(tmp_path):
    return WorkflowExecutor(codeweaver_root=tmp_path, llm_fn=lambda msgs: "summary")


@patch("codeweaver.engine.executor.SqliteSaver")
@patch("codeweaver.engine.executor.compile_graph")
@patch("codeweaver.engine.executor.Orchestrator")
def test_new_run_creates_checkpoint(mock_orch_cls, mock_compile, mock_saver, tmp_path):
    compiled = MagicMock()
    mock_compile.return_value.compile.return_value = compiled
    mock_orch_cls.return_value.analyze.return_value = []

    executor = make_executor(tmp_path)
    thread_id = executor.run(make_workflow(), thread_id="abc-123")

    assert thread_id == "abc-123"
    compiled.invoke.assert_called_once()

    runs = yaml.safe_load((tmp_path / "runs.yaml").read_text())
    assert "abc-123" in runs
    assert runs["abc-123"]["status"] == "completed"
    assert runs["abc-123"]["workflow"] == "test-workflow"


@patch("codeweaver.engine.executor.SqliteSaver")
@patch("codeweaver.engine.executor.compile_graph")
@patch("codeweaver.engine.executor.Orchestrator")
def test_resume_continues_from_last_step(mock_orch_cls, mock_compile, mock_saver, tmp_path):
    compiled = MagicMock()
    mock_compile.return_value.compile.return_value = compiled
    mock_orch_cls.return_value.analyze.return_value = []

    executor = make_executor(tmp_path)
    executor._save_run("tid-1", "test-workflow", "interrupted")

    executor.resume("tid-1", make_workflow())

    compiled.invoke.assert_called_once_with(None, config={"configurable": {"thread_id": "tid-1"}})

    runs = executor.list_runs()
    assert runs["tid-1"]["status"] == "completed"


def test_interrupted_run_listed_in_runs_yaml(tmp_path):
    executor = make_executor(tmp_path)
    executor._save_run("tid-2", "test-workflow", "interrupted")

    runs = executor.list_runs()
    assert "tid-2" in runs
    assert runs["tid-2"]["status"] == "interrupted"


def test_completed_run_not_resumable(tmp_path):
    executor = make_executor(tmp_path)
    executor._save_run("tid-3", "test-workflow", "completed")

    with pytest.raises(ValueError, match="already completed"):
        executor.resume("tid-3", make_workflow())


@patch("codeweaver.engine.executor.SqliteSaver")
@patch("codeweaver.engine.executor.compile_graph")
@patch("codeweaver.engine.executor.Orchestrator")
def test_executor_uses_display(mock_orch_cls, mock_compile, mock_saver, tmp_path):
    from codeweaver.engine.display import ExecutionDisplay
    from unittest.mock import Mock

    display = Mock(spec=ExecutionDisplay)
    executor = WorkflowExecutor(tmp_path, llm_fn=lambda msgs, tools=None: "test")
    executor.display = display

    compiled = MagicMock()
    mock_compile.return_value.compile.return_value = compiled
    mock_orch_cls.return_value.analyze.return_value = []

    workflow = WorkflowDef(
        name="test",
        description="test",
        entry_command=None,
        steps=[StepDef(index=1, title="Do something", raw_text="@test-agent: do something", explicit_agents=["test-agent"])]
    )

    executor.run(workflow)

    # Verify display methods were called
    display.start_workflow.assert_called_once()
    display.complete_workflow.assert_called_once()
