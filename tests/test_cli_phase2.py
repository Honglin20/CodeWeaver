from unittest.mock import patch, MagicMock
from pathlib import Path
from codeweaver.cli import _dispatch


def test_analyze_command_dispatches(tmp_path, monkeypatch):
    """Test /analyze command without arguments shows usage."""
    monkeypatch.chdir(tmp_path)
    # Create .codeweaver dir to avoid errors
    (tmp_path / ".codeweaver").mkdir()
    # Should not raise even with no workflow file
    _dispatch("/analyze")  # missing arg → prints usage, no crash


def test_analyze_with_workflow_file(tmp_path, monkeypatch):
    """Test /analyze command with a valid workflow file."""
    monkeypatch.chdir(tmp_path)
    # Create .codeweaver dir
    (tmp_path / ".codeweaver").mkdir()

    # Create workflow file
    wf_file = tmp_path / "test.md"
    wf_file.write_text("---\nname: test\ndescription: test\n---\n## Step 1\ndo something\n")

    with patch("codeweaver.cli.WorkflowAnalyzer") as mock_analyzer:
        mock_tree = MagicMock()
        mock_tree.gaps = []
        mock_tree.to_markdown.return_value = "# Analysis"
        mock_analyzer.return_value.analyze.return_value = mock_tree

        _dispatch(f"/analyze test")
        mock_analyzer.return_value.analyze.assert_called_once()
