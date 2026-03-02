import sys
from pathlib import Path
import typer
import yaml
from rich.console import Console
from rich.table import Table
from prompt_toolkit import PromptSession
from prompt_toolkit.completion import WordCompleter

from codeweaver.engine.executor import WorkflowExecutor
from codeweaver.parser.workflow import parse_workflow
from codeweaver.parser.agent import load_agent_registry
from codeweaver.generator.analyzer import WorkflowAnalyzer
from codeweaver.generator.agent_gen import generate_agent
from codeweaver.generator.reviewer import review_agents

app = typer.Typer()
console = Console()

COMMANDS = ["/list", "/run", "/resume", "/agents", "/agents new", "/tools", "/memory", "/status", "/analyze", "/help", "/quit", "/exit"]
TOOLS = ["select", "run_command", "read_file", "list_files", "debugger"]


def _cw_root() -> Path:
    return Path.cwd() / ".codeweaver"


def _load_runs() -> dict:
    runs_file = _cw_root() / "runs.yaml"
    if not runs_file.exists():
        return {}
    return yaml.safe_load(runs_file.read_text()) or {}


def _find_workflow_file(name: str) -> Path | None:
    # If it's already a path that exists, use it
    p = Path(name)
    if p.exists() and p.suffix == ".md":
        return p

    # Otherwise search in current dir and .codeweaver
    for search_dir in [Path.cwd(), _cw_root()]:
        for f in search_dir.glob("*.md"):
            if f.stem == name or f.name == name:
                return f
    return None


def _mock_llm_fn(messages: list[dict]) -> str:
    """Real LLM function using Kimi API."""
    import os
    import litellm

    # Use Kimi API
    api_key = "sk-IA0OXgtva7EmahBVdzkCJgcJxnmo4ja6O0M0M146HniteI3m"
    api_base = "https://api.moonshot.cn/v1"

    try:
        response = litellm.completion(
            model="moonshot/moonshot-v1-8k",
            messages=messages,
            api_key=api_key,
            api_base=api_base,
        )
        return response.choices[0].message.content
    except Exception as e:
        console.print(f"[red]LLM API error: {e}[/red]")
        raise


def _run_analyze(wf_file: Path, auto: bool) -> None:
    """Analyze workflow, generate missing agents, optionally review."""
    from rich.panel import Panel

    # Parse workflow
    wf = parse_workflow(wf_file.read_text())

    # Load agent registry
    agents_dir = _cw_root() / "agents"
    agents_dir.mkdir(parents=True, exist_ok=True)
    registry = load_agent_registry(agents_dir) if agents_dir.exists() else {}

    # Create analyzer with mock LLM
    analyzer = WorkflowAnalyzer(registry=registry, llm_fn=_mock_llm_fn)

    # Analyze workflow
    tree = analyzer.analyze(wf)

    # Display analysis tree
    md_content = tree.to_markdown()
    console.print(Panel(md_content, title="Workflow Analysis", border_style="cyan"))

    # Write analysis to file
    analysis_file = _cw_root() / "workflow_analysis.md"
    analysis_file.write_text(md_content)
    console.print(f"[green]Analysis written to {analysis_file}[/green]")

    # Generate agents for gaps
    if tree.gaps:
        console.print(f"\n[yellow]Found {len(tree.gaps)} gaps. Generating agents...[/yellow]")
        generated_agents = []
        for gap in tree.gaps:
            agent = generate_agent(gap, _mock_llm_fn, agents_dir)
            generated_agents.append(agent)
            console.print(f"[green]Generated: {agent.name}[/green]")

        # Review agents if not auto
        if not auto:
            accepted = review_agents(generated_agents, agents_dir)
            console.print(f"\n[green]Accepted {len(accepted)} agents[/green]")
    else:
        console.print("\n[green]No gaps found. All steps have matching agents.[/green]")



