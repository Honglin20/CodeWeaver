"""LLM integration for CodeWeaver using litellm."""

import os
from typing import Callable
import litellm


def create_kimi_llm() -> Callable[[list[dict]], str]:
    """Create LLM function using Kimi API (Moonshot)."""
    api_key = os.getenv("KIMI_API", "sk-IA0OXgtva7EmahBVdzkCJgcJxnmo4ja6O0M0M146HniteI3m")
    api_base = os.getenv("KIMI_URL", "https://api.moonshot.cn/v1")

    def llm_fn(messages: list[dict]) -> str:
        """Call Kimi API with messages, return response text."""
        # Use openai/ prefix with custom api_base for Moonshot compatibility
        response = litellm.completion(
            model="openai/moonshot-v1-8k",
            messages=messages,
            api_key=api_key,
            api_base=api_base,
            timeout=30,
        )
        return response.choices[0].message.content.strip()

    return llm_fn
