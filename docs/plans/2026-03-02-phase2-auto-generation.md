# Phase 2: Auto-Generation Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Given a workflow markdown file, automatically analyze each step, detect missing agents, generate their YAML definitions via LLM, present them for user review, then execute.

**Architecture:** Three-layer tree decomposition — (1) workflow → step goals, (2) step goals → required capabilities, (3) capabilities → agent definitions. All analysis written to `workflow_analysis.md` as a hierarchical tree. Agent definitions generated as declarative YAML (no code), reviewed by user before execution.

**Tech Stack:** `litellm`, `pyyaml`, `questionary`, `python-frontmatter`, existing Phase 1 APIs.

---

## Real Test Project

All E2E tests use `tests/fixtures/slow_sort_project/` — a Python project with a deliberately slow bubble sort that the optimizer workflow will analyze and improve.

```
tests/fixtures/slow_sort_project/
├── src/
│   ├── main.py       # entry: runs sort benchmark, prints time + result hash
│   ├── sorter.py     # contains bubble_sort() — O(n²), intentionally slow
│   └── utils.py      # timing helper
└── optimizer.md      # workflow that drives the optimization
```

`main.py` output format (deterministic, comparable):
```
time=2.34s result_hash=abc123
```

---

## Task 1: Workflow Gap Analyzer

**Files:**
- Create: `codeweaver/generator/analyzer.py`
- Create: `codeweaver/generator/__init__.py`
- Test: `tests/test_analyzer.py`

### What it does
Takes a `WorkflowDef` + existing `registry: dict[str, AgentDef]` → returns a tree-structured `AnalysisTree` identifying which steps have agents, which are missing, and what capability each missing step needs.

### Tree structure output

```python
@dataclass
class StepAnalysis:
    step_index: int
    step_title: str
    goal: str                        # LLM-extracted one-sentence goal
    required_capability: str         # LLM-inferred capability description
    matched_agent: str | None        # name of existing agent, or None
    gap: bool                        # True if no agent matched

@dataclass
class AnalysisTree:
    workflow_name: str
    workflow_description: str
    steps: list[StepAnalysis]
    gaps: list[StepAnalysis]         # steps where gap=True
    
    def to_markdown(self) -> str:    # tree-structured md for workflow_analysis.md
```

### `to_markdown()` output format

```markdown
# Workflow Analysis: optimizer

## Meta
- Name: optimizer
- Description: Optimize a Python algorithm for performance
- Total steps: 6
- Gaps found: 1

## Step Tree

### Step 1: Analyze Structure
- Goal: Understand the project's file structure and code architecture
- Required capability: Python project structure analysis
- Matched agent: structure-agent ✓

### Step 6: Validate
- Goal: Verify optimization correctness and performance improvement
- Required capability: Output validation and performance comparison
- Matched agent: MISSING ✗
- Gap: needs agent with capability "output validation"
```

### Implementation

```python
# codeweaver/generator/analyzer.py
from dataclasses import dataclass, field
from codeweaver.parser.workflow import WorkflowDef, StepDef
from codeweaver.parser.agent import AgentDef
from typing import Callable

@dataclass
class StepAnalysis:
    step_index: int
    step_title: str
    goal: str
    required_capability: str
    matched_agent: str | None
    gap: bool

@dataclass
class AnalysisTree:
    workflow_name: str
    workflow_description: str
    steps: list[StepAnalysis]
    
    @property
    def gaps(self) -> list[StepAnalysis]:
        return [s for s in self.steps if s.gap]
    
    def to_markdown(self) -> str: ...

class WorkflowAnalyzer:
    def __init__(self, registry: dict[str, AgentDef], llm_fn: Callable[[list[dict]], str]):
        self.registry = registry
        self.llm_fn = llm_fn
    
    def analyze(self, workflow: WorkflowDef) -> AnalysisTree: ...
    def _match_agent(self, capability: str) -> str | None: ...
    # _match_agent: call llm_fn with capability + registry descriptions,
    # ask "which agent best matches? reply with agent name or NONE"
```

### Step 1: Write failing tests

