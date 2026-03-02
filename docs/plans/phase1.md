# Phase 1 Implementation Plan — CodeWeaver Execution Engine

## Overview

Build the core execution pipeline: CLI → Workflow Parser → Orchestrator → LangGraph Executor → Memory Tree.
Every component ships with unit tests and a usage example.

---

## Project Setup

```
codeweaver/
├── __init__.py
├── cli.py                    # prompt_toolkit REPL + typer direct commands
├── parser/
│   ├── workflow.py           # md → WorkflowDef
│   └── agent.py              # yaml → AgentDef
├── engine/
│   ├── orchestrator.py       # two-layer tree decomposition
│   ├── compiler.py           # WorkflowDef → LangGraph StateGraph
│   ├── node_factory.py       # AgentDef → LangGraph node callable
│   └── executor.py           # run/resume graph
├── memory/
│   ├── manager.py            # read/write/compress md files
│   └── compressor.py         # LLM-based step compression
├── tools/
│   ├── select.py             # questionary + LangGraph interrupt
│   ├── filesystem.py         # read_file, list_files, run_command
│   └── debugger.py           # debugpy integration
├── code_db/
│   ├── builder.py            # ast + jedi → hierarchical index
│   ├── query.py              # LLM-callable query tools
│   └── skill.py              # `codeweaver index` skill entry point
└── tests/
    ├── test_parser.py
    ├── test_memory.py
    ├── test_orchestrator.py
    ├── test_code_db.py
    ├── test_tools.py
    └── fixtures/             # sample workflows, agents, python projects
```

**Dependencies (pyproject.toml):**
```toml
[project]
name = "codeweaver"
dependencies = [
    "langgraph>=0.3",
    "litellm>=1.0",
    "prompt_toolkit>=3.0",
    "rich>=13.0",
    "questionary>=2.0",
    "python-frontmatter>=1.0",
    "libcst>=1.0",
    "jedi>=0.19",
    "pyyaml>=6.0",
    "debugpy>=1.8",
]

[project.scripts]
codeweaver = "codeweaver.cli:main"
```

---

## Task 1: Workflow DSL Parser

**File:** `codeweaver/parser/workflow.py`

**Output type:**
```python
@dataclass
class StepDef:
    index: int
    title: str
    raw_text: str
    explicit_agents: list[str]   # from @agent-name syntax
    explicit_tools: list[str]    # from @tool:name syntax
    parallel: bool               # from (parallel) marker
    sub_steps: list["StepDef"]   # nested steps

@dataclass
class WorkflowDef:
    name: str
    description: str
    entry_command: str | None
    steps: list[StepDef]
```

**Parsing rules:**
- `## Step N: Title` → StepDef
- `### Step Na: Title` → sub_step (parallel branch)
- `@agent-name:` → explicit_agents
- `@tool:name:` → explicit_tools
- `## Step N (parallel)` → parallel=True

**Tests (`tests/test_parser.py`):**
```python
def test_explicit_agent_extraction()
def test_tool_extraction()
def test_parallel_step_detection()
def test_nested_substeps()
def test_frontmatter_metadata()
def test_natural_language_step_no_agent()  # no @agent, explicit_agents=[]
```

**Usage:**
```python
from codeweaver.parser.workflow import parse_workflow
wf = parse_workflow("optimizer.md")
# wf.steps[0].explicit_agents == ["structure-agent"]
# wf.steps[1].parallel == True
```

---

## Task 2: Agent Definition Loader

**File:** `codeweaver/parser/agent.py`

**Agent yaml schema:**
```yaml
name: structure-agent
description: Analyzes Python project structure
system_prompt: |
  You are a Python code structure analyst...
tools:
  - read_file
  - list_files
memory:
  read: [code_db/index.md]
  write: [agents/structure-agent/context.md]
model: gpt-4o          # optional, overrides global default
max_tokens: 4096       # optional
```

**Output type:**
```python
@dataclass
class AgentDef:
    name: str
    description: str
    system_prompt: str
    tools: list[str]
    memory_read: list[str]
    memory_write: list[str]
    model: str | None
    max_tokens: int
```

