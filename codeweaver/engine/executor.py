from pathlib import Path
from uuid import uuid4
from datetime import datetime
import yaml
from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from langgraph.checkpoint.sqlite import SqliteSaver
from codeweaver.engine.compiler import compile_graph, WorkflowState
from codeweaver.engine.orchestrator import Orchestrator
from codeweaver.parser.agent import load_agent_registry
from codeweaver.memory.manager import MemoryManager

console = Console()


class WorkflowExecutor:
    def __init__(self, codeweaver_root: Path, llm_fn=None):
        self.root = codeweaver_root
        self.llm_fn = llm_fn
        self.checkpoints_db = str(codeweaver_root / "checkpoints.db")
        self.runs_file = codeweaver_root / "runs.yaml"

    def run(self, workflow_def, thread_id: str | None = None) -> str:
        """Start a new workflow run. Returns thread_id."""
        thread_id = thread_id or str(uuid4())

        console.print(f"\n[bold cyan]Starting workflow:[/bold cyan] {workflow_def.name}")
        console.print(f"[dim]Thread ID: {thread_id}[/dim]\n")

        agents_dir = self.root / "agents"
        registry = load_agent_registry(agents_dir) if agents_dir.exists() else {}

        memory = MemoryManager(self.root / "memory")

        console.print("[yellow]Analyzing workflow and generating execution plan...[/yellow]")
        orchestrator = Orchestrator(registry, memory, self.llm_fn)
        plans = orchestrator.analyze(workflow_def)

        console.print(f"[green]✓[/green] Generated {len(plans)} execution steps\n")

        # Determine project root (parent of .codeweaver directory)
        project_root = str(self.root.parent)

        graph = compile_graph(
            plans, registry, memory, self.llm_fn,
            workflow_steps=workflow_def.steps,
            project_root=project_root
        )

        console.print("[bold]Executing workflow...[/bold]\n")

        with SqliteSaver.from_conn_string(self.checkpoints_db) as checkpointer:
            compiled = graph.compile(checkpointer=checkpointer)

            initial_state = WorkflowState(
                current_step=0,
                iteration=0,
                status="running",
                memory_root=str(self.root / "memory"),
                error_count=0,
                task_description="",
            )
            config = {"configurable": {"thread_id": thread_id}}

            # Execute with progress tracking
            for i, plan in enumerate(plans, 1):
                console.print(f"[cyan]Step {i}/{len(plans)}:[/cyan] {plan.goal}")
                if plan.agents:
                    console.print(f"[dim]  Agents: {', '.join(plan.agents)}[/dim]")

            compiled.invoke(initial_state, config=config)

        console.print(f"\n[bold green]✓ Workflow completed successfully[/bold green]")
        self._save_run(thread_id, workflow_def.name, "completed")
        return thread_id

    def resume(self, thread_id: str, workflow_def) -> None:
        """Resume an interrupted workflow from checkpoint."""
        runs = self._load_runs()
        if thread_id not in runs:
            raise ValueError(f"No run found for thread_id: {thread_id}")
        if runs[thread_id]["status"] == "completed":
            raise ValueError(f"Run {thread_id} is already completed")

        agents_dir = self.root / "agents"
        registry = load_agent_registry(agents_dir) if agents_dir.exists() else {}

        memory = MemoryManager(self.root / "memory")
        orchestrator = Orchestrator(registry, memory, self.llm_fn)
        plans = orchestrator.analyze(workflow_def)

        # Determine project root (parent of .codeweaver directory)
        project_root = str(self.root.parent)

        graph = compile_graph(
            plans, registry, memory, self.llm_fn,
            workflow_steps=workflow_def.steps,
            project_root=project_root
        )
        with SqliteSaver.from_conn_string(self.checkpoints_db) as checkpointer:
            compiled = graph.compile(checkpointer=checkpointer)

            config = {"configurable": {"thread_id": thread_id}}
            compiled.invoke(None, config=config)

        self._save_run(thread_id, workflow_def.name, "completed")

    def list_runs(self) -> dict:
        """Return runs.yaml contents."""
        return self._load_runs()

    def _load_runs(self) -> dict:
        if not self.runs_file.exists():
            return {}
        return yaml.safe_load(self.runs_file.read_text()) or {}

    def _save_run(self, thread_id: str, workflow_name: str, status: str) -> None:
        runs = self._load_runs()
        runs[thread_id] = {
            "workflow": workflow_name,
            "started_at": datetime.now().isoformat(),
            "status": status,
        }
        self.runs_file.write_text(yaml.dump(runs))
