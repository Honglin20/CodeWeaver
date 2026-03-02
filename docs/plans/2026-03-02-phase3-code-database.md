# Phase 3: Code Database Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a hierarchical Python code database using `ast` + `jedi` + `LibCST`, with LLM-generated symbol descriptions, change notification, and agent-accessible query tools.

**Architecture:** Five-layer tree structure — (1) file list, (2) file dependencies, (3) symbols per file, (4) LLM descriptions, (5) source code. All stored as markdown in `.codeweaver/code_db/`. Agents query via tools. Changes trigger re-indexing and memory notifications.

**Tech Stack:** `ast`, `jedi`, `LibCST`, `litellm`, existing Phase 1/2 APIs.

---

## Phase 3 Scope (from design.md)

**Deliverables:**
- `codeweaver index <project_dir>` — builds `.codeweaver/code_db/`
- Uses `ast` for symbol extraction (functions, classes, variables)
- Uses `jedi` for cross-reference analysis (imports, call graphs)
- LLM generates short descriptions for each symbol
- `query_code_db` tool available to all agents
- Change notification: when coder-agent modifies a file, re-indexes affected symbols and notifies other active agents via memory

**Note:** Phase 1 already implemented basic code_db (Task 4). Phase 3 enhances it with:
1. LLM-generated descriptions (not placeholder "(no description)")
2. Change notification system
3. Integration with coder-agent for auto-reindexing
4. Enhanced query tools with semantic search (optional chromadb)

---

## Task 1: Enhance Code Database Builder with LLM Descriptions

**Files:**
- Modify: `codeweaver/code_db/builder.py`
- Test: `tests/test_code_db.py` (add new tests)

### What to enhance

Phase 1 implementation uses `llm_describe_fn=None` → descriptions are "(no description)".

Phase 3 enhancement:
- Accept real `llm_fn` parameter
- For each symbol (function/class/variable), call LLM with:
  - Symbol name
  - Symbol type (function/class/variable)
  - Source code
  - Context (file path, surrounding symbols)
- LLM returns one-sentence description
- Cache descriptions to avoid re-generating on unchanged symbols

### Implementation

```python
# codeweaver/code_db/builder.py

def build_index(
    project_root: Path,
    output_root: Path,
    llm_fn: Callable[[list[dict]], str] | None = None,
) -> None:
    """
    Builds .codeweaver/code_db/ structure with LLM-generated descriptions.
    
    If llm_fn is None, descriptions are "(no description)".
    If llm_fn is provided, generates descriptions for all symbols.
    """
    # ... existing file discovery code ...
    
    for py_file in python_files:
        symbols = _extract_symbols(py_file)
        
        for symbol in symbols:
            if llm_fn:
                description = _generate_description(symbol, llm_fn)
            else:
                description = "(no description)"
            
            symbol.description = description
        
        _write_symbol_file(py_file, symbols, output_root)

def _generate_description(symbol: Symbol, llm_fn: Callable) -> str:
    """Generate one-sentence description for a symbol using LLM."""
    messages = [{
        "role": "user",
        "content": f"""Describe this Python {symbol.type} in one sentence (max 100 chars):

Name: {symbol.name}
Type: {symbol.type}
Source:
```python
{symbol.source[:500]}  # truncate long source
```

Reply with ONLY the description, no extra text."""
    }]
    return llm_fn(messages).strip()
```

### Tests

```python
# tests/test_code_db.py (add these)

def test_llm_description_generation(tmp_path):
    """Test that LLM descriptions are generated when llm_fn is provided."""
    # Create test project
    src = tmp_path / "src"
    src.mkdir()
    (src / "main.py").write_text("def hello(): return 'world'")
    
    # Mock LLM
    def mock_llm(msgs):
        return "Returns a greeting string"
    
    # Build index with LLM
    code_db = tmp_path / "code_db"
    build_index(src, code_db, llm_fn=mock_llm)
    
    # Check description was generated
    symbols_file = code_db / "symbols" / "src__main.md"
    content = symbols_file.read_text()
    assert "Returns a greeting string" in content
    assert "(no description)" not in content

def test_description_caching(tmp_path):
    """Test that descriptions are cached and not regenerated for unchanged symbols."""
    # Build index twice, count LLM calls
    call_count = [0]
    def counting_llm(msgs):
        call_count[0] += 1
        return "Test description"
    
    src = tmp_path / "src"
    src.mkdir()
    (src / "main.py").write_text("def hello(): pass")
    
    code_db = tmp_path / "code_db"
    build_index(src, code_db, llm_fn=counting_llm)
    first_count = call_count[0]
    
    # Build again without changes
    build_index(src, code_db, llm_fn=counting_llm)
    second_count = call_count[0]
    
    # Should not call LLM again for unchanged symbols
    assert second_count == first_count
```

---

## Task 2: Change Notification System

**Files:**
- Create: `codeweaver/code_db/watcher.py`
- Test: `tests/test_watcher.py`

### What it does

