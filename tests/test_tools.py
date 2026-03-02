import pytest
from codeweaver.tools.filesystem import run_command, read_file, list_files


def test_run_command_captures_output(tmp_path):
    result = run_command("echo hello", cwd=str(tmp_path))
    assert result["stdout"].strip() == "hello"
    assert result["returncode"] == 0


def test_run_command_timeout_raises(tmp_path):
    import subprocess
    with pytest.raises(subprocess.TimeoutExpired):
        run_command("sleep 10", cwd=str(tmp_path), timeout=1)


def test_run_command_no_shell_injection(tmp_path):
    # shell=False: ";" is a literal arg to echo, not a shell operator
    # output is "hello; echo world" on one line — proves no second command ran
    result = run_command("echo hello; echo world", cwd=str(tmp_path))
    assert result["returncode"] == 0
    assert ";" in result["stdout"]          # ";" passed as literal
    assert result["stdout"].count("\n") <= 1  # single line output, not two commands


def test_read_file_returns_content(tmp_path):
    f = tmp_path / "test.txt"
    f.write_text("hello world")
    assert read_file(str(f)) == "hello world"


def test_list_files_respects_pattern(tmp_path):
    (tmp_path / "a.py").write_text("")
    (tmp_path / "b.txt").write_text("")
    files = list_files(str(tmp_path), "*.py")
    assert any("a.py" in f for f in files)
    assert not any("b.txt" in f for f in files)


def test_tool_select_imports():
    from codeweaver.tools import select  # noqa: F401


def test_insert_breakpoint_imports():
    from codeweaver.tools import debugger  # noqa: F401
