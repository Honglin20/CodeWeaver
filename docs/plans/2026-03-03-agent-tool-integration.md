# Agent-Tool Integration Enhancement Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Enhance CodeWeaver's agent-workflow integration by implementing proper tool execution, step-specific context passing, and interactive prompts.

**Architecture:** Create a tool execution framework that agents can invoke through function calling, pass workflow step instructions as structured context to agents, and implement interactive prompt handling with LangGraph interrupts.

**Tech Stack:** Python 3.10+, LangGraph (interrupts), litellm (function calling), pytest

---

## Summary of Changes

This plan addresses four critical limitations:

1. **Tool Execution Framework** - Create ToolExecutor with sandboxing and function calling schemas
2. **Step Context Passing** - Pass workflow step instructions directly to agents
3. **Agent-Tool Integration** - Implement tool execution loop in node_factory
4. **Interactive Prompts** - Implement @tool:select using LangGraph interrupts

**Expected Outcome:** Agents will receive clear step instructions, execute tools properly, and support interactive user prompts.

---

### Task 1: Create Tool Execution Framework

**Goal:** Build a safe tool execution system with OpenAI function calling schemas.

**Files:**
- Create: `codeweaver/tools/executor.py`
- Test: `tests/test_tool_executor.py`

**Implementation:**

Create ToolExecutor class that:
- Wraps existing tools (run_command, read_file, list_files)
- Validates paths to prevent directory traversal
- Returns structured ToolResult with success/error
- Provides OpenAI function calling schemas

**Key Code:**

```python
# codeweaver/tools/executor.py
from dataclasses import dataclass
from pathlib import Path
from codeweaver.tools.filesystem import run_command, read_file, list_files

@dataclass
class ToolResult:
    success: bool
    output: Any = None
    error: str | None = None

class ToolExecutor:
    def __init__(self, project_root: str, memory_root: str | None = None):
        self.project_root = Path(project_root)
        self.tools = {
            "run_command": self._run_command,
            "read_file": self._read_file,
            "list_files": self._list_files,
        }
    
    def execute(self, tool_name: str, params: dict) -> ToolResult:
        if tool_name not in self.tools:
            return ToolResult(success=False, error=f"Unknown tool: {tool_name}")
        try:
            output = self.tools[tool_name](**params)
            return ToolResult(success=True, output=output)
        except Exception as e:
            return ToolResult(success=False, error=str(e))
    
    def get_tool_schemas(self) -> list[dict]:
        # Return OpenAI function calling schemas
        pass
```

**Tests:**
- test_tool_executor_runs_command
- test_tool_executor_reads_file
- test_tool_executor_handles_unknown_tool

**Commit:** "feat: add tool execution framework with sandboxing"

---

### Task 2: Pass Step Context to Agents

**Goal:** Agents receive workflow step instructions, not just generic prompts.

**Files:**
- Modify: `codeweaver/engine/node_factory.py`
- Modify: `codeweaver/engine/compiler.py`
- Modify: `codeweaver/engine/executor.py`
- Test: `tests/test_node_factory.py`

**Implementation:**

1. Add `step_goal` and `step_raw_text` parameters to `make_node()`
2. Build structured context with step instructions
3. Pass workflow steps through compiler chain

**Key Changes:**

```python
# node_factory.py
def make_node(
    agent_def: AgentDef,
    memory: MemoryManager,
    total_steps: int,
    llm_fn: Callable | None = None,
    step_goal: str = "",
    step_raw_text: str = "",
) -> Callable:
    def node(state: dict) -> dict:
        context_parts = [
            "# Current Step Context",
            f"**Goal:** {step_goal}",
            f"**Instructions:**\n{step_raw_text}",
            "\n# Memory Context",
            bundle
        ]
        messages = [
            {"role": "system", "content": agent_def.system_prompt},
            {"role": "user", "content": "\n\n".join(context_parts)},
        ]
        # ... rest
```

**Tests:**
- test_node_receives_step_instructions

**Commit:** "feat: pass step-specific context to agents"

---

### Task 3: Integrate Tool Execution with Agents

**Goal:** Agents can execute tools through function calling loop.

**Files:**
- Modify: `codeweaver/engine/node_factory.py`
- Modify: `codeweaver/engine/compiler.py`
- Modify: `codeweaver/engine/executor.py`
- Test: `tests/test_agent_tool_integration.py`

**Implementation:**

1. Initialize ToolExecutor in node function
2. Pass tool schemas to LLM
3. Implement tool execution loop (max 5 iterations)
4. Parse tool calls from LLM response
5. Execute tools and inject results back

**Key Code:**

```python
# node_factory.py
def node(state: dict) -> dict:
    # Initialize tool executor
    tool_executor = ToolExecutor(project_root=project_root)
    tool_schemas = tool_executor.get_tool_schemas() if agent_def.tools else []
    
    # Tool execution loop
    for iteration in range(MAX_TOOL_ITERATIONS):
        response = llm_fn(messages, tools=tool_schemas)
        
        # Parse tool calls
        tool_calls = extract_tool_calls(response)
        if not tool_calls:
            break
        
        # Execute tools
        for tool_call in tool_calls:
            result = tool_executor.execute(tool_call.name, tool_call.args)
            messages.append({"role": "tool", "content": result})
```

**Tests:**
- test_agent_can_execute_tools

**Commit:** "feat: integrate tool execution with agents"

