# Execution Display Layer Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add execution display layer to provide real-time workflow progress feedback with step summaries, tool call visibility, and user-friendly error messages.

**Architecture:** Create ExecutionDisplay class to centralize all console output, integrate it into WorkflowExecutor and node_factory, suppress LiteLLM debug output, and ensure interactive tools properly pause execution.

**Tech Stack:** rich (progress bars, panels, console), litellm (LLM API), LangGraph (workflow engine)

---

## Task 1: Create ExecutionDisplay Class

**Files:**
- Create: `codeweaver/engine/display.py`
- Test: `tests/engine/test_display.py`

**Step 1: Write the failing test**

Create test file:

```python
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
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/engine/test_display.py -v`
Expected: FAIL with "No module named 'codeweaver.engine.display'"

**Step 3: Write minimal implementation**

Create `codeweaver/engine/display.py`:

```python
from dataclasses import dataclass
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
from rich.panel import Panel
from rich.table import Table


@dataclass
class StepInfo:
    index: int
    goal: str
    agents: list[str]


class ExecutionDisplay:
    def __init__(self, console: Console = None):
        self.console = console or Console()
        self.progress = None
        self.current_step = 0
        self.total_steps = 0

    def start_workflow(self, name: str, steps: list[StepInfo]) -> None:
        self.total_steps = len(steps)
        self.console.print(f"\n[bold cyan]Workflow:[/bold cyan] {name}")
        self.console.print("─" * 80)

        # Show overview
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
        pass  # Placeholder for progress bar updates
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/engine/test_display.py -v`
Expected: PASS (3 tests)

**Step 5: Commit**

```bash
git add codeweaver/engine/display.py tests/engine/test_display.py
git commit -m "feat: add ExecutionDisplay class for workflow feedback"
```

---

## Task 2: Integrate ExecutionDisplay into WorkflowExecutor

**Files:**
- Modify: `codeweaver/engine/executor.py`
- Test: `tests/engine/test_executor.py`

**Step 1: Write the failing test**

Add to `tests/engine/test_executor.py`:

```python
def test_executor_uses_display(tmp_path):
    from codeweaver.engine.display import ExecutionDisplay
    from codeweaver.parser.workflow import WorkflowDef, StepDef
    from unittest.mock import Mock

    display = Mock(spec=ExecutionDisplay)
    executor = WorkflowExecutor(tmp_path, llm_fn=lambda msgs, tools=None: "test")
    executor.display = display

    workflow = WorkflowDef(
        name="test",
        description="test",
        steps=[StepDef(index=1, raw_text="@test-agent: do something", agents=["test-agent"])]
    )

    executor.run(workflow)

    # Verify display methods were called
    display.start_workflow.assert_called_once()
    display.complete_workflow.assert_called_once()
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/engine/test_executor.py::test_executor_uses_display -v`
Expected: FAIL with "AttributeError: 'WorkflowExecutor' object has no attribute 'display'"

**Step 3: Modify WorkflowExecutor to use ExecutionDisplay**

In `codeweaver/engine/executor.py`, modify the `__init__` method:

```python
from codeweaver.engine.display import ExecutionDisplay, StepInfo

class WorkflowExecutor:
    def __init__(self, codeweaver_root: Path, llm_fn=None, display: ExecutionDisplay = None):
        self.root = codeweaver_root
        self.llm_fn = llm_fn
        self.checkpoints_db = str(codeweaver_root / "checkpoints.db")
        self.runs_file = codeweaver_root / "runs.yaml"
        self.display = display or ExecutionDisplay()
```

Modify the `run` method to use display:

```python
def run(self, workflow_def, thread_id: str | None = None) -> str:
    """Start a new workflow run. Returns thread_id."""
    thread_id = thread_id or str(uuid4())

    agents_dir = self.root / "agents"
    registry = load_agent_registry(agents_dir) if agents_dir.exists() else {}

    memory = MemoryManager(self.root / "memory")

    orchestrator = Orchestrator(registry, memory, self.llm_fn)
    plans = orchestrator.analyze(workflow_def)

    # Show workflow overview
    steps_info = [StepInfo(index=p.index, goal=p.goal, agents=p.agents) for p in plans]
    self.display.start_workflow(workflow_def.name, steps_info)

    # Determine project root
    project_root = str(self.root.parent)

    graph = compile_graph(
        plans, registry, memory, self.llm_fn,
        workflow_steps=workflow_def.steps,
        project_root=project_root,
        display=self.display  # Pass display to graph
    )

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

        try:
            compiled.invoke(initial_state, config=config)
            self.display.complete_workflow(success=True)
        except Exception as e:
            self.display.complete_workflow(success=False, error=str(e))
            raise

    self._save_run(thread_id, workflow_def.name, "completed")
    return thread_id
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/engine/test_executor.py::test_executor_uses_display -v`
Expected: PASS

