"""Memory manager for agent state persistence."""
from pathlib import Path


class MemoryManager:
    """Manages agent memory across different time horizons."""

    def __init__(self, workspace_path: str):
        """Initialize memory manager.

        Args:
            workspace_path: Root path for memory storage
        """
        self.workspace_path = Path(workspace_path)
        self.workspace_path.mkdir(parents=True, exist_ok=True)
        print(f"[MemoryManager] Initialized at {self.workspace_path}")

    def get_ultra_short_context(self, file_path: str) -> str:
        """Retrieve ultra-short-term context.

        Args:
            file_path: Path to context file

        Returns:
            Context content (mocked)
        """
        print(f"[MemoryManager] Reading ultra-short context: {file_path}")
        return f"Mock ultra-short context from {file_path}"

    def search_long_term_meta(self, query: str) -> str:
        """Search long-term memory metadata.

        Args:
            query: Search query

        Returns:
            Search results (mocked)
        """
        print(f"[MemoryManager] Searching long-term memory: {query}")
        return f"Mock search results for: {query}"

    def append_medium_term_log(self, agent_name: str, log_content: str):
        """Append to medium-term log.

        Args:
            agent_name: Name of the agent
            log_content: Content to log
        """
        log_file = self.workspace_path / f"{agent_name}_log.txt"
        print(f"[MemoryManager] Appending to {log_file}: {log_content[:50]}...")
        with open(log_file, 'a', encoding='utf-8') as f:
            f.write(f"{log_content}\n")
