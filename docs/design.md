# CodeWeaver — Design Document

## Overview

CodeWeaver is a Python-only CLI tool for defining, generating, and executing multi-agent workflows. Users write workflows in markdown files using a simple DSL (`@agent`, `@tool:name`), and the framework parses, compiles, and executes them using LangGraph as the execution engine, with md files as the shared memory/communication layer.

---

## Phased Roadmap

| Phase | Scope |
|-------|-------|
| **Phase 1** | Execution engine — hand-written workflows + agent definitions, full execution pipeline |
| **Phase 2** | Auto-generation — LLM analyzes workflow md, auto-creates missing agent/tool definitions |
| **Phase 3** | Code database — hierarchical Python code index using `ast` + `jedi` |

---

## Tech Stack

| Component | Library | Notes |
|-----------|---------|-------|
| Workflow execution | `langgraph` | Nodes, routing, interrupt, checkpointing, SqliteSaver |
| LLM providers | `litellm` | 100+ providers, unified OpenAI-compatible API |
| Interactive REPL | `prompt_toolkit` | 主循环，历史记录，Tab补全 |
| Terminal UI | `rich` | 面板、表格、进度条、语法高亮 |
| Interactive prompts | `questionary` | tool:select，基于prompt_toolkit |
| Workflow md parsing | `python-frontmatter` + custom | Frontmatter元数据 + @agent/@tool混合解析 |
| Code modification | `LibCST` | 精准插入/替换，保留格式和注释 |
| Code analysis (Phase 3) | `ast` + `jedi` | 只读，结构提取 + 跨文件引用 |
| Agent definitions | `pyyaml` | 声明式yaml，人工可审查 |
| Debugger | `debugpy` | 程序化断点插入 |
| Sandbox (Phase 1) | `subprocess` (no shell=True) | 基础隔离，timeout + cwd限制 |
| Sandbox (Phase 2+) | Docker (optional) | 高安全级别，可选 |
| Semantic search (Phase 3) | `chromadb` | 大型代码库符号语义搜索 |

**Custom-built components:**
- Workflow DSL解析器（混合模式：显式@agent + LLM推断）
- Agent实例化引擎（yaml → LangGraph node）
- 记忆树管理器（读/写/压缩，循环迭代支持）
- Orchestrator分析引擎（两层树状分解）
- LangGraph图编译器（WorkflowDef → StateGraph）
- tool:select / tool:debugger集成

---

## Architecture

```
codeweaver run optimizer.md
        │
        ▼
┌─────────────────┐
│  Workflow Parser │  parse md → WorkflowDef (steps, agents, tools)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Graph Compiler  │  WorkflowDef → LangGraph StateGraph
└────────┬────────┘
         │
         ▼
┌─────────────────────────────────────────────┐
│              LangGraph Executor              │
│                                             │
│  [step_1_node] → [step_2_node] → ...        │
│       │               │                     │
│  reads/writes     interrupt()               │
│  md memory        for human input           │
└─────────────────────────────────────────────┘
         │
         ▼
  .codeweaver/memory/   (shared md blackboard)
```

---

## Core Abstractions

### 1. Workflow DSL (`.md` files)

```markdown
---
name: optimizer
description: Optimize a Python algorithm for performance
entry_command: python main.py
---

## Step 1: Analyze Structure
@structure-agent: Read the project and map the overall architecture

## Step 2: Identify Entry Point
@interact-agent: Identify the project entry file
@tool:select: Present file options to user for confirmation

## Step 3: Identify Target Algorithm
@interact-agent: Ask user which algorithm to optimize and define the goal

## Step 4: Establish Baseline
@runner-agent: Execute the entry command and save output as baseline

## Step 5: Optimize
@coder-agent: Optimize the target algorithm

## Step 6: Validate
@validator-agent: Re-run entry command, compare output against baseline and user goal
```

### 2. Agent Definition (`.yaml` files)

```yaml
# .codeweaver/agents/structure-agent.yaml
name: structure-agent
description: Analyzes Python project structure and architecture
system_prompt: |
  You are a Python code structure analyst. Given a project directory,
  you map files, their relationships, and key symbols.
  Always write your findings to memory before completing.
tools:
  - read_file
  - list_files
  - query_code_db        # Phase 3
memory:
  read:
    - code_db/index.md
  write:
    - agents/structure-agent/context.md
model: gpt-4o            # overrides global default
```

### 3. LangGraph State (minimal)

