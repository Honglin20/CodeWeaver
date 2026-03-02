import shlex
import subprocess
import time
from pathlib import Path

def run_command(cmd: str, cwd: str, timeout: int = 60) -> dict:
    """
    Run a shell command safely (no shell=True).
    Returns {"stdout": str, "stderr": str, "returncode": int, "execution_time": float}
    Raises subprocess.TimeoutExpired if timeout exceeded.
    """
    args = shlex.split(cmd)
    start = time.time()
    result = subprocess.run(
        args,
        cwd=cwd,
        timeout=timeout,
        capture_output=True,
        text=True,
        shell=False,
    )
    elapsed = time.time() - start
    return {
        "stdout": result.stdout,
        "stderr": result.stderr,
        "returncode": result.returncode,
        "execution_time": elapsed,
    }

def read_file(path: str) -> str:
    return Path(path).read_text()

def list_files(directory: str, pattern: str = "**/*.py") -> list[str]:
    return [str(p) for p in Path(directory).glob(pattern)]