```python
# tests/test_analyzer.py
from codeweaver.generator.analyzer import WorkflowAnalyzer, AnalysisTree, StepAnalysis
from codeweaver.parser.workflow import WorkflowDef, StepDef
from codeweaver.parser.agent import AgentDef

def make_registry():
    return {
        "structure-agent": AgentDef(
            name="structure-agent",
            description="Analyzes Python project structure",
            system_prompt="You analyze code structure.",
        )
    }

def make_llm(responses: list[str]):
    """Returns a mock llm_fn that pops responses in order."""
    responses = list(responses)
    def llm_fn(messages):
        return responses.pop(0)
    return llm_fn

def test_matched_agent_no_gap():
    wf = WorkflowDef(name="test", description="test", entry_command=None, steps=[
        StepDef(index=0, title="Analyze Structure", raw_text="@structure-agent: analyze",
                explicit_agents=["structure-agent"], explicit_tools=[], parallel=False, sub_steps=[])
    ])
    llm = make_llm(["Understand project architecture", "code analysis", "structure-agent"])
    analyzer = WorkflowAnalyzer(registry=make_registry(), llm_fn=llm)
    tree = analyzer.analyze(wf)
    assert tree.steps[0].matched_agent == "structure-agent"
    assert tree.steps[0].gap == False
    assert len(tree.gaps) == 0

def test_missing_agent_creates_gap():
    wf = WorkflowDef(name="test", description="test", entry_command=None, steps=[
        StepDef(index=0, title="Validate Results", raw_text="validate output",
                explicit_agents=[], explicit_tools=[], parallel=False, sub_steps=[])
    ])
    llm = make_llm(["Verify optimization correctness", "output validation", "NONE"])
    analyzer = WorkflowAnalyzer(registry=make_registry(), llm_fn=llm)
    tree = analyzer.analyze(wf)
    assert tree.steps[0].matched_agent is None
    assert tree.steps[0].gap == True
    assert len(tree.gaps) == 1

def test_explicit_agent_skips_llm_matching():
    """If step has explicit_agents, use it directly — no LLM call for matching."""
    call_count = [0]
    def counting_llm(messages):
        call_count[0] += 1
        return "Understand structure"  # only goal extraction calls
    wf = WorkflowDef(name="test", description="test", entry_command=None, steps=[
        StepDef(index=0, title="Step 1", raw_text="@structure-agent: do it",
                explicit_agents=["structure-agent"], explicit_tools=[], parallel=False, sub_steps=[])
    ])
    analyzer = WorkflowAnalyzer(registry=make_registry(), llm_fn=counting_llm)
    tree = analyzer.analyze(wf)
    assert tree.steps[0].matched_agent == "structure-agent"
    # LLM called for goal + capability, but NOT for agent matching (explicit)
    assert call_count[0] <= 2

def test_analysis_tree_to_markdown():
    tree = AnalysisTree(
        workflow_name="optimizer",
        workflow_description="Optimize algorithm",
        steps=[
            StepAnalysis(0, "Analyze", "Understand structure", "code analysis", "structure-agent", False),
            StepAnalysis(1, "Validate", "Verify results", "output validation", None, True),
        ]
    )
    md = tree.to_markdown()
    assert "# Workflow Analysis: optimizer" in md
    assert "structure-agent ✓" in md
    assert "MISSING ✗" in md
    assert "Gaps found: 1" in md

def test_multiple_steps_dependency_order():
    """Steps analyzed in order, gaps list preserves order."""
    wf = WorkflowDef(name="test", description="test", entry_command=None, steps=[
        StepDef(index=0, title="Step A", raw_text="analyze", explicit_agents=[], explicit_tools=[], parallel=False, sub_steps=[]),
        StepDef(index=1, title="Step B", raw_text="validate", explicit_agents=[], explicit_tools=[], parallel=False, sub_steps=[]),
    ])
    llm = make_llm(["goal A", "cap A", "NONE", "goal B", "cap B", "NONE"])
    analyzer = WorkflowAnalyzer(registry={}, llm_fn=llm)
    tree = analyzer.analyze(wf)
    assert len(tree.gaps) == 2
    assert tree.gaps[0].step_index == 0
    assert tree.gaps[1].step_index == 1
```