```python
class WorkflowState(TypedDict):
    current_step: int
    status: Literal["running", "waiting_human", "completed", "error"]
    memory_root: str      # path to .codeweaver/memory/
    last_agent_output: str
```

All rich data lives in md files. LangGraph state only carries routing info.

---

## Orchestrator Analysis Tree

Orchestrator分析workflow时采用两层树状分解：

```
workflow_analysis.md
├── meta: "优化Python项目中的算法性能"
│
├── step_1:
│   ├── goal: "理解项目整体架构"          ← 第一层：总体目标
│   ├── context: {available_agents: [...]}
│   ├── decision:
│   │   ├── agent: structure-agent        ← 第二层：具体决策
│   │   ├── tools: [read_file, list_files, query_code_db]
│   │   ├── parallel: false
│   │   └── depends_on: []
│   └── status: pending
│
├── step_2:
│   ├── goal: "识别入口文件并与用户确认"
│   ├── context: {depends_on: step_1.output}
│   ├── decision:
│   │   ├── agent: interact-agent
│   │   ├── tools: [tool:select]
│   │   ├── parallel: false
│   │   └── depends_on: [step_1]
│   └── status: pending
│
└── step_5_6_loop:
    ├── goal: "优化并验证，循环直到达标"
    ├── loop: true
    ├── max_iterations: 5
    └── branches:
        ├── optimize: {agent: coder-agent, tools: [libcst_edit]}
        └── validate: {agent: validator-agent, tools: [run_command]}
```

**分析流程：**
1. LLM读取整个workflow md，提取每个step的总体目标（第一层）
2. 对每个step，结合available agents的树状描述，决策agent/tools/并行性（第二层）
3. 识别循环模式（validate→fix→validate），标记为loop节点
4. 将分析结果写入`workflow_analysis.md`，作为执行图的编译依据

## Memory Tree Structure

```
.codeweaver/
├── memory/
│   ├── workflow.md              # 整体状态 + 所有step的meta摘要
│   ├── workflow_analysis.md     # orchestrator分析结果（两层树）
│   ├── steps/
│   │   ├── step_1/
│   │   │   ├── full.md          # 完整细节（活跃时）
│   │   │   └── meta.md          # 压缩摘要（非活跃时）
│   │   └── step_6_validate/
│   │       ├── meta.md          # 整体摘要
│   │       ├── iter_1/
│   │       │   └── full.md      # 第1次迭代完整记录
│   │       ├── iter_2/
│   │       │   └── full.md      # 第2次迭代（修复后）
│   │       └── current.md       # 指向当前迭代的指针
│   └── agents/
│       ├── structure-agent/
│       │   ├── context.md       # 当前工作记忆
│       │   └── history.md       # 历史激活的压缩记录
│       ├── coder-agent/
│       │   ├── context.md
│       │   └── history.md
│       └── validator-agent/
│           ├── context.md
│           └── history.md
├── code_db/                     # Phase 3
│   ├── index.md                 # 文件列表 + 依赖图
│   └── symbols/
│       └── src__main.md         # src/main.py中的符号
├── agents/                      # agent定义文件
│   ├── structure-agent.yaml
│   ├── interact-agent.yaml
│   └── ...
└── tools/                       # tool定义文件
    ├── select.yaml
    └── debugger.yaml
```

**记忆规则：**
- 每个agent激活时只加载：`agents/<name>/context.md` + `agents/<name>/history.md` + 当前step的`full.md` + 其他step的`meta.md`
- 循环每次迭代写入新的`iter_N/full.md`，不覆盖历史，保证可追溯
- step完成后，LLM将`full.md`压缩成`meta.md`，释放上下文空间
- `history.md`记录agent历次激活的压缩摘要，让agent知道"我之前做过什么"

---

## Interactive CLI (REPL Mode)

参考Claude Code的交互模式，`codeweaver`启动后进入交互式REPL：

```
$ codeweaver

  ╔═══════════════════════════════╗
  ║       CodeWeaver v0.1.0       ║
  ║  Multi-agent workflow engine  ║
  ╚═══════════════════════════════╝

  Type /help for available commands

> _
```

**内置命令（Skills）：**