**Tests:**
```python
def test_load_agent_yaml()
def test_missing_optional_fields_use_defaults()
def test_invalid_yaml_raises_error()
def test_load_all_agents_from_directory()
```

**Usage:**
```python
from codeweaver.parser.agent import load_agent, load_agent_registry
agent = load_agent(".codeweaver/agents/structure-agent.yaml")
registry = load_agent_registry(".codeweaver/agents/")
# registry = {"structure-agent": AgentDef(...), ...}
```

---

## Task 3: Memory Tree Manager

**File:** `codeweaver/memory/manager.py`

**Responsibilities:**
- Read/write md files in `.codeweaver/memory/`
- Track loop iterations (`iter_N/full.md`)
- Compress active `full.md` → `meta.md` via LLM
- Load agent context (context.md + history.md + relevant step mds)

**Key API:**
```python
class MemoryManager:
    def write_step_full(self, step_idx: int, content: str, iteration: int = 0) -> Path
    def read_step(self, step_idx: int, full: bool = False) -> str
    def compress_step(self, step_idx: int, iteration: int) -> None  # LLM call
    def write_agent_context(self, agent_name: str, content: str) -> None
    def read_agent_context(self, agent_name: str) -> str
    def append_agent_history(self, agent_name: str, summary: str) -> None
    def load_agent_memory_bundle(self, agent_name: str, current_step: int) -> str
    # returns: context.md + history.md + current step full.md + all other steps meta.md
```

**Memory layout enforced:**
```
.codeweaver/memory/
  workflow.md
  steps/step_{N}/
    full.md | iter_{K}/full.md
    meta.md
  agents/{name}/
    context.md
    history.md
```

**Tests:**
```python
def test_write_and_read_step_full()
def test_iteration_creates_new_dir()        # iter_1, iter_2 never overwrite
def test_compress_step_creates_meta()
def test_load_agent_memory_bundle_structure()
def test_inactive_steps_return_meta_only()
```

**Usage:**
```python
mm = MemoryManager(root=Path(".codeweaver/memory"))
mm.write_step_full(step_idx=6, content="...", iteration=2)
bundle = mm.load_agent_memory_bundle("validator-agent", current_step=6)
# bundle contains full.md for step 6 iter 2, meta.md for all other steps
```

---

## Task 4: Code Database (Skill)

**Files:** `codeweaver/code_db/builder.py`, `query.py`, `skill.py`

**Five layers of information:**
1. File list (pathlib glob)
2. File relationships (ast import analysis)
3. Symbols per file (ast: functions, classes, variables)
4. Symbol descriptions (LLM-generated, one sentence each)
5. Symbol source code (ast.get_source_segment)

**Output structure:**
```
.codeweaver/code_db/
  index.md          # layer 1+2: files + dependency graph
  symbols/
    src__main.md    # layer 3+4+5 for src/main.py
```

**`index.md` format:**
```markdown
# Project Index

## Files
- src/main.py — entry point, imports: [src/model.py, src/utils.py]
- src/model.py — imports: [src/utils.py]
- src/utils.py — imports: []

## Dependency Graph
src/main.py → src/model.py → src/utils.py
```

**`symbols/src__main.md` format:**
```markdown
# src/main.py

## Functions
### train_model(data, lr, epochs)
**Description:** Trains the neural network with given hyperparameters.
**Source:**
```python
def train_model(data, lr, epochs):
    ...
```

## Classes
### Trainer
**Description:** Manages the training loop and checkpointing.
...
```

**LLM-callable query tools:**
```python
def get_file_list(project_root: str) -> str          # layer 1
def get_file_dependencies(file_path: str) -> str     # layer 2
def get_file_symbols(file_path: str) -> str          # layer 3+4 (no source)
def get_symbol_source(file_path: str, symbol: str) -> str  # layer 5
def search_symbols(query: str) -> str                # search by name/description
```

**CLI skill:**
```bash
codeweaver index <project_dir>    # builds/updates .codeweaver/code_db/
codeweaver index --update         # re-index changed files only
```

