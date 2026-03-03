from pathlib import Path
from datetime import datetime, timezone


class MemoryManager:
    def __init__(self, root: Path):
        self.root = root

    def _step_dir(self, step_idx: int) -> Path:
        return self.root / "steps" / f"step_{step_idx}"

    def write_step_full(self, step_idx: int, content: str, iteration: int = 0) -> Path:
        if iteration == 0:
            path = self._step_dir(step_idx) / "full.md"
        else:
            path = self._step_dir(step_idx) / f"iter_{iteration}" / "full.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
        return path

    def read_step(self, step_idx: int, full: bool = False) -> str:
        step_dir = self._step_dir(step_idx)
        if full:
            # find latest iter_N
            iters = sorted(step_dir.glob("iter_*/full.md"),
                           key=lambda p: int(p.parent.name.split("_")[1]))
            path = iters[-1] if iters else step_dir / "full.md"
        else:
            path = step_dir / "meta.md"
        return path.read_text() if path.exists() else ""

    def compress_step(self, step_idx: int, iteration: int, summary: str) -> None:
        path = self._step_dir(step_idx) / "meta.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(summary)

    def write_agent_context(self, agent_name: str, content: str) -> None:
        path = self.root / "agents" / agent_name / "context.md"
        path.parent.mkdir(parents=True, exist_ok=True)

        # Add timestamp header
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        full_content = f"<!-- Generated: {timestamp} -->\n\n{content}"

        path.write_text(full_content)

    def read_agent_context(self, agent_name: str) -> str:
        path = self.root / "agents" / agent_name / "context.md"
        return path.read_text() if path.exists() else ""

    def append_agent_history(self, agent_name: str, summary: str) -> None:
        path = self.root / "agents" / agent_name / "history.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        with path.open("a") as f:
            f.write(f"\n## {ts}\n\n{summary}\n")

    def load_agent_memory_bundle(self, agent_name: str, current_step: int, total_steps: int) -> str:
        parts = []
        parts.append(self.read_agent_context(agent_name))
        history = self.root / "agents" / agent_name / "history.md"
        parts.append(history.read_text() if history.exists() else "")
        parts.append(self.read_step(current_step, full=True))
        for n in range(total_steps):
            if n != current_step:
                parts.append(self.read_step(n, full=False))
        return "\n".join(parts)

    def write_workflow_state(self, content: str) -> None:
        path = self.root / "workflow.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)

    def read_workflow_state(self) -> str:
        path = self.root / "workflow.md"
        return path.read_text() if path.exists() else ""

    def write_baseline_output(self, output: str, execution_time: float) -> None:
        """Save baseline program output and metrics."""
        content = f"""# Baseline Output

**Execution Time:** {execution_time:.4f}s

## Output
```
{output}
```
"""
        path = self.root / "baseline_output.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)

    def write_optimized_output(self, output: str, execution_time: float) -> None:
        """Save optimized program output and metrics."""
        content = f"""# Optimized Output

**Execution Time:** {execution_time:.4f}s

## Output
```
{output}
```
"""
        path = self.root / "optimized_output.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)

    def read_baseline_output(self) -> str:
        """Read baseline output."""
        path = self.root / "baseline_output.md"
        return path.read_text() if path.exists() else ""

    def read_optimized_output(self) -> str:
        """Read optimized output."""
        path = self.root / "optimized_output.md"
        return path.read_text() if path.exists() else ""