Run: `pytest tests/test_analyzer.py -v`
Expected: FAIL (module not found)

### Step 2: Implement `analyzer.py`

### Step 3: Run tests — all 5 pass

---

## Task 2: Agent Generator

**Files:**
- Create: `codeweaver/generator/agent_gen.py`
- Test: `tests/test_agent_gen.py`

### What it does
Takes a `StepAnalysis` (gap) → calls LLM with a structured prompt → returns a complete `AgentDef` + writes YAML to `.codeweaver/agents/<name>.yaml`.

### Tree decomposition for generation

The LLM prompt asks for a tree-structured response:

```
Given this step:
  Goal: Verify optimization correctness and performance improvement
  Required capability: output validation

Generate an agent definition with this structure:
1. Name (kebab-case, descriptive)
2. Description (one sentence)
3. Responsibilities (2-3 bullet points)
4. System prompt (based on responsibilities)
5. Tools needed (from: run_command, read_file, list_files, tool:select)
```

### Implementation

```python
# codeweaver/generator/agent_gen.py
import yaml
from pathlib import Path
from codeweaver.parser.agent import AgentDef
from codeweaver.generator.analyzer import StepAnalysis
from typing import Callable

AVAILABLE_TOOLS = ["run_command", "read_file", "list_files", "tool:select", "tool:debugger"]

def generate_agent(
    gap: StepAnalysis,
    llm_fn: Callable[[list[dict]], str],
    output_dir: Path,
) -> AgentDef:
    """
    Generate an AgentDef for a gap step, write YAML to output_dir/<name>.yaml.
    Returns the generated AgentDef.
    """

def _build_generation_prompt(gap: StepAnalysis) -> list[dict]:
    """Build the LLM messages for agent generation."""

def _parse_llm_response(response: str) -> dict:
    """
    Parse LLM response into {name, description, system_prompt, tools}.
    LLM response format (YAML block):
    ```yaml
    name: validator-agent
    description: Validates optimization results
    system_prompt: |
      You are a validation specialist...
    tools:
      - run_command
      - read_file
    ```
    """
```

### Step 1: Write failing tests

```python
# tests/test_agent_gen.py
import yaml
from pathlib import Path
from codeweaver.generator.agent_gen import generate_agent, _parse_llm_response
from codeweaver.generator.analyzer import StepAnalysis

MOCK_LLM_RESPONSE = """
```yaml
name: validator-agent
description: Validates optimization results by comparing output against baseline
system_prompt: |
  You are a validation specialist. Run the entry command, compare output
  against baseline, and report whether the optimization goal was achieved.
tools:
  - run_command
  - read_file
```
"""

def make_gap():
    return StepAnalysis(
        step_index=5,
        step_title="Validate",
        goal="Verify optimization correctness",
        required_capability="output validation",
        matched_agent=None,
        gap=True,
    )

def test_generate_agent_returns_agentdef(tmp_path):
    llm = lambda msgs: MOCK_LLM_RESPONSE
    agent = generate_agent(make_gap(), llm, tmp_path)
    assert agent.name == "validator-agent"
    assert "validation" in agent.description.lower()
    assert "run_command" in agent.tools

def test_generate_agent_writes_yaml(tmp_path):
    llm = lambda msgs: MOCK_LLM_RESPONSE
    generate_agent(make_gap(), llm, tmp_path)
    yaml_file = tmp_path / "validator-agent.yaml"
    assert yaml_file.exists()
    data = yaml.safe_load(yaml_file.read_text())
    assert data["name"] == "validator-agent"

def test_parse_llm_response_extracts_yaml():
    result = _parse_llm_response(MOCK_LLM_RESPONSE)
    assert result["name"] == "validator-agent"
    assert result["tools"] == ["run_command", "read_file"]

def test_parse_llm_response_handles_no_fences():
    """LLM sometimes returns YAML without code fences."""
    raw = "name: test-agent\ndescription: test\nsystem_prompt: you are a test\ntools:\n  - read_file\n"
    result = _parse_llm_response(raw)
    assert result["name"] == "test-agent"

def test_generated_yaml_has_required_fields(tmp_path):
    llm = lambda msgs: MOCK_LLM_RESPONSE
    generate_agent(make_gap(), llm, tmp_path)
    data = yaml.safe_load((tmp_path / "validator-agent.yaml").read_text())
    for field in ["name", "description", "system_prompt"]:
        assert field in data, f"Missing field: {field}"
```