When coder-agent modifies a file:
1. Detect which file was changed
2. Re-index that file's symbols
3. Write notification to memory: `.codeweaver/memory/notifications/code_change.md`
4. Other agents can read this notification to know what changed

### Implementation

```python
# codeweaver/code_db/watcher.py

from pathlib import Path
from datetime import datetime

def notify_code_change(
    file_path: Path,
    change_type: str,  # "modified" | "created" | "deleted"
    memory_root: Path,
    code_db_root: Path,
    llm_fn: Callable | None = None,
) -> None:
    """
    Notify that a code file changed. Re-indexes the file and writes notification.
    """
    # Re-index the changed file
    if change_type in ["modified", "created"]:
        from codeweaver.code_db.builder import _extract_symbols, _write_symbol_file
        symbols = _extract_symbols(file_path)
        # Generate descriptions if llm_fn provided
        for symbol in symbols:
            if llm_fn:
                symbol.description = _generate_description(symbol, llm_fn)
        _write_symbol_file(file_path, symbols, code_db_root)
    
    # Write notification to memory
    notif_dir = memory_root / "notifications"
    notif_dir.mkdir(parents=True, exist_ok=True)
    
    notif_file = notif_dir / "code_changes.md"
    timestamp = datetime.now().isoformat()
    
    entry = f"""
## {timestamp}
- File: {file_path}
- Change: {change_type}
- Symbols updated: {len(symbols) if change_type != "deleted" else 0}
"""
    
    # Append to notification file
    if notif_file.exists():
        content = notif_file.read_text()
    else:
        content = "# Code Change Notifications\n"
    
    notif_file.write_text(content + entry)
```

### Tests

```python
# tests/test_watcher.py

def test_notify_code_change_reindexes(tmp_path):
    """Test that notify_code_change re-indexes the changed file."""
    src = tmp_path / "src"
    src.mkdir()
    main_py = src / "main.py"
    main_py.write_text("def old(): pass")
    
    code_db = tmp_path / "code_db"
    memory = tmp_path / "memory"
    
    # Initial index
    build_index(src, code_db)
    
    # Modify file
    main_py.write_text("def new(): pass")
    
    # Notify change
    notify_code_change(main_py, "modified", memory, code_db)
    
    # Check symbols were updated
    symbols_file = code_db / "symbols" / "src__main.md"
    content = symbols_file.read_text()
    assert "def new()" in content
    assert "def old()" not in content

def test_notification_written_to_memory(tmp_path):
    """Test that notification is written to memory/notifications/."""
    src = tmp_path / "src"
    src.mkdir()
    main_py = src / "main.py"
    main_py.write_text("def hello(): pass")
    
    memory = tmp_path / "memory"
    code_db = tmp_path / "code_db"
    
    notify_code_change(main_py, "modified", memory, code_db)
    
    notif_file = memory / "notifications" / "code_changes.md"
    assert notif_file.exists()
    content = notif_file.read_text()
    assert str(main_py) in content
    assert "modified" in content
```

---

## Task 3: Integrate with Coder-Agent

**Files:**
- Modify: `codeweaver/tools/filesystem.py` (or create new `codeweaver/tools/code_edit.py`)
- Test: `tests/test_code_edit.py`

### What to add

New tool: `edit_code` that wraps LibCST editing + change notification.

```python
# codeweaver/tools/code_edit.py

import libcst as cst
from pathlib import Path
from codeweaver.code_db.watcher import notify_code_change

def edit_code(
    file_path: str,
    old_code: str,
    new_code: str,
    memory_root: Path,
    code_db_root: Path,
    llm_fn: Callable | None = None,
) -> dict:
    """
    Edit code using LibCST, then notify change for re-indexing.
    
    Returns {"success": bool, "message": str}
    """
    path = Path(file_path)
    
    # Read file
    source = path.read_text()
    
    # Parse with LibCST
    tree = cst.parse_module(source)
    
    # Replace old_code with new_code (simplified - real impl uses LibCST transformers)
    new_source = source.replace(old_code, new_code)
    
    # Write back
    path.write_text(new_source)
    
    # Notify change
    notify_code_change(path, "modified", memory_root, code_db_root, llm_fn)
    
    return {"success": True, "message": f"Edited {file_path} and updated code database"}
```

### Tests

```python
# tests/test_code_edit.py

def test_edit_code_updates_file_and_notifies(tmp_path):
    """Test that edit_code modifies file and triggers notification."""
    src = tmp_path / "src"
    src.mkdir()
    main_py = src / "main.py"
    main_py.write_text("def old(): pass")
    
    memory = tmp_path / "memory"
    code_db = tmp_path / "code_db"
    
    # Edit code
    result = edit_code(
        str(main_py),
        "def old(): pass",
        "def new(): pass",
        memory,
        code_db,
    )
    
    assert result["success"]
    assert main_py.read_text() == "def new(): pass"
    
    # Check notification was written
    notif_file = memory / "notifications" / "code_changes.md"
    assert notif_file.exists()
```