def _dispatch(text: str) -> None:
    parts = text.split()
    cmd = parts[0]

    if cmd == "/help":
        console.print("[bold]Commands:[/bold]")
        for c in COMMANDS:
            console.print(f"  {c}")

    elif cmd == "/list":
        runs = _load_runs()
        if not runs:
            console.print("[yellow]No runs found.[/yellow]")
            return
        t = Table("thread_id", "workflow", "status", "started_at")
        for tid, info in runs.items():
            t.add_row(tid, info.get("workflow", ""), info.get("status", ""), info.get("started_at", ""))
        console.print(t)

    elif cmd == "/run":
        if len(parts) < 2:
            console.print("[red]Usage: /run <workflow_name>[/red]")
            return
        name = parts[1]
        wf_file = _find_workflow_file(name)
        if not wf_file:
            console.print(f"[red]Workflow file not found: {name}[/red]")
            return
        wf = parse_workflow(wf_file.read_text())
        executor = WorkflowExecutor(_cw_root())
        tid = executor.run(wf)
        console.print(f"[green]Completed. thread_id: {tid}[/green]")

    elif cmd == "/resume":
        if len(parts) < 2:
            console.print("[red]Usage: /resume <thread_id>[/red]")
            return
        tid = parts[1]
        runs = _load_runs()
        if tid not in runs:
            console.print(f"[red]No run found for: {tid}[/red]")
            return
        wf_name = runs[tid].get("workflow", "")
        wf_file = _find_workflow_file(wf_name)
        if not wf_file:
            console.print(f"[red]Workflow file not found: {wf_name}[/red]")
            return
        wf = parse_workflow(wf_file.read_text())
        executor = WorkflowExecutor(_cw_root())
        executor.resume(tid, wf)
        console.print(f"[green]Resumed and completed: {tid}[/green]")

    elif cmd == "/agents":
        agents_dir = _cw_root() / "agents"
        if not agents_dir.exists():
            console.print("[yellow]No agents directory found.[/yellow]")
            return
        registry = load_agent_registry(agents_dir)
        if not registry:
            console.print("[yellow]No agents found.[/yellow]")
            return
        t = Table("name", "description")
        for agent in registry.values():
            t.add_row(agent.name, agent.description)
        console.print(t)

    elif cmd == "/tools":
        t = Table("tool")
        for tool in TOOLS:
            t.add_row(tool)
        console.print(t)

    elif cmd == "/memory":
        if len(parts) < 2:
            console.print("[red]Usage: /memory <step>[/red]")
            return
        step = parts[1]
        step_dir = _cw_root() / "memory" / "steps" / f"step_{step}"
        if not step_dir.exists():
            console.print(f"[yellow]No memory for step {step}[/yellow]")
            return
        for f in step_dir.iterdir():
            console.print(f"[bold]{f.name}[/bold]")
            console.print(f.read_text())

    elif cmd == "/status":
        runs = _load_runs()
        if not runs:
            console.print("[yellow]No runs.[/yellow]")
            return
        last_tid = list(runs.keys())[-1]
        info = runs[last_tid]
        console.print(f"thread_id: {last_tid}  workflow: {info.get('workflow')}  status: {info.get('status')}")

    elif cmd == "/analyze":
        if len(parts) < 2:
            console.print("[red]Usage: /analyze <workflow_name>[/red]")
            return
        name = parts[1]
        wf_file = _find_workflow_file(name)
        if not wf_file:
            console.print(f"[red]Workflow file not found: {name}[/red]")
            return
        _run_analyze(wf_file, auto=False)

    elif cmd in ("/quit", "/exit"):
        sys.exit(0)

    else:
        console.print("[red]Unknown command[/red]")


def _repl() -> None:
    completer = WordCompleter(COMMANDS, pattern=r"[/\w]+")
    session = PromptSession(completer=completer)
    console.print("[bold cyan]CodeWeaver[/bold cyan] — type /help for commands")

    while True:
        try:
            text = session.prompt("> ").strip()
        except KeyboardInterrupt:
            console.print("\n[yellow]Use /quit to exit[/yellow]")
            continue
        except EOFError:
            break

        if not text:
            continue
        _dispatch(text)


@app.command()
def run(workflow: str):
    """Parse workflow md, create executor, run."""
    wf_file = _find_workflow_file(workflow)
    if not wf_file:
        console.print(f"[red]Workflow file not found: {workflow}[/red]")
        raise typer.Exit(1)
    wf = parse_workflow(wf_file.read_text())
    executor = WorkflowExecutor(_cw_root())
    tid = executor.run(wf)
    console.print(f"[green]Completed. thread_id: {tid}[/green]")


@app.command()
def resume(thread_id: str):
    """Load runs.yaml, find workflow, resume."""
    runs = _load_runs()
    if thread_id not in runs:
        console.print(f"[red]No run found for: {thread_id}[/red]")
        raise typer.Exit(1)
    wf_name = runs[thread_id].get("workflow", "")
    wf_file = _find_workflow_file(wf_name)
    if not wf_file:
        console.print(f"[red]Workflow file not found: {wf_name}[/red]")
        raise typer.Exit(1)
    wf = parse_workflow(wf_file.read_text())
    executor = WorkflowExecutor(_cw_root())
    executor.resume(thread_id, wf)
    console.print(f"[green]Resumed and completed: {thread_id}[/green]")


@app.command()
def index(
    project_dir: str,
    llm: bool = typer.Option(True, "--llm/--no-llm", help="Use LLM to generate symbol descriptions")
):
    """Build code database for a Python project with optional LLM descriptions."""
    from codeweaver.code_db.builder import build_index
    from codeweaver.llm import create_kimi_llm

    project_path = Path(project_dir)
    if not project_path.exists():
        console.print(f"[red]Directory not found: {project_dir}[/red]")
        raise typer.Exit(1)

    # Use real LLM if --llm flag is set
    llm_fn = create_kimi_llm() if llm else None

    if llm:
        console.print(f"[cyan]Indexing {project_dir} with LLM descriptions...[/cyan]")
    else:
        console.print(f"[cyan]Indexing {project_dir} (no LLM)...[/cyan]")

    build_index(project_path, _cw_root(), llm_describe_fn=llm_fn)

    code_db_path = _cw_root() / "code_db"
    console.print(f"[green]✓ Index built at {code_db_path}[/green]")


@app.command()
def analyze(workflow: str, auto: bool = typer.Option(False, "--auto")):
    """Analyze workflow, generate missing agents, optionally run."""
    wf_file = _find_workflow_file(workflow)
    if not wf_file:
        console.print(f"[red]Workflow file not found: {workflow}[/red]")
        raise typer.Exit(1)
    _run_analyze(wf_file, auto=auto)


def main():
    if len(sys.argv) > 1:
        app()
    else:
        _repl()
