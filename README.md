# CodeWeaver

Multi-agent workflow generation and execution engine with LLM-powered code database.

## Overview

CodeWeaver is a Python CLI tool that enables you to define complex multi-agent workflows using simple markdown files. Agents collaborate through a shared memory system, with LangGraph handling orchestration and checkpointing for reliable execution.

**Key Capabilities:**
- Define workflows in markdown with natural language or explicit agent references
- Automatic agent generation from workflow analysis
- LLM-powered code database with semantic search
- Workflow interruption and resume support
- Interactive user prompts and tool execution

## Installation

```bash
# Clone repository
git clone https://github.com/Honglin20/CodeWeaver.git
cd CodeWeaver

# Install dependencies
pip install -e .

# Configure LLM API (required)
export KIMI_API='your-api-key'
export KIMI_URL='https://api.moonshot.cn/v1'
```

## Quick Start

### 1. Run the Example Workflow

```bash
cd tests/fixtures/slow_sort_project
codeweaver run optimizer.md
```

This demonstrates a complete 8-step optimization workflow with user interaction and validation.

### 2. Start Interactive REPL

```bash
codeweaver
```

Available commands:
- `/run <workflow.md>` - Execute a workflow
- `/resume <thread_id>` - Resume interrupted workflow
- `/list` - Show all workflow runs
- `/agents` - List available agents
- `/help` - Show all commands

## Creating Your Own Workflow

### Workflow File Structure

Create a markdown file (e.g., `my-workflow.md`) with frontmatter and steps:

```markdown
---
name: my-workflow
description: Brief description of what this workflow does
entry_command: python main.py  # Optional: command to run
---

## Step 1: Analyze Code
@structure-agent: Read the project and identify key components.

## Step 2: Run Tests
@test-agent: Execute the test suite and report results.

## Step 3: Generate Report
Create a summary of findings and save to memory.
```

### Workflow Syntax

**Frontmatter (required):**
```yaml
---
name: workflow-name          # Unique identifier
description: What it does    # Brief description
entry_command: cmd           # Optional: shell command
---
```

**Step Definition:**
```markdown
## Step N: Step Title
@agent-name: Instructions for the agent.
@tool:select: Present options to user.
Natural language instructions without agent reference.
```

### Agent References

**Explicit agent reference:**
```markdown
@structure-agent: Analyze the codebase structure.
```

**Tool invocation:**
```markdown
@tool:select: Ask user to choose from options.
@tool:debugger: Set breakpoint for debugging.
```

**Natural language (LLM infers agent):**
```markdown
Read the configuration file and extract database settings.
```

### Creating Custom Agents

Agents are defined in YAML files in `.codeweaver/agents/` directory:

```yaml
name: my-agent
description: What this agent does
system_prompt: |
  You are an agent that performs specific tasks.

  Your responsibilities:
  1. Task one
  2. Task two

  Always save results to memory for other agents.
tools:
  - read_file
  - run_command
  - list_files
memory:
  read:
    - memory/input.md
    - agents/other-agent/context.md
  write:
    - agents/my-agent/context.md
    - memory/output.md
model: gpt-4o
max_tokens: 4096
```

**Agent Definition Fields:**

- `name` - Unique agent identifier (matches @agent-name in workflows)
- `description` - Brief description for workflow analyzer
- `system_prompt` - Instructions for the LLM (supports multi-line)
- `tools` - List of available tools (read_file, run_command, list_files, debugger)
- `memory.read` - Files this agent reads from memory
- `memory.write` - Files this agent writes to memory
- `model` - LLM model to use (gpt-4o, moonshot-v1-8k, etc.)
- `max_tokens` - Maximum response length

### Available Tools

**Filesystem Tools:**
- `read_file` - Read file contents
- `list_files` - List directory contents
- `run_command` - Execute shell commands (sandboxed)

**Interactive Tools:**
- `tool:select` - Present multiple-choice options to user
- `tool:debugger` - Set programmatic breakpoints

**Code Database Tools (Phase 3):**
- `code_edit` - Modify code with LibCST validation
- `semantic_search` - Search code by natural language query

### Memory System

All agents share a memory directory at `.codeweaver/memory/`:

```
.codeweaver/
├── memory/
│   ├── workflow.md              # Workflow analysis
│   ├── baseline_output.md       # Shared data
│   ├── optimized_output.md      # Shared data
│   └── agents/
│       ├── agent-a/
│       │   ├── context.md       # Agent's working memory
│       │   └── history.md       # Agent's execution history
│       └── agent-b/
│           └── context.md
├── agents/                      # Agent definitions (YAML)
├── checkpoints.db               # LangGraph checkpoints
└── runs.yaml                    # Workflow execution history
```

**Memory Best Practices:**

1. **Agent Context:** Each agent writes to `agents/{agent-name}/context.md`
2. **Shared Data:** Use `memory/*.md` for data shared between agents
3. **Read Before Write:** Agents should read relevant memory files before executing
4. **Structured Output:** Use markdown formatting for readability

### Workflow Patterns

**Sequential Steps:**
```markdown
## Step 1: First Task
@agent-a: Do something.

## Step 2: Second Task
@agent-b: Use results from Step 1.
```

**Validation Loop:**
```markdown
## Step 3 (loop): Validate Results
@validator-agent: Check if results are correct.
If validation fails: @fixer-agent corrects and returns to Step 3.
If validation passes: Continue to next step.
```

Mark a step with `(loop)` to enable automatic retry on errors.

**Parallel Execution (planned):**
```markdown
## Step 4: Parallel Tasks
@agent-a: Task A (independent)
@agent-b: Task B (independent)
@agent-c: Task C (independent)
```

**User Interaction:**
```markdown
## Step 5: Get User Input
@interact-agent: Ask user for preferences.
@tool:select: Present options: ["Option A", "Option B", "Option C"]
Save user choice to memory/user_choices.md.
```

## Complete Example: Optimizer Workflow

See [Optimizer Workflow Guide](docs/optimizer-workflow-guide.md) for a detailed walkthrough.

**Workflow:** `tests/fixtures/slow_sort_project/optimizer.md`

This 8-step workflow demonstrates:
- Project structure analysis
- Interactive user prompts
- Baseline execution and output capture
- Code optimization
- Validation with automatic bug-fix loops

**Run it:**
```bash
cd tests/fixtures/slow_sort_project
codeweaver run optimizer.md
```

**Expected flow:**
1. Structure agent analyzes project
2. User selects entry file via interactive prompt
3. User specifies optimization target and goal
4. User selects specific function to optimize
5. Baseline execution captured (time + output hash)
6. Coder agent applies optimization
7. Validator agent compares baseline vs optimized
8. If validation fails, coder fixes and retries

**Expected output:**
```
time=0.0856s result_hash=dc3f5d46  # baseline
time=0.0023s result_hash=dc3f5d46  # optimized (37x faster, same output)
```

## Important Notes and Limitations

### Critical Setup Requirements

1. **Agent Location:** Agents must be in `.codeweaver/agents/` directory (not `tests/fixtures/agents/`)
2. **LLM Configuration:** Must set `KIMI_API` environment variable or modify `codeweaver/llm.py`
3. **Workflow Steps:** Step indices start at 1 (not 0) in markdown files

### Known Limitations

1. **Agent-Workflow Integration:** Agents currently receive generic prompts, not step-specific instructions
2. **Tool Execution:** Some tools (like `@tool:select`) require additional implementation
3. **Interactive Prompts:** User interaction is partially implemented
4. **Rate Limits:** Kimi API has 20 RPM limit, workflows may need retry logic

### Troubleshooting

**Error: "NoneType object is not callable"**
- Cause: LLM function not passed to WorkflowExecutor
- Fix: Ensure `WorkflowExecutor(_cw_root(), llm_fn=_mock_llm_fn)` in CLI

**Error: "Invalid checkpointer provided"**
- Cause: SqliteSaver.from_conn_string() returns Iterator
- Fix: Use `with SqliteSaver.from_conn_string(db) as checkpointer:`

**Error: "Found edge ending at unknown node step_0"**
- Cause: Graph entry point hardcoded to step_0, but steps start at index 1
- Fix: Use `graph.set_entry_point(f"step_{plans[0].index}")`

