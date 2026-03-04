# Execution Display Layer Design

**Date:** 2026-03-04
**Status:** Approved
**Approach:** B - Add Execution Layer

## Problem Statement

CodeWeaver's current workflow execution has several critical UX issues:

1. **Poor Overview Display**: The workflow overview shows too much detail upfront, making it hard to see the big picture
2. **Missing Step Feedback**: Steps execute silently without showing what's happening or what was accomplished
3. **No Interactive Tool Support**: Tools like `@tool:select` don't properly pause and wait for user input
4. **Noisy Error Messages**: LiteLLM debug messages clutter the output
5. **No Progress Tracking**: Users can't see which step is currently executing or how far along they are

## User Requirements

Based on user feedback, the execution experience should:

- Show a **progress bar with step list** at workflow start
- Display **real-time step progress**: "🔄 Executing Step X..." → "✓ Step X completed: [summary]"
- **Automatically pause** when interactive tools need user input
- **Suppress LiteLLM debug output**, show only friendly error messages
- Reference: Claude Code's task list and execution feedback model

## Design Overview

### Architecture

We'll introduce a clean separation between execution logic and display/feedback:

```
┌─────────────────────────────────────────┐
│         WorkflowExecutor                │
│  (orchestrates workflow execution)      │
└──────────────┬──────────────────────────┘
               │
               ├─> ExecutionDisplay (new)
               │   - Progress tracking
               │   - Console output
               │   - Step summaries
               │
               └─> LangGraph Nodes
                   - Agent execution
                   - Tool calls
                   - State management
```

### Core Principle

**Separation of Concerns:**
- **Nodes** focus on agent execution and tool calls
- **ExecutionDisplay** handles all user-facing output
- **WorkflowExecutor** coordinates between them

## Component Design

### 1. ExecutionDisplay Class

**Location:** `codeweaver/engine/display.py`

**Purpose:** Centralized display manager for all workflow execution feedback

**Key Responsibilities:**
- Display workflow overview with progress tracking
- Show real-time step execution status
- Format and display tool call feedback
- Extract and present step summaries from LLM output
- Handle interactive tool prompts

**Public API:**

```python
class ExecutionDisplay:
    def __init__(self, console: Console = None):
        """Initialize display with optional console instance"""

    def start_workflow(self, name: str, steps: list[StepInfo]) -> None:
        """Display workflow overview with progress bar

        Args:
            name: Workflow name
            steps: List of StepInfo(index, goal, agents)
        """

    def start_step(self, step_num: int, goal: str, agents: list[str]) -> None:
        """Show step start message with spinner

        Args:
            step_num: Current step number (1-indexed)
            goal: Step goal description
            agents: List of agent names for this step
        """

    def report_tool_call(self, tool_name: str, args_preview: str) -> None:
        """Display tool call in progress

        Args:
            tool_name: Name of the tool being called
            args_preview: Preview of arguments (truncated if long)
        """

    def report_tool_result(
        self,
        tool_name: str,
        success: bool,
        error: str = None
    ) -> None:
        """Display tool execution result

        Args:
            tool_name: Name of the tool
            success: Whether tool succeeded
            error: Error message if failed
        """

    def complete_step(self, step_num: int, summary: str) -> None:
        """Show step completion with summary

        Args:
            step_num: Completed step number
            summary: Brief summary extracted from LLM output
        """

    def complete_workflow(self, success: bool, error: str = None) -> None:
        """Display workflow completion status

        Args:
            success: Whether workflow completed successfully
            error: Error message if failed
        """

    def update_progress(self, current: int, total: int) -> None:
        """Update progress bar

        Args:
            current: Current step number
            total: Total number of steps
        """
```