**Tests:**
```python
def test_file_list_discovery()
def test_import_relationship_extraction()
def test_function_symbol_extraction()
def test_class_symbol_extraction()
def test_variable_symbol_extraction()
def test_llm_description_generation()
def test_source_code_extraction()
def test_query_tool_get_file_list()
def test_query_tool_get_symbol_source()
def test_incremental_update_changed_file_only()
```

**Usage:**
```bash
$ codeweaver index ./my_project

  Indexing my_project...
  ✓ Discovered 12 files
  ✓ Mapped 8 import relationships
  ✓ Extracted 47 symbols
  ✓ Generated descriptions (LLM)
  ✓ Written to .codeweaver/code_db/
```

```python
from codeweaver.code_db.query import get_file_symbols, get_symbol_source
print(get_file_symbols("src/main.py"))
# Returns markdown: functions, classes, descriptions (no source)
print(get_symbol_source("src/main.py", "train_model"))
# Returns full source of train_model
```

---

## Task 5: Orchestrator (Two-Layer Tree Decomposition)

**File:** `codeweaver/engine/orchestrator.py`

**Responsibilities:**
- Layer 1: Extract overall goal for each step
- Layer 2: For each step, select agent(s) from registry + identify tools + detect parallelism + detect loops
- Write analysis to `memory/workflow_analysis.md`
- Return execution plan (ordered list of resolved StepPlans)

**Key types:**
```python
@dataclass
class StepPlan:
    index: int
    goal: str
    agents: list[str]
    tools: list[str]
    parallel: bool
    depends_on: list[int]
    is_loop: bool
    loop_exit_condition: str | None
```

**Agent registry context fed to LLM:**
```
Available agents:
- structure-agent: Analyzes Python project structure and architecture
- interact-agent: Interacts with user, collects input and confirmations
- coder-agent: Modifies Python code using LibCST
- validator-agent: Runs commands and validates output against baseline
```

**Tests:**
```python
def test_explicit_agent_respected()          # @agent-name not overridden
def test_llm_infers_agent_from_description()
def test_loop_detection()                    # validate→fix→validate pattern
def test_parallel_step_detection()
def test_dependency_graph_construction()
def test_analysis_written_to_memory()
```

**Usage:**
```python
from codeweaver.engine.orchestrator import Orchestrator
orch = Orchestrator(registry=registry, memory=mm, llm_model="gpt-4o")
plan = orch.analyze(workflow_def)
# plan[0] = StepPlan(goal="Understand architecture", agents=["structure-agent"], ...)
```

---

## Task 6: LangGraph Compiler + Node Factory

**Files:** `codeweaver/engine/compiler.py`, `node_factory.py`

**LangGraph state (minimal):**
```python
class WorkflowState(TypedDict):
    current_step: int
    iteration: int          # loop iteration counter
    status: str             # running | waiting_human | completed | error
    memory_root: str
    error_count: int        # for max_retries logic
```

**Node factory:** converts AgentDef → async LangGraph node callable:
1. Load agent memory bundle via MemoryManager
2. Build messages: system_prompt + memory bundle + task description
3. Call LLM via litellm with agent's tools
4. Write output to agent context.md
5. Return updated state

**Compiler:** converts list[StepPlan] → StateGraph:
- Sequential steps → linear edges
- Parallel steps → fan-out/fan-in
- Loop steps → conditional edge back to coder node

**Tests:**
```python
def test_sequential_graph_compilation()
def test_parallel_fanout_fanin()
def test_loop_conditional_edge()
def test_node_loads_correct_memory_bundle()
def test_node_writes_output_to_memory()
def test_max_retries_exits_loop()
```

---

## Task 7: Built-in Tools

**Files:** `codeweaver/tools/`

### tool:select (`select.py`)
```python
# Uses LangGraph interrupt() + questionary
def tool_select(options: list[str], prompt: str) -> str:
    # interrupt execution, show questionary.select(), resume with choice
```

### tool:run_command (`filesystem.py`)
```python
def run_command(cmd: str, cwd: str, timeout: int = 60) -> dict:
    # subprocess, no shell=True, capture stdout/stderr
    # returns {"stdout": ..., "stderr": ..., "returncode": ...}
```