Run: `pytest tests/test_agent_gen.py -v`
Expected: FAIL

### Step 2: Implement `agent_gen.py`

### Step 3: Run tests — all 5 pass

---

## Task 3: Review Interface

**Files:**
- Create: `codeweaver/generator/reviewer.py`
- Test: `tests/test_reviewer.py`

### What it does
Presents generated agent definitions to the user for review. Uses `rich` to display the YAML, then `questionary` to ask: accept / edit / skip. Returns list of accepted `AgentDef`s.

```python
# codeweaver/generator/reviewer.py
from pathlib import Path
from rich.console import Console
from rich.syntax import Syntax
from codeweaver.parser.agent import AgentDef
from typing import Callable

console = Console()

def review_agents(
    agents: list[AgentDef],
    agents_dir: Path,
    prompt_fn: Callable[[str, list[str]], str] | None = None,
    # prompt_fn injectable for tests: (question, choices) -> choice
) -> list[AgentDef]:
    """
    For each agent: display YAML, ask user to accept/skip.
    Accepted agents are written to agents_dir/<name>.yaml.
    Returns list of accepted AgentDefs.
    """
```

### Step 1: Write failing tests

```python
# tests/test_reviewer.py
from codeweaver.generator.reviewer import review_agents
from codeweaver.parser.agent import AgentDef

def make_agent(name="test-agent"):
    return AgentDef(
        name=name, description="A test agent",
        system_prompt="You are a test agent.",
        tools=["read_file"],
    )

def test_accept_all_agents(tmp_path):
    agents = [make_agent("agent-a"), make_agent("agent-b")]
    prompt_fn = lambda q, choices: "accept"
    accepted = review_agents(agents, tmp_path, prompt_fn=prompt_fn)
    assert len(accepted) == 2
    assert (tmp_path / "agent-a.yaml").exists()
    assert (tmp_path / "agent-b.yaml").exists()

def test_skip_agent_not_written(tmp_path):
    agents = [make_agent("agent-a")]
    prompt_fn = lambda q, choices: "skip"
    accepted = review_agents(agents, tmp_path, prompt_fn=prompt_fn)
    assert len(accepted) == 0
    assert not (tmp_path / "agent-a.yaml").exists()

def test_mixed_accept_skip(tmp_path):
    agents = [make_agent("agent-a"), make_agent("agent-b")]
    responses = ["accept", "skip"]
    prompt_fn = lambda q, choices: responses.pop(0)
    accepted = review_agents(agents, tmp_path, prompt_fn=prompt_fn)
    assert len(accepted) == 1
    assert accepted[0].name == "agent-a"
```

Run: `pytest tests/test_reviewer.py -v`
Expected: FAIL

### Step 2: Implement `reviewer.py`

### Step 3: Run tests — all 3 pass

---

## Task 4: CLI Integration

**Files:**
- Modify: `codeweaver/cli.py`
- Test: `tests/test_cli_phase2.py`

### New CLI commands

```bash
codeweaver analyze optimizer.md          # analyze + show gaps + generate + review
codeweaver run optimizer.md --auto       # analyze + generate + run (skip review)
```

### `/analyze` REPL command

Add to `_dispatch()`:
```
/analyze <workflow>   analyze workflow, generate missing agents, review
```

### Implementation additions to `cli.py`

