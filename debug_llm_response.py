#!/usr/bin/env python3
"""Debug script to see what LLM returns."""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from codeweaver.parser.agent import load_agent_registry

# Set API credentials
os.environ["CODEWEAVER_API_KEY"] = "sk-IA0OXgtva7EmahBVdzkCJgcJxnmo4ja6O0M0M146HniteI3m"
os.environ["CODEWEAVER_API_BASE"] = "https://api.moonshot.cn/v1"

def create_llm_fn(messages: list[dict], tools: list[dict] | None = None):
    """LLM function with debugging."""
    import litellm

    api_key = os.getenv("CODEWEAVER_API_KEY")
    api_base = os.getenv("CODEWEAVER_API_BASE")
    model = os.getenv("CODEWEAVER_MODEL", "moonshot/moonshot-v1-8k")

    print(f"\n=== LLM Call ===")
    print(f"Model: {model}")
    print(f"Messages: {len(messages)} messages")
    print(f"Tools: {len(tools) if tools else 0} tools")

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

    print(f"\n=== LLM Response ===")
    print(f"Type: {type(response)}")
    print(f"Content: {response.choices[0].message.content}")
    print(f"Tool calls: {response.choices[0].message.tool_calls}")

    return response.choices[0].message.content

def main():
    # Load structure-agent
    agents_dir = Path("codeweaver/builtin_agents")
    registry = load_agent_registry(agents_dir)

    structure_agent = registry.get("structure-agent")
    if not structure_agent:
        print("Error: structure-agent not found")
        return

    print(f"Agent: {structure_agent.name}")
    print(f"Tools: {structure_agent.tools}")

    # Create a simple test message
    messages = [
        {"role": "system", "content": structure_agent.system_prompt},
        {"role": "user", "content": "Analyze the codeweaver project structure using build_code_tree."}
    ]

    # Call LLM
    response = create_llm_fn(messages, tools=None)
    print(f"\n=== Final Response ===")
    print(response)

if __name__ == "__main__":
    main()
