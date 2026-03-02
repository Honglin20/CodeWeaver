# CodeWeaver

Multi-agent workflow generation and execution engine with LLM-powered code database.

## Overview

CodeWeaver is a Python CLI tool for multi-agent workflow generation and execution. It uses LangGraph for orchestration, LiteLLM for multi-provider LLM support, and provides an interactive REPL for workflow management.

## Features

### Phase 1: Execution Engine ✅
- LangGraph-based workflow execution with checkpointing
- Interactive REPL with prompt_toolkit + rich
- Tool system: select, run_command, read_file, list_files, debugger
- Memory management with markdown-based blackboard
- Workflow interruption and resume support

### Phase 2: Auto-Generation ✅
- Automatic agent generation from workflow analysis
- LLM-powered agent definition creation
- Agent review and validation system
- Workflow analyzer for missing agent detection

### Phase 3: Code Database ✅
- **LLM-powered symbol descriptions** using Kimi API (Moonshot)
- **MD5-based caching** for performance optimization
- **Change notification system** with auto re-indexing
- **Semantic search** with LLM-based relevance ranking
- **Code editing tools** with LibCST validation
- CLI: `codeweaver index <dir> [--llm/--no-llm]`

## Installation

```bash
# Clone repository
git clone https://github.com/Honglin20/CodeWeaver.git
cd CodeWeaver

# Install dependencies
pip install -e .
```

## Quick Start

```bash
# Start interactive REPL
codeweaver

# Index a Python project with LLM descriptions
codeweaver index /path/to/project --llm

# Index without LLM (faster)
codeweaver index /path/to/project --no-llm

# Run a workflow
codeweaver run optimizer.md

# Resume interrupted workflow
codeweaver resume <thread_id>
```

## Architecture

### Tech Stack
- **langgraph** - Execution engine with interrupt/checkpoint support
- **litellm** - Multi-provider LLM (OpenAI/Claude/Kimi/etc.)
- **prompt_toolkit + rich** - Interactive REPL
- **LibCST** - Code modification with formatting preservation
- **ast + jedi** - Code analysis and indexing (Phase 3)
- **pyyaml** - Agent definition files

### Design Approach (Approach C)
- LangGraph handles control flow only (minimal state)
- Rich data stored in markdown files (`.codeweaver/memory/`)
- Orchestrator LLM performs two-layer tree decomposition
- Agent definitions: declarative YAML (no generated Python code)
- Node communication: markdown files as shared blackboard

## Project Structure

```
codeweaver/
├── cli.py              # CLI entry point
├── parser/             # Workflow and agent parsing
├── engine/             # LangGraph execution engine
├── memory/             # Memory management
├── tools/              # Built-in tools (filesystem, debugger, code_edit)
├── code_db/            # Code database (Phase 3)
│   ├── builder.py      # Index builder with LLM
│   ├── query.py        # Semantic search
│   └── watcher.py      # Change notifications
├── generator/          # Agent auto-generation (Phase 2)
└── llm.py              # LLM integration

tests/
├── fixtures/           # Test projects
└── test_*.py           # Test suites
```

## Phase 3: Code Database

### Features

**LLM-Powered Descriptions**
```python
from codeweaver.llm import create_kimi_llm
from codeweaver.code_db.builder import build_index

llm_fn = create_kimi_llm()
build_index(project_root, output_root, llm_describe_fn=llm_fn)
```

**Semantic Search**
```python
from codeweaver.code_db.query import search_symbols_semantic

result = search_symbols_semantic(
    code_db_root,
    "sorting algorithm",
    llm_fn,
    top_k=5
)
# Returns: bubble_sort ranked #1 based on semantic relevance
```

**Change Notifications**
```python
from codeweaver.tools.code_edit import edit_code

edit_code(
    file_path="src/main.py",
    old_code="def old(): pass",
    new_code="def new(): pass",
    memory_root=memory,
    code_db_root=code_db,
    project_root=src,
    llm_fn=llm_fn
)
# Automatically re-indexes and writes notification
```

### API Configuration

Set environment variables for Kimi API:
```bash
export KIMI_API='your-api-key'
export KIMI_URL='https://api.moonshot.cn/v1'
```

Or use defaults in `codeweaver/llm.py`.

## Testing

```bash
# Run all tests
pytest tests/ -v

# Run Phase 3 tests
pytest tests/test_code_db_phase3.py tests/test_watcher.py tests/test_semantic_search.py -v

# Run with real LLM (requires API key)
KIMI_API='your-key' pytest tests/test_semantic_search.py -v
```

**Test Coverage:**
- Phase 1: 76 tests
- Phase 2: Additional agent generation tests
- Phase 3: 26 tests (19 without LLM, 7 with real Kimi API)

## Documentation

- [Design Document](docs/design.md) - Architecture and design decisions
- [Phase 1 Plan](docs/plans/phase1.md) - Execution engine implementation
- [Phase 2 Plan](docs/plans/2026-03-02-phase2-auto-generation.md) - Auto-generation system
- [Phase 3 Plan](docs/plans/2026-03-02-phase3-code-database.md) - Code database implementation
- [Phase 3 Summary](docs/phase3-summary.md) - Implementation summary

## Example: Optimizer Workflow

```markdown
# Optimizer Workflow

@analyzer: Analyze the slow_sort_project and identify performance issues
@coder: Implement optimizations based on analyzer findings
@validator: Run tests to verify optimizations work correctly
```

Run with:
```bash
codeweaver run optimizer.md
```

## Contributing

Contributions welcome! Please ensure:
- Tests pass: `pytest tests/ -v`
- Code follows existing patterns
- Documentation updated for new features

## License

MIT License

## Acknowledgments

Built with Claude Sonnet 4.6 assistance.
