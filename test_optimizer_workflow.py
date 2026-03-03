#!/usr/bin/env python3
"""Test optimizer workflow on slow_sort_project."""

import os
import sys
from pathlib import Path

# Set working directory to slow_sort_project
os.chdir(Path(__file__).parent / "tests/fixtures/slow_sort_project")

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from codeweaver.engine.executor import WorkflowExecutor
from codeweaver.parser.workflow import parse_workflow

# Set API credentials
os.environ["CODEWEAVER_API_KEY"] = "sk-IA0OXgtva7EmahBVdzkCJgcJxnmo4ja6O0M0M146HniteI3m"
os.environ["CODEWEAVER_API_BASE"] = "https://api.moonshot.cn/v1"

def create_llm_fn(messages: list[dict], tools: list[dict] | None = None):
    """LLM function for testing."""
    import litellm

    api_key = os.getenv("CODEWEAVER_API_KEY")
    api_base = os.getenv("CODEWEAVER_API_BASE")
    model = os.getenv("CODEWEAVER_MODEL", "moonshot/moonshot-v1-8k")

    kwargs = {
        "model": model,
        "messages": messages,
        "api_key": api_key,
        "api_base": api_base,
    }
    if tools:
        kwargs["tools"] = tools
        kwargs["tool_choice"] = "auto"

    response = litellm.completion(**kwargs)

    # Return full message if tools provided, otherwise just content
    if tools:
        return response.choices[0].message
    else:
        return response.choices[0].message.content

def main():
    # Load workflow
    workflow_file = Path(".codeweaver/simple-optimizer.md")
    if not workflow_file.exists():
        print(f"Error: Workflow file not found: {workflow_file}")
        sys.exit(1)

    workflow = parse_workflow(workflow_file.read_text())

    # Create executor
    cw_root = Path(".codeweaver")
    executor = WorkflowExecutor(cw_root, llm_fn=create_llm_fn)

    # Run workflow
    print("=" * 60)
    print("Testing Optimizer Workflow on slow_sort_project")
    print("=" * 60)
    thread_id = executor.run(workflow)
    print(f"\n{'=' * 60}")
    print(f"Workflow completed! Thread ID: {thread_id}")
    print("=" * 60)

if __name__ == "__main__":
    main()
