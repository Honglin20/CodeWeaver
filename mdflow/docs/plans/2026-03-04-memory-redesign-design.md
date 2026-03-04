# Memory Redesign - Structured Memory Architecture

## Date: 2026-03-04

## Overview

重新设计 MDFlow 的记忆系统，采用 Manager-Agnostic State 架构，实现四层结构化记忆。

## Architecture

### Core Principles

1. **状态与逻辑分离**：GraphState 只包含路径和标识符
2. **MemoryManager 中心化**：统一管理所有记忆层
3. **文件锁机制**：防止并发冲突
4. **按 Session 隔离**：每个会话独立文件

### Memory Tiers

#### 1. Ultra-Short Memory (超短期记忆)
- **用途**：无状态 context，每次调用重新读取
- **存储**：agent.md frontmatter 中定义 context_file
- **示例**：validator 的校验规则

#### 2. Short-Term Memory (短期记忆)
- **用途**：对话历史，滑动窗口
- **存储**：`checkpoint_{session_id}.json`
- **特点**：按 session 隔离，自动截断

#### 3. Medium-Term Memory (中期记忆)
- **用途**：任务日志
- **存储**：JSONL (结构化) + MD (展示)
- **特点**：每个任务结束后追加摘要

#### 4. Long-Term Memory (长期记忆)
- **用途**：知识库
- **存储**：system_meta.md (索引) + details/ (详情)
- **特点**：Agent 主动调用工具搜索

## Directory Structure

```
workflows/
└── code_optimization/
    ├── flow.md
    ├── config.yaml
    ├── agents/
    │   ├── validator.md
    │   ├── interactor.md
    │   └── optimizer.md
    ├── memory/
    │   ├── checkpoint_{session_id}.json
    │   ├── .locks/
    │   ├── medium_term/
    │   │   ├── task_logs.jsonl
    │   │   └── task_logs.md
    │   └── long_term/
    │       ├── system_meta.md
    │       └── details/
    └── tools/
        ├── bash_executor.md
        └── code_parser.md
```

## Key Changes

### 1. GraphState Simplification

```python
class GraphState(TypedDict):
    workflow_dir: str
    session_id: str
    routing_flag: str
    current_node: str
```

### 2. MemoryManager API

- `get_ultra_short_context(agent_name)`
- `get_short_term(max_entries)`
- `append_short_term(entry, max_window)`
- `append_medium_term(summary)`
- `get_medium_term_recent(n)`
- `search_long_term(query)`
- `get_long_term_detail(meta_id)`

### 3. File Locking

使用 `fcntl.flock` 实现文件级锁，防止并发冲突。

## Implementation Plan

1. 实现新的 MemoryManager
2. 更新 Parser 支持新的配置格式
3. 重写 Compiler 集成 MemoryManager
4. 创建测试用例
5. 更新文档和示例