---

## Task 4: CLI Integration

**Files:**
- Modify: `codeweaver/cli.py`
- Test: `tests/test_cli_phase3.py`

### Add `index` command

```python
# codeweaver/cli.py

@app.command()
def index(project_dir: str, use_llm: bool = typer.Option(True, "--llm/--no-llm")):
    """Build code database for a Python project."""
    from codeweaver.code_db.builder import build_index
    
    project_path = Path(project_dir)
    if not project_path.exists():
        console.print(f"[red]Directory not found: {project_dir}[/red]")
        raise typer.Exit(1)
    
    code_db_root = _cw_root() / "code_db"
    
    # Use real LLM if --llm flag is set
    llm_fn = _mock_llm_fn if use_llm else None
    
    console.print(f"[cyan]Indexing {project_dir}...[/cyan]")
    build_index(project_path, code_db_root, llm_fn=llm_fn)
    console.print(f"[green]Index written to {code_db_root}[/green]")
```

### Tests

```python
# tests/test_cli_phase3.py

def test_index_command(tmp_path, monkeypatch):
    """Test codeweaver index command."""
    monkeypatch.chdir(tmp_path)
    
    # Create test project
    src = tmp_path / "test_project"
    src.mkdir()
    (src / "main.py").write_text("def hello(): pass")
    
    # Run index command
    from codeweaver.cli import index
    index(str(src), use_llm=False)
    
    # Check code_db was created
    code_db = tmp_path / ".codeweaver" / "code_db"
    assert code_db.exists()
    assert (code_db / "index.md").exists()
```

---

## Task 5: Enhanced Query Tools

**Files:**
- Modify: `codeweaver/code_db/query.py`
- Test: `tests/test_code_db.py` (add query tests)

### Add semantic search (optional)

```python
# codeweaver/code_db/query.py

def search_symbols_semantic(
    code_db_root: Path,
    query: str,
    llm_fn: Callable,
    top_k: int = 5,
) -> str:
    """
    Semantic search using LLM to rank symbols by relevance.
    
    Returns markdown with top_k most relevant symbols.
    """
    # Get all symbols
    all_symbols = []
    symbols_dir = code_db_root / "symbols"
    for symbol_file in symbols_dir.glob("*.md"):
        content = symbol_file.read_text()
        # Parse symbols from markdown
        symbols = _parse_symbols_from_md(content)
        all_symbols.extend(symbols)
    
    # Ask LLM to rank by relevance
    symbols_text = "\n".join([f"{i}. {s.name}: {s.description}" for i, s in enumerate(all_symbols)])
    
    messages = [{
        "role": "user",
        "content": f"""Given this query: "{query}"

Rank these symbols by relevance (return top {top_k} indices, comma-separated):

{symbols_text}

Reply with ONLY the indices, e.g.: 3,7,12,1,5"""
    }]
    
    response = llm_fn(messages)
    indices = [int(x.strip()) for x in response.split(",")][:top_k]
    
    # Return top symbols as markdown
    result = f"# Semantic Search Results for: {query}\n\n"
    for idx in indices:
        if idx < len(all_symbols):
            s = all_symbols[idx]
            result += f"## {s.name}\n{s.description}\n\n"
    
    return result
```

---

## Execution Order

```
Task 1 (LLM descriptions) → Task 2 (Change notification) → Task 3 (Coder integration) → Task 4 (CLI) → Task 5 (Semantic search)
```

Tasks 1-2 can be built in parallel.
Tasks 3-5 depend on 1-2.

---

## Verification

```bash
# Unit tests
pytest tests/test_code_db.py tests/test_watcher.py tests/test_code_edit.py tests/test_cli_phase3.py -v

# Full suite (76 Phase 1+2 + Phase 3 tests)
pytest tests/ -v

# Manual E2E
codeweaver index tests/fixtures/slow_sort_project/src --llm
# Expected: builds code_db with LLM descriptions

# Test change notification
# (modify a file, check notifications/code_changes.md)
```

---

## Documentation

Create `docs/phase3-usage.md`:

```markdown
# Phase 3: Code Database Usage

## Indexing a Project

```bash
codeweaver index <project_dir>          # with LLM descriptions
codeweaver index <project_dir> --no-llm # without LLM (faster)
```

## Query Tools (for agents)

Available in agent tool definitions:

```yaml
tools:
  - query_code_db        # search symbols by name
  - get_file_symbols     # get all symbols in a file
  - get_symbol_source    # get source code for a symbol
```

## Change Notifications

When coder-agent modifies code:
1. File is automatically re-indexed
2. Notification written to `.codeweaver/memory/notifications/code_changes.md`
3. Other agents can read notifications to stay updated

## Memory Structure

```
.codeweaver/
├── code_db/
│   ├── index.md              # file list + dependencies
│   └── symbols/
│       └── src__main.md      # symbols with LLM descriptions
└── memory/
    └── notifications/
        └── code_changes.md   # change log
```
```