**Step 5: Commit**

```bash
git add codeweaver/engine/executor.py tests/engine/test_executor.py
git commit -m "feat: integrate ExecutionDisplay into WorkflowExecutor"
```

---

## Task 3: Pass Display to Node Factory

**Files:**
- Modify: `codeweaver/engine/compiler.py`
- Modify: `codeweaver/engine/node_factory.py`

**Step 1: Modify compile_graph to accept and pass display**

In `codeweaver/engine/compiler.py`:

```python
def compile_graph(
    plans: list[StepPlan],
    agent_registry: dict[str, AgentDef],
    memory: MemoryManager,
    llm_fn=None,
    workflow_steps: list[StepDef] | None = None,
    project_root: str = ".",
    display=None,  # Add display parameter
) -> StateGraph:
    graph = StateGraph(WorkflowState)
    total_steps = len(plans)

    # Create a mapping from step index to StepDef for quick lookup
    step_map = {}
    if workflow_steps:
        step_map = {step.index: step for step in workflow_steps}

    for plan in plans:
        node_name = f"step_{plan.index}"
        if plan.agents and plan.agents[0] in agent_registry:
            agent_def = agent_registry[plan.agents[0]]

            # Extract step context from workflow_steps if available
            step_goal = plan.goal
            step_raw_text = ""
            step_def = step_map.get(plan.index)
            if step_def:
                step_raw_text = step_def.raw_text

            node_fn = make_node(
                agent_def,
                memory,
                total_steps,
                llm_fn,
                step_goal=step_goal,
                step_raw_text=step_raw_text,
                project_root=project_root,
                display=display,  # Pass display to node
                step_index=plan.index,  # Pass step index
                step_agents=plan.agents,  # Pass agents list
            )
        else:
            def node_fn(state: dict) -> dict:
                return state
        graph.add_node(node_name, node_fn)

    if plans:
        # Set entry point to first step's actual index
        graph.set_entry_point(f"step_{plans[0].index}")

    for i, plan in enumerate(plans):
        node_name = f"step_{plan.index}"
        is_last = i == len(plans) - 1
        next_node = f"step_{plans[i + 1].index}" if not is_last else END

        if plan.is_loop:
            def make_condition(loop_node, nxt):
                def condition(state: dict) -> str:
                    if state["error_count"] < MAX_RETRIES and state["status"] == "error":
                        return loop_node
                    return nxt
                return condition
            graph.add_conditional_edges(
                node_name,
                make_condition(node_name, next_node),
                {node_name: node_name, next_node: next_node},
            )
        else:
            graph.add_edge(node_name, next_node)

    return graph
```

**Step 2: Commit**

```bash
git add codeweaver/engine/compiler.py
git commit -m "feat: pass display to compile_graph and nodes"
```

---

## Task 4: Integrate Display into Node Execution

**Files:**
- Modify: `codeweaver/engine/node_factory.py`

**Step 1: Modify make_node to accept and use display**

In `codeweaver/engine/node_factory.py`, update the function signature:

```python
def make_node(
    agent_def: AgentDef,
    memory: MemoryManager,
    total_steps: int,
    llm_fn: Callable | None = None,
    step_goal: str = "",
    step_raw_text: str = "",
    project_root: str = ".",
    display=None,  # Add display parameter
    step_index: int = 0,  # Add step index
    step_agents: list[str] = None,  # Add agents list
) -> Callable:
```

**Step 2: Add display calls at node start**

At the beginning of the `node` function:

```python
def node(state: dict) -> dict:
    # Show step start
    if display:
        display.start_step(step_index, step_goal, step_agents or [agent_def.name])

    # Build context using ContextBuilder
    context_builder = ContextBuilder()
    messages = context_builder.build_messages(
        agent_def, memory, state, total_steps, step_goal, step_raw_text
    )
    # ... rest of the function
```

