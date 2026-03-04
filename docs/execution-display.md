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