```python
@app.command()
def analyze(workflow: str, auto: bool = typer.Option(False, "--auto")):
    """Analyze workflow, generate missing agents, optionally run."""
    # 1. parse workflow md
    # 2. load registry from .codeweaver/agents/
    # 3. WorkflowAnalyzer.analyze() → AnalysisTree
    # 4. display tree (rich panel)
    # 5. if gaps: generate agents via AgentGenerator
    # 6. if not auto: review_agents()
    # 7. if auto or all accepted: WorkflowExecutor.run()
```

### Step 1: Write failing tests

```python
# tests/test_cli_phase2.py
from unittest.mock import patch, MagicMock
from codeweaver.cli import _dispatch

def test_analyze_command_dispatches(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    # Should not raise even with no .codeweaver dir
    _dispatch("/analyze")  # missing arg → prints usage, no crash

def test_analyze_with_workflow_file(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    wf_file = tmp_path / "test.md"
    wf_file.write_text("---\nname: test\ndescription: test\n---\n## Step 1\ndo something\n")
    with patch("codeweaver.cli.WorkflowAnalyzer") as mock_analyzer:
        mock_tree = MagicMock()
        mock_tree.gaps = []
        mock_tree.to_markdown.return_value = "# Analysis"
        mock_analyzer.return_value.analyze.return_value = mock_tree
        _dispatch(f"/analyze {wf_file}")
        mock_analyzer.return_value.analyze.assert_called_once()
```

Run: `pytest tests/test_cli_phase2.py -v`
Expected: FAIL

### Step 2: Add `analyze` command to `cli.py` and `/analyze` to `_dispatch()`

### Step 3: Run tests — pass

---

## Task 5: Real Test Project + E2E Test

**Files:**
- Create: `tests/fixtures/slow_sort_project/src/main.py`
- Create: `tests/fixtures/slow_sort_project/src/sorter.py`
- Create: `tests/fixtures/slow_sort_project/src/utils.py`
- Create: `tests/fixtures/slow_sort_project/optimizer.md`
- Test: `tests/test_phase2_e2e.py`

### Real test project

```python
# tests/fixtures/slow_sort_project/src/sorter.py
def bubble_sort(arr):
    """Intentionally slow O(n²) sort."""
    n = len(arr)
    for i in range(n):
        for j in range(0, n - i - 1):
            if arr[j] > arr[j + 1]:
                arr[j], arr[j + 1] = arr[j + 1], arr[j]
    return arr
```

```python
# tests/fixtures/slow_sort_project/src/utils.py
import time, hashlib, json

def timed_run(fn, *args):
    start = time.time()
    result = fn(*args)
    elapsed = time.time() - start
    return elapsed, result

def result_hash(data):
    return hashlib.md5(json.dumps(sorted(data)).encode()).hexdigest()[:8]
```

```python
# tests/fixtures/slow_sort_project/src/main.py
import sys
sys.path.insert(0, ".")
from src.sorter import bubble_sort
from src.utils import timed_run, result_hash

data = list(range(1000, 0, -1))  # worst case: reverse sorted
elapsed, result = timed_run(bubble_sort, data)
print(f"time={elapsed:.4f}s result_hash={result_hash(result)}")
```

```markdown
# tests/fixtures/slow_sort_project/optimizer.md
---
name: slow-sort-optimizer
description: Optimize the bubble sort algorithm in slow_sort_project
entry_command: python src/main.py
---

## Step 1: Analyze Structure
@structure-agent: Read the project and map the overall architecture

## Step 2: Identify Target
Ask user which algorithm to optimize

## Step 3: Establish Baseline
@runner-agent: Execute the entry command and save output as baseline

## Step 4: Optimize
@coder-agent: Replace bubble_sort with a faster implementation

## Step 5: Validate
Verify the optimized output matches baseline hash and runs faster
```

### E2E test (mocked LLM, real file I/O)

