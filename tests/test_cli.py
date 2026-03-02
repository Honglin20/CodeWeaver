import sys
from pathlib import Path
from unittest.mock import patch, MagicMock
from codeweaver.cli import _dispatch


def test_help_command(capsys):
    _dispatch("/help")
    captured = capsys.readouterr()
    assert "Commands" in captured.out


def test_unknown_command(capsys):
    _dispatch("/unknown")
    captured = capsys.readouterr()
    assert "Unknown" in captured.out


def test_list_command_no_runs(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _dispatch("/list")  # should not raise


def test_tools_command(capsys):
    _dispatch("/tools")
    captured = capsys.readouterr()
    assert "select" in captured.out
    assert "run_command" in captured.out


def test_status_no_runs(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _dispatch("/status")  # should not raise


def test_memory_no_dir(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _dispatch("/memory 1")  # should not raise


def test_agents_no_dir(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _dispatch("/agents")  # should not raise


def test_run_missing_name(capsys):
    _dispatch("/run")
    captured = capsys.readouterr()
    assert "Usage" in captured.out


def test_resume_missing_id(capsys):
    _dispatch("/resume")
    captured = capsys.readouterr()
    assert "Usage" in captured.out


def test_quit_exits():
    with patch("sys.exit") as mock_exit:
        _dispatch("/quit")
        mock_exit.assert_called_once_with(0)


def test_exit_exits():
    with patch("sys.exit") as mock_exit:
        _dispatch("/exit")
        mock_exit.assert_called_once_with(0)
