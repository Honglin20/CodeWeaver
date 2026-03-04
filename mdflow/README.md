# MDFlow - Configuration-Driven Multi-Agent System

## Overview
MDFlow is a Python-based framework for defining multi-agent workflows using Markdown files with YAML frontmatter. Built on LangGraph for robust execution.

## Project Structure
```
mdflow/
├── core/
│   ├── models.py      # Pydantic data models
│   ├── parser.py      # Markdown/YAML parsers
│   ├── memory.py      # Memory manager
│   └── compiler.py    # LangGraph workflow compiler
├── agents/            # Agent definition files (.md)
├── workflows/         # Workflow definition files (.md)
├── tools/             # Tool implementations
├── memory/            # Runtime memory storage
└── tests/             # Test suite (8 tests, 100% pass)
```

## Installation
```bash
pip install -r requirements.txt
```

## Features

### Step 1: Configuration Parsing ✅
- Pydantic models for type-safe configuration
- Robust markdown parsing with YAML frontmatter
- Clear error messages for invalid configurations

### Step 2: LangGraph Execution Engine ✅
- Dynamic workflow compilation from configurations
- Memory management with multiple time horizons
- Support for linear and conditional workflows
- Mock execution for topology verification

## Usage

### Agent Definition Format
```markdown
---
name: my_agent
model: gpt-4
max_output_tokens: 2000
memory_strategy: full
tools:
  - search
  - calculator
---

## System Prompt

You are a helpful assistant...
```

### Workflow Definition Format
```markdown
---
workflow_name: my_workflow
entry_point: start
end_point: end
---

### Node: start (agent: planner)

### Node: process (agent: worker) - Description here

### Node: end (agent: summarizer)

## Flow

start --> process : [condition]
process --> end
```

### Programmatic Usage

```python
from core.parser import parse_agent_file, parse_workflow_file
from core.memory import MemoryManager
from core.compiler import WorkflowCompiler, GraphState

# Parse configurations
workflow = parse_workflow_file("workflows/my_workflow.md")
agent = parse_agent_file("agents/my_agent.md")

# Setup execution
memory = MemoryManager("./memory")
compiler = WorkflowCompiler(memory)
graph = compiler.compile(workflow, {"my_agent": agent})

# Execute
result = graph.invoke(GraphState(messages=[], routing_flag="", current_agent=""))
```

## Running Tests
```bash
pytest tests/ -v
# 8 passed in 0.32s
```

## Implementation Status

- ✅ Step 1: Pydantic models + Markdown parser (6 tests)
- ✅ Step 2: LangGraph compiler + Memory manager (2 tests)
- ✅ Step 3: Meta-builder with context compression (2 tests)
- ✅ Step 4: Real execution engine with tools (2 tests)
- 📊 Total: 12 tests, 100% pass rate

## Architecture

- **Type Safety**: Pydantic v2 models with validation
- **Error Handling**: Custom exceptions with clear messages
- **Parsing**: python-frontmatter + regex
- **Execution**: LangGraph StateGraph with conditional routing
- **Memory**: Multi-horizon strategy (ultra-short, medium, long-term)