```python
# tests/test_phase2_e2e.py
from pathlib import Path
from codeweaver.generator.analyzer import WorkflowAnalyzer
from codeweaver.generator.agent_gen import generate_agent
from codeweaver.parser.workflow import parse_workflow
from codeweaver.parser.agent import load_agent_registry

FIXTURE = Path(__file__).parent / "fixtures" / "slow_sort_project"

def make_mock_llm(goal_prefix="Perform task", capability="general", match="NONE"):
    """Returns deterministic mock LLM for analysis."""
    call_count = [0]
    def llm_fn(messages):
        call_count[0] += 1
        content = messages[-1]["content"].lower()
        if "one sentence" in content or "goal" in content:
            return f"{goal_prefix} for step {call_count[0]}"
        if "capability" in content or "required" in content:
            return capability
        if "which agent" in content or "matches" in content:
            return match
        return goal_prefix
    return llm_fn

def test_analyze_slow_sort_project(tmp_path):
    """Full analysis of slow_sort_project/optimizer.md with mock LLM."""
    wf_text = (FIXTURE / "optimizer.md").read_text()
    wf = parse_workflow(wf_text)
    assert wf.name == "slow-sort-optimizer"
    assert len(wf.steps) == 5

    # Registry has structure-agent and coder-agent, missing runner-agent and validator
    registry = {}  # empty — all steps will be gaps
    llm = make_mock_llm()
    analyzer = WorkflowAnalyzer(registry=registry, llm_fn=llm)
    tree = analyzer.analyze(wf)
    
    assert len(tree.steps) == 5
    assert len(tree.gaps) == 5  # all missing since registry is empty
    md = tree.to_markdown()
    assert "slow-sort-optimizer" in md
    assert "MISSING ✗" in md

def test_generate_agents_for_gaps(tmp_path):
    """Generate agent YAMLs for all gaps in slow_sort_project."""
    wf_text = (FIXTURE / "optimizer.md").read_text()
    wf = parse_workflow(wf_text)
    registry = {}
    llm = make_mock_llm()
    analyzer = WorkflowAnalyzer(registry=registry, llm_fn=llm)
    tree = analyzer.analyze(wf)
    
    MOCK_YAML = """
```yaml
name: runner-agent
description: Executes commands and captures output
system_prompt: You run commands and save output.
tools:
  - run_command
```
"""
    gen_llm = lambda msgs: MOCK_YAML
    agents_dir = tmp_path / "agents"
    agents_dir.mkdir()
    
    generated = []
    for gap in tree.gaps[:2]:  # generate first 2
        agent = generate_agent(gap, gen_llm, agents_dir)
        generated.append(agent)
    
    assert len(generated) == 2
    assert len(list(agents_dir.glob("*.yaml"))) == 2

def test_analysis_tree_markdown_structure(tmp_path):
    """Verify the markdown tree has correct hierarchical structure."""
    wf_text = (FIXTURE / "optimizer.md").read_text()
    wf = parse_workflow(wf_text)
    llm = make_mock_llm(goal_prefix="Execute task", capability="execution")
    analyzer = WorkflowAnalyzer(registry={}, llm_fn=llm)
    tree = analyzer.analyze(wf)
    md = tree.to_markdown()
    
    # Verify tree structure
    assert "## Meta" in md
    assert "## Step Tree" in md
    assert "### Step 1:" in md
    assert "- Goal:" in md
    assert "- Required capability:" in md
    assert "- Matched agent:" in md
```

Run: `pytest tests/test_phase2_e2e.py -v`
Expected: All 3 pass after Tasks 1-4 complete.

---

## Execution Order

```
Task 1 (Analyzer) → Task 2 (Generator) → Task 3 (Reviewer) → Task 4 (CLI) → Task 5 (E2E)
```

Tasks 1-3 are independent of each other and can be built in parallel.
Task 4 depends on 1-3. Task 5 depends on all.

---

## Verification

```bash
# Unit tests
pytest tests/test_analyzer.py tests/test_agent_gen.py tests/test_reviewer.py tests/test_cli_phase2.py tests/test_phase2_e2e.py -v

# Full suite (58 Phase 1 + Phase 2 tests)
pytest tests/ -v

# Manual E2E
cd tests/fixtures/slow_sort_project
python src/main.py   # baseline: time=~0.05s result_hash=<hash>

# From project root
codeweaver analyze tests/fixtures/slow_sort_project/optimizer.md
# Expected: shows analysis tree, identifies missing agents, generates YAMLs, prompts for review
```