---

### Task 4: Implement Interactive Prompts

**Goal:** Support @tool:select for user interaction.

**Files:**
- Create: `codeweaver/tools/interactive.py`
- Modify: `codeweaver/tools/executor.py`
- Test: `tests/test_interactive_tools.py`

**Implementation:**

1. Create InteractiveToolHandler
2. Use LangGraph Command to trigger interrupts
3. Integrate with ToolExecutor
4. Add tool_select to schemas

**Key Code:**

```python
# interactive.py
from langgraph.types import Command

class InteractiveToolHandler:
    def handle_select(self, prompt: str, options: list[str]) -> Command:
        if len(options) < 2:
            raise ValueError("tool:select requires at least 2 options")
        
        return Command(
            graph=Command.PARENT,
            update={"__interrupt__": {
                "type": "select",
                "prompt": prompt,
                "options": options
            }}
        )
```

**Tests:**
- test_interactive_select_creates_interrupt
- test_interactive_select_validates_options

**Commit:** "feat: implement interactive tool:select prompts"

---

### Task 5: Add Integration Tests

**Goal:** Verify full workflow execution with tools.

**Files:**
- Create: `tests/test_workflow_integration.py`

**Implementation:**

Create end-to-end test that:
1. Sets up test project with files
2. Creates agent with tools
3. Defines workflow that uses tools
4. Executes workflow with mock LLM
5. Verifies tool execution and results

**Tests:**
- test_workflow_with_tools_executes

**Commit:** "test: add integration test for workflow with tools"

---

### Task 6: Update Documentation

**Goal:** Document new tool execution capabilities.

**Files:**
- Modify: `README.md`
- Modify: `docs/optimizer-workflow-guide.md`

**Implementation:**

Add sections covering:
1. Tool execution architecture
2. How agents use function calling
3. Tool sandboxing and security
4. Interactive prompt usage
5. Example workflows with tools

**Commit:** "docs: document tool execution and interactive prompts"

---

### Task 7: Update Existing Agents

**Goal:** Update agent definitions to use new tool system.

**Files:**
- Modify: `tests/fixtures/agents/interact-agent.yaml`
- Modify: `tests/fixtures/agents/coder-agent.yaml`
- Modify: `tests/fixtures/agents/structure-agent.yaml`

**Implementation:**

Update agent YAML files to:
1. Specify tools they need
2. Update system prompts to mention tool usage
3. Remove manual tool instructions

**Example:**

```yaml
name: interact-agent
tools:
  - tool_select
  - run_command
system_prompt: |
  You coordinate user interaction.
  Use tool_select to present options.
  Use run_command to execute programs.
```

**Commit:** "refactor: update agent definitions for new tool system"

---

### Task 8: Run Full Optimizer Workflow Test

**Goal:** Verify optimizer workflow works end-to-end.

**Files:**
- Test: Manual execution of optimizer workflow

**Steps:**

1. Navigate to test project:
   ```bash
   cd tests/fixtures/slow_sort_project
   ```

2. Clean previous runs:
   ```bash
   rm -rf .codeweaver/checkpoints.db .codeweaver/runs.yaml .codeweaver/memory/
   ```

3. Run workflow:
   ```bash
   codeweaver run optimizer.md
   ```

4. Verify:
   - Agents receive step instructions
   - Tools execute successfully
   - Memory files created with meaningful content
   - No generic "please provide information" responses

**Expected Output:**
- Structure agent analyzes project
- Interact agent uses tool_select for user choices
- Coder agent uses read_file and run_command
- Validator agent compares outputs

**Commit:** "test: verify optimizer workflow with new tool system"

---

## Verification Checklist

After completing all tasks:

- [ ] All unit tests pass: `pytest tests/ -v`
- [ ] Tool executor validates paths correctly
- [ ] Agents receive step-specific instructions
- [ ] Tool execution loop works (max 5 iterations)
- [ ] Interactive prompts trigger interrupts
- [ ] Integration test passes
- [ ] Documentation updated
- [ ] Optimizer workflow executes without errors
- [ ] Agent context files contain meaningful responses
- [ ] No "please provide information" generic responses

---

## Architecture Improvements

This plan improves:

1. **Robustness:**
   - Path validation prevents directory traversal
   - Tool execution has timeout and error handling
   - MAX_TOOL_ITERATIONS prevents infinite loops

2. **Extensibility:**
   - ToolExecutor easily extended with new tools
   - Tool schemas follow OpenAI standard
   - InteractiveToolHandler can support more prompt types

3. **Functionality:**
   - Agents execute real tools instead of asking for info
   - Step instructions provide clear context
   - Interactive prompts enable user guidance

---

## Testing Strategy

**Unit Tests:**
- Test each component in isolation
- Mock LLM responses
- Verify error handling

**Integration Tests:**
- Test full workflow execution
- Use realistic agent definitions
- Verify end-to-end behavior

**Manual Tests:**
- Run optimizer workflow
- Verify user experience
- Check memory file contents

---

## Rollback Plan

If issues arise:

1. Each task is independently committable
2. Can revert individual commits
3. Tests verify each component works
4. Integration test catches breaking changes

---

## Future Enhancements

After this plan:

1. Add more tools (write_file, edit_code, semantic_search)
2. Implement tool:debugger for breakpoints
3. Add tool execution metrics and logging
4. Support parallel tool execution
5. Add tool result caching