| 命令 | 说明 |
|------|------|
| `/list` | 列出所有workflow（含状态：pending/running/completed/interrupted） |
| `/create` | 交互式创建新workflow（引导用户填写步骤） |
| `/run <workflow>` | 执行指定workflow |
| `/resume <id>` | 恢复中断的workflow |
| `/agents` | 列出所有可用agent（树状：name + description） |
| `/agents new` | 创建新agent定义（交互式） |
| `/tools` | 列出所有可用工具 |
| `/memory <step>` | 查看指定step的记忆内容 |
| `/status` | 当前workflow执行状态 |
| `/help` | 帮助 |

**技术实现：**
- `prompt_toolkit` — REPL主循环，支持历史记录、Tab补全、快捷键
- `rich` — 面板、表格、进度条、语法高亮
- `questionary` — workflow执行中的交互提示（tool:select等）

**执行时的交互体验：**
```
> /run optimizer

  Running: optimizer.md
  ─────────────────────────────────────
  ✓ Step 1  Analyzing project structure...     [structure-agent]
  ● Step 2  Identifying entry point...         [interact-agent]

  ? Select the entry file:
    ❯ src/main.py
      src/train.py
      scripts/run.py
  ─────────────────────────────────────
```

**直接传入workflow路径（非交互模式）：**
```bash
codeweaver run optimizer.md          # 直接运行
codeweaver resume workflow_abc123    # 直接恢复
```

## Tool Definitions

### tool:select
Pauses execution via LangGraph `interrupt()`, presents a `questionary.select()` prompt to the user, resumes with the selection written to memory.

### tool:debugger
Uses `debugpy` to insert a breakpoint at a specified file:line. The debugger-agent can then inspect variables and step through execution.

---

## Phase 1 — Execution Engine (MVP)

**Deliverables:**
- `codeweaver run <workflow.md>` CLI command
- Workflow md parser
- Agent yaml loader + LangGraph node factory
- Memory tree manager (read/write/compress)
- Built-in tools: `tool:select`, `read_file`, `list_files`, `run_command`
- LangGraph graph compiler
- Human-in-the-loop via `interrupt()`

**Project structure:**
```
codeweaver/
├── cli.py                  # typer entry points
├── parser/
│   ├── workflow.py         # md → WorkflowDef
│   └── agent.py            # yaml → AgentDef
├── engine/
│   ├── compiler.py         # WorkflowDef → StateGraph
│   ├── node_factory.py     # AgentDef → LangGraph node
│   └── executor.py         # run the graph
├── memory/
│   ├── manager.py          # read/write/compress md files
│   └── compressor.py       # LLM-based step compression
├── tools/
│   ├── select.py           # questionary integration
│   ├── debugger.py         # debugpy integration
│   └── filesystem.py       # read_file, list_files, run_command
└── code_db/                # Phase 3
    ├── builder.py
    └── query.py
```

---

## Phase 2 — Auto-Generation

**Deliverables:**
- `codeweaver analyze <workflow.md>` — LLM analyzes steps, identifies needed agents/tools
- Auto-generates missing agent yaml definitions
- User reviews generated definitions before execution
- `codeweaver run <workflow.md> --auto` — analyze + run in one command

---

## Phase 3 — Code Database

**Deliverables:**
- `codeweaver index <project_dir>` — builds `.codeweaver/code_db/`
- Uses `ast` for symbol extraction (functions, classes, variables)
- Uses `jedi` for cross-reference analysis (imports, call graphs)
- LLM generates short descriptions for each symbol
- `query_code_db` tool available to all agents
- Change notification: when coder-agent modifies a file, re-indexes affected symbols and notifies other active agents via memory

---

## Key Design Decisions

1. **md files as communication protocol** — not Python dataclasses. Enables universal applicability across projects with different data shapes. Any agent can read/write any memory file.

2. **LangGraph state is minimal** — only routing metadata. This avoids LangGraph's typed state schema becoming a bottleneck as workflows grow complex.

3. **Agent definitions are declarative yaml** — no generated Python code. Safe, auditable, human-editable. The framework interprets them at runtime.

4. **Memory compression is LLM-driven** — inactive step memories are compressed to meta descriptions, keeping each agent's context window focused on the current task.

5. **litellm for all LLM calls** — single interface, swap providers per-agent via `model:` field in yaml.

---

## Open Questions

- [ ] How to handle parallel steps in the workflow DSL? (e.g., two agents running concurrently)
- [ ] Should agent definitions support inheritance? (e.g., `extends: base-coder-agent`)
- [ ] Workflow versioning — how to resume a partially-completed workflow after code changes?
- [ ] Security model for `run_command` tool — sandboxing?