**Step 3: Add display calls for tool execution**

Replace the existing tool call console.print statements:

```python
# Display tool execution to user
args_preview = str(arguments_str)[:50] + "..." if len(str(arguments_str)) > 50 else str(arguments_str)
if display:
    display.report_tool_call(tool_name, args_preview)
else:
    console.print(f"  [dim]→ Calling {tool_name}({args_preview})[/dim]")
```

And for tool results:

```python
if result.success:
    result_content = json.dumps({
        "success": True,
        "output": output
    })
    if display:
        display.report_tool_result(tool_name, success=True)
    else:
        console.print(f"  [dim green]✓ {tool_name} succeeded[/dim green]")
else:
    result_content = json.dumps({
        "success": False,
        "error": result.error
    })
    if display:
        display.report_tool_result(tool_name, success=False, error=result.error)
    else:
        console.print(f"  [yellow]⚠ {tool_name} failed: {result.error}[/yellow]")
```

**Step 4: Add display call at node completion**

Before returning from the node function:

```python
# Extract summary from LLM response
summary = "Completed"
if isinstance(response, dict):
    content = response.get("content", "")
    if content:
        # Take first sentence as summary
        summary = content.split('.')[0][:100]
elif hasattr(response, "content") and response.content:
    summary = response.content.split('.')[0][:100]

if display:
    display.complete_step(step_index, summary)

memory.write_agent_context(agent_def.name, final_content)
return {**state, "status": "running", "current_step": state["current_step"]}
```

**Step 5: Commit**

```bash
git add codeweaver/engine/node_factory.py
git commit -m "feat: integrate display callbacks into node execution"
```

---

## Task 5: Suppress LiteLLM Debug Output

**Files:**
- Modify: `codeweaver/cli.py`

**Step 1: Configure litellm to suppress debug output**

At the top of `create_llm_fn` function in `codeweaver/cli.py`:

```python
def create_llm_fn(messages: list[dict], tools: list[dict] | None = None):
    """Real LLM function using litellm with configurable API.

    Returns:
        - If tools provided: full message object with potential tool_calls
        - If no tools: content string only
    """
    import os
    import time
    import litellm
    from litellm.exceptions import RateLimitError

    # Suppress LiteLLM debug output
    litellm.suppress_debug_info = True
    import logging
    logging.getLogger("LiteLLM").setLevel(logging.ERROR)

    # Get API configuration from environment variables
    api_key = os.getenv("CODEWEAVER_API_KEY", "sk-IA0OXgtva7EmahBVdzkCJgcJxnmo4ja6O0M0M146HniteI3m")
    # ... rest of function
```

**Step 2: Improve error messages**

Replace the generic error handling:

```python
except Exception as e:
    # Show user-friendly error message
    error_msg = str(e)
    if "api_key" in error_msg.lower():
        console.print(f"[red]API key error:[/red] Please set CODEWEAVER_API_KEY environment variable")
    elif "connection" in error_msg.lower():
        console.print(f"[red]Connection error:[/red] Cannot reach API endpoint. Check CODEWEAVER_API_BASE")
    elif "timeout" in error_msg.lower():
        console.print(f"[red]Timeout error:[/red] API request took too long")
    else:
        console.print(f"[red]LLM error:[/red] {error_msg}")
    raise
```

**Step 3: Commit**

```bash
git add codeweaver/cli.py
git commit -m "feat: suppress LiteLLM debug output and improve error messages"
```

---

## Task 6: Test End-to-End with Real Workflow

**Files:**
- Test: Manual testing with `tests/fixtures/slow_sort_project/optimizer.md`

**Step 1: Set environment variables**

```bash
export CODEWEAVER_API_KEY='sk-IA0OXgtva7EmahBVdzkCJgcJxnmo4ja6O0M0M146HniteI3m'
export CODEWEAVER_API_BASE='https://api.moonshot.cn/v1'
```

**Step 2: Run the optimizer workflow**

```bash
python -m codeweaver.cli run tests/fixtures/slow_sort_project/optimizer.md
```

**Step 3: Verify expected output**

