from dataclasses import dataclass
from rich.console import Console
from rich.table import Table


@dataclass
class StepInfo:
    index: int
    goal: str
    agents: list[str]


class ExecutionDisplay:
    def __init__(self, console: Console = None):
        self.console = console or Console()
        self.current_step = 0
        self.total_steps = 0

    def start_workflow(self, name: str, steps: list[StepInfo]) -> None:
        self.total_steps = len(steps)
        self.console.print(f"\n[bold cyan]Workflow:[/bold cyan] {name}")
        self.console.print("─" * 80)

        table = Table(show_header=False, box=None, padding=(0, 2))
        for step in steps:
            agents_str = f"[dim]({', '.join(step.agents)})[/dim]" if step.agents else ""
            table.add_row(f"[cyan]{step.index}.[/cyan]", step.goal, agents_str)
        self.console.print(table)
        self.console.print()

    def start_step(self, step_num: int, goal: str, agents: list[str]) -> None:
        self.current_step = step_num
        agents_str = f" [{', '.join(agents)}]" if agents else ""
        self.console.print(f"\n[cyan]Step {step_num}/{self.total_steps}:[/cyan] {goal}{agents_str}")

    def report_tool_call(self, tool_name: str, args_preview: str) -> None:
        self.console.print(f"  [dim]→ {tool_name}({args_preview})[/dim]")

    def report_tool_result(self, tool_name: str, success: bool, error: str = None) -> None:
        if success:
            self.console.print(f"  [dim green]✓ {tool_name}[/dim green]")
        else:
            self.console.print(f"  [yellow]⚠ {tool_name}: {error}[/yellow]")

    def complete_step(self, step_num: int, summary: str) -> None:
        self.console.print(f"[green]✓ Step {step_num} complete:[/green] {summary}")

    def complete_workflow(self, success: bool, error: str = None) -> None:
        if success:
            self.console.print(f"\n[bold green]✓ Workflow completed[/bold green]")
        else:
            self.console.print(f"\n[bold red]✗ Workflow failed:[/bold red] {error}")

    def update_progress(self, current: int, total: int) -> None:
        pass