### tool:read_file, tool:list_files (`filesystem.py`)
```python
def read_file(path: str) -> str
def list_files(directory: str, pattern: str = "**/*.py") -> list[str]
```

### tool:debugger (`debugger.py`)
```python
def insert_breakpoint(file_path: str, line: int) -> None
    # uses debugpy to set breakpoint programmatically
```

**Tests:**
```python
def test_run_command_captures_output()
def test_run_command_timeout_raises()
def test_run_command_no_shell_injection()   # cmd with ; should not execute second part
def test_read_file_returns_content()
def test_list_files_respects_pattern()
```

---

## Task 8: Interactive REPL + CLI

**File:** `codeweaver/cli.py`

**Entry points:**
```python
# REPL mode (default)
codeweaver

# Direct commands
codeweaver run <workflow.md>
codeweaver resume <workflow_id>
codeweaver index <project_dir>
```

**REPL commands:**
```
/list              list all workflows + status
/run <name>        run workflow
/resume <id>       resume from checkpoint
/agents            list agent registry (tree: name + description)
/agents new        interactive agent creator
/tools             list available tools
/memory <step>     inspect step memory
/status            current workflow status
/help
```

**REPL implementation:**
- `prompt_toolkit.PromptSession` for input loop with history
- Tab completion for `/` commands and workflow names
- `rich.Console` for all output (panels, tables, progress)
- Graceful Ctrl+C → checkpoint save → "Use /resume <id> to continue"

**Tests:**
```python
def test_list_command_shows_workflows()
def test_run_command_triggers_executor()
def test_ctrl_c_saves_checkpoint()
def test_tab_completion_suggests_commands()
```

---

## Task 9: Checkpoint & Resume

**File:** `codeweaver/engine/executor.py`

**Implementation:**
```python
from langgraph.checkpoint.sqlite import SqliteSaver

class WorkflowExecutor:
    def run(self, workflow_def, thread_id: str | None = None) -> str:
        # thread_id = new uuid if None, else resume existing
        checkpointer = SqliteSaver.from_conn_string(".codeweaver/checkpoints.db")
        graph = self.compiler.compile(workflow_def, checkpointer=checkpointer)
        config = {"configurable": {"thread_id": thread_id or str(uuid4())}}
        graph.invoke(initial_state, config=config)
        return config["configurable"]["thread_id"]

    def resume(self, thread_id: str) -> None:
        # same graph, same thread_id → LangGraph resumes from last checkpoint
        graph.invoke(None, config={"configurable": {"thread_id": thread_id}})
```

**Workflow ID storage:** `.codeweaver/runs.yaml` maps `{id: {workflow, started_at, status}}`

**Tests:**
```python
def test_new_run_creates_checkpoint()
def test_resume_continues_from_last_step()
def test_interrupted_run_listed_in_runs_yaml()
def test_completed_run_not_resumable()
```

---

## Execution Order (dependencies)

```
Task 1 (Parser) ──────────────────────────────┐
Task 2 (Agent Loader) ────────────────────────┤
                                               ▼
Task 3 (Memory Manager) ──────────────── Task 5 (Orchestrator)
Task 4 (Code DB) ─── independent              │
                                               ▼
                                        Task 6 (Compiler + Node Factory)
                                               │
                                        Task 7 (Tools)
                                               │
                                        Task 9 (Executor + Checkpoint)
                                               │
                                        Task 8 (REPL + CLI)
```

Tasks 1, 2, 3, 4 can be built in parallel.
Tasks 5→6→7→9→8 are sequential.

---

## Acceptance Criteria for Phase 1

```bash
# Full end-to-end test
$ codeweaver run tests/fixtures/optimizer.md

  ✓ Parsed workflow: 6 steps
  ✓ Orchestrator analysis complete
  ✓ Graph compiled: 6 nodes, 1 loop
  ● Step 1: Analyzing structure...     [structure-agent]
  ✓ Step 1 complete
  ● Step 2: Identifying entry point... [interact-agent]
  ? Select entry file: > src/main.py
  ✓ Step 2 complete
  ...
  ✓ Workflow complete
```

All 40+ unit tests pass.
`codeweaver index ./tests/fixtures/sample_project` produces valid code_db.