Expected output should show:
1. Workflow overview with numbered steps
2. Each step showing "Step X/Y: [goal]"
3. Tool calls displayed as "→ tool_name(args)"
4. Tool results shown as "✓ tool_name" or "⚠ tool_name: error"
5. Step completion with "✓ Step X complete: [summary]"
6. Final "✓ Workflow completed"

**Step 4: Verify no LiteLLM debug messages**

Confirm that output does NOT contain:
- "Give Feedback / Get Help: https://github.com/BerriAI/litellm"
- "LiteLLM.Info: If you need to debug this error, use `litellm._turn_on_debug()`"

**Step 5: Document test results**

Create `docs/testing/execution-display-test-results.md` with:
- Screenshots or output samples
- Any issues found
- Performance observations

**Step 6: Commit test documentation**

```bash
git add docs/testing/execution-display-test-results.md
git commit -m "docs: add execution display test results"
```

---

## Task 7: Update CLI REPL to Use Display

**Files:**
- Modify: `codeweaver/cli.py`

**Step 1: Update _dispatch function to pass display**

In the `/run` command handler:

```python
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
    executor = WorkflowExecutor(_cw_root(), llm_fn=create_llm_fn)  # Display created automatically
    tid = executor.run(wf)
    console.print(f"[dim]Thread ID: {tid}[/dim]")
```

**Step 2: Update resume command similarly**

```python
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
    executor = WorkflowExecutor(_cw_root(), llm_fn=create_llm_fn)  # Display created automatically
    executor.resume(tid, wf)
    console.print(f"[dim]Thread ID: {tid}[/dim]")
```

**Step 3: Commit**

```bash
git add codeweaver/cli.py
git commit -m "feat: update CLI REPL to use ExecutionDisplay"
```

---

## Task 8: Final Integration Test and Documentation

**Files:**
- Update: `README.md`
- Create: `docs/execution-display.md`

**Step 1: Run full test suite**

```bash
pytest tests/ -v
```

Expected: All tests pass

**Step 2: Create execution display documentation**

Create `docs/execution-display.md`:

```markdown
# Execution Display

CodeWeaver provides real-time feedback during workflow execution.

## Features

### Workflow Overview
At workflow start, see all steps at a glance:
```
Workflow: optimizer
────────────────────────────────────────────────────────────────────────────────
1. Analyze Project Structure (structure-agent)
2. Identify Entry Point (interact-agent)
3. Ask Optimization Target (interact-agent)
...
```

### Step Progress
Each step shows:
- Current step number and total
- Step goal
- Agents involved

```
Step 1/8: Analyze Project Structure [structure-agent]
```

### Tool Execution
See tools being called in real-time:
```
  → read_file(path="src/main.py")
  ✓ read_file
  → list_files(directory="src")
  ✓ list_files
```

### Step Completion
Each step shows a summary:
```
✓ Step 1 complete: Project structure analyzed, found 5 Python files
```

### Error Handling
Clear error messages without debug noise:
```
⚠ read_file: File not found: missing.py
```

## Configuration

Suppress debug output (enabled by default):
```python
import litellm
litellm.suppress_debug_info = True
```

## Customization

Create custom display:
```python
from codeweaver.engine.display import ExecutionDisplay
from rich.console import Console

console = Console(width=120)
display = ExecutionDisplay(console=console)
executor = WorkflowExecutor(root, display=display)
```
```

**Step 3: Update README with execution display section**

Add to README.md under "Features":

```markdown
### Real-Time Execution Feedback

- **Progress tracking**: See workflow overview and current step
- **Tool visibility**: Watch tools being called in real-time
- **Step summaries**: Understand what each step accomplished
- **Clean output**: No debug noise, only relevant information
```

**Step 4: Commit documentation**

```bash
git add docs/execution-display.md README.md
git commit -m "docs: add execution display documentation"
```

**Step 5: Push all changes**

```bash
git push origin main
```

---

## Completion Checklist

- [ ] ExecutionDisplay class created and tested
- [ ] WorkflowExecutor integrated with display
- [ ] Node factory uses display for feedback
- [ ] LiteLLM debug output suppressed
- [ ] End-to-end testing with real workflow
- [ ] CLI REPL updated
- [ ] Documentation complete
- [ ] All tests passing
- [ ] Changes pushed to GitHub