**Workflow completes but agents don't execute tasks:**
- Cause: Agents not found in `.codeweaver/agents/` directory
- Fix: Copy agent YAML files to `.codeweaver/agents/`

**Rate limit errors:**
- Cause: Too many LLM API calls in short time
- Fix: Wait 3-5 seconds between workflow runs, or use different API key

## Advanced Features

### Phase 2: Auto-Generation

Automatically generate missing agents from workflow analysis:

```bash
codeweaver analyze my-workflow.md --auto
```

This will:
1. Parse the workflow and identify required agents
2. Generate YAML definitions for missing agents
3. Save to `.codeweaver/agents/`
4. Optionally review generated agents before use

### Phase 3: Code Database

Index your codebase for semantic search:

```bash
# Index with LLM-powered descriptions
codeweaver index /path/to/project --llm

# Index without LLM (faster, no descriptions)
codeweaver index /path/to/project --no-llm
```

**Use in workflows:**
```markdown
## Step 1: Find Sorting Functions
@search-agent: Use semantic search to find all sorting algorithms.
Query: "functions that sort arrays or lists"
Save results to memory/search_results.md.
```

**Programmatic usage:**
```python
from codeweaver.code_db.query import search_symbols_semantic
from codeweaver.llm import create_kimi_llm

llm_fn = create_kimi_llm()
results = search_symbols_semantic(
    code_db_root=".codeweaver/code_db",
    query="sorting algorithm",
    llm_fn=llm_fn,
    top_k=5
)

for result in results:
    print(f"{result['name']}: {result['description']}")
```

### Workflow Interruption and Resume

Workflows automatically checkpoint after each step:

```bash
# Run workflow (may be interrupted)
codeweaver run long-workflow.md

# If interrupted, resume from last checkpoint
codeweaver resume <thread_id>

# List all runs
codeweaver
/list
```

Checkpoints are stored in `.codeweaver/checkpoints.db` using LangGraph's SqliteSaver.

## Project Structure

```
codeweaver/
├── cli.py              # CLI entry point and REPL
├── parser/
│   ├── workflow.py     # Markdown workflow parser
│   └── agent.py        # YAML agent definition parser
├── engine/
│   ├── executor.py     # Workflow execution orchestrator
│   ├── compiler.py     # LangGraph graph compiler
│   ├── orchestrator.py # Two-layer tree decomposition
│   └── node_factory.py # Agent node creation
├── memory/
│   └── manager.py      # Memory file management
├── tools/
│   ├── filesystem.py   # File and command tools
│   └── code_edit.py    # Code modification tools
├── code_db/            # Phase 3: Code database
│   ├── builder.py      # Index builder with LLM
│   ├── query.py        # Semantic search
│   └── watcher.py      # Change notifications
├── generator/          # Phase 2: Auto-generation
│   ├── analyzer.py     # Workflow analyzer
│   ├── agent_gen.py    # Agent generator
│   └── reviewer.py     # Agent reviewer
└── llm.py              # LLM integration (litellm)
```

## Testing

```bash
# Run all tests
pytest tests/ -v

# Run specific phase tests
pytest tests/test_phase1.py -v
pytest tests/test_code_db_phase3.py -v

# Run with real LLM (requires API key)
KIMI_API='your-key' pytest tests/test_semantic_search.py -v
```

**Test Coverage:**
- Phase 1: 76 tests (execution engine, memory, tools)
- Phase 2: Agent generation and review
- Phase 3: 26 tests (code database, semantic search)

## Documentation

- [Design Document](docs/design.md) - Architecture and design decisions
- [Optimizer Workflow Guide](docs/optimizer-workflow-guide.md) - Complete workflow walkthrough
- [Phase 1 Plan](docs/plans/phase1.md) - Execution engine implementation
- [Phase 2 Plan](docs/plans/2026-03-02-phase2-auto-generation.md) - Auto-generation system
- [Phase 3 Plan](docs/plans/2026-03-02-phase3-code-database.md) - Code database implementation

## Contributing

Contributions welcome! Please ensure:
- Tests pass: `pytest tests/ -v`
- Code follows existing patterns
- Documentation updated for new features
- Commit messages follow conventional commits format

## License

MIT License

## Acknowledgments

Built with Claude Sonnet 4.6 assistance.
