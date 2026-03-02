from langgraph.types import interrupt

def tool_select(options: list[str], prompt: str) -> str:
    """
    Pause workflow execution and present options to user.
    Uses LangGraph interrupt() — caller must resume with the chosen option.
    """
    return interrupt({"type": "select", "prompt": prompt, "options": options})
