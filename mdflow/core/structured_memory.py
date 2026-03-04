"""Structured memory manager with four-tier architecture."""
from pathlib import Path
from typing import List, Dict, Optional
import json
import fcntl
from contextlib import contextmanager
from datetime import datetime


class MemoryManager:
    """Manages four-tier structured memory with file locking."""

    def __init__(self, workflow_dir: str, session_id: str):
        self.workflow_dir = Path(workflow_dir)
        self.session_id = session_id
        self.memory_root = self.workflow_dir / "memory"
        self.locks_dir = self.memory_root / ".locks"
        self.locks_dir.mkdir(parents=True, exist_ok=True)

    @contextmanager
    def _file_lock(self, file_path: Path):
        """Context manager for file locking with cleanup."""
        lock_file = self.locks_dir / f"{file_path.name}.lock"
        lock_file.touch(exist_ok=True)

        with open(lock_file, 'w') as f:
            fcntl.flock(f.fileno(), fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)
                try:
                    lock_file.unlink()
                except FileNotFoundError:
                    pass

    # Ultra-Short Memory
    def get_ultra_short_context(self, agent_name: str) -> str:
        """Get ultra-short context from agent config."""
        import frontmatter
        
        agent_file = self.workflow_dir / "agents" / f"{agent_name}.md"
        if not agent_file.exists():
            return ""
        
        post = frontmatter.load(agent_file)
        context_file = post.metadata.get('context_file')
        
        if not context_file:
            return ""
        
        context_path = self.workflow_dir / context_file
        if not context_path.exists():
            return ""
        
        with self._file_lock(context_path):
            return context_path.read_text(encoding='utf-8')

    # Short-Term Memory
    def get_short_term(self, max_entries: int = 10) -> List[Dict]:
        """Get short-term memory (per-session file)."""
        checkpoint_file = self.memory_root / f"checkpoint_{self.session_id}.json"
        
        if not checkpoint_file.exists():
            return []
        
        with self._file_lock(checkpoint_file):
            try:
                data = json.loads(checkpoint_file.read_text())
                return data[-max_entries:]
            except json.JSONDecodeError:
                backup = checkpoint_file.with_suffix('.json.bak')
                checkpoint_file.rename(backup)
                return []

    def append_short_term(self, entry: Dict, max_window: int = 10):
        """Append to short-term memory with sliding window."""
        checkpoint_file = self.memory_root / f"checkpoint_{self.session_id}.json"
        
        with self._file_lock(checkpoint_file):
            try:
                if checkpoint_file.exists():
                    data = json.loads(checkpoint_file.read_text())
                else:
                    data = []
            except json.JSONDecodeError:
                backup = checkpoint_file.with_suffix('.json.bak')
                checkpoint_file.rename(backup)
                data = []
            
            data.append(entry)
            data = data[-max_window:]
            
            checkpoint_file.write_text(json.dumps(data, indent=2, ensure_ascii=False))

    # Medium-Term Memory
    def append_medium_term(self, summary: str):
        """Append to medium-term task logs (JSONL + MD)."""
        timestamp = datetime.now().isoformat()
        
        # Write to JSONL
        jsonl_file = self.memory_root / "medium_term" / "task_logs.jsonl"
        jsonl_file.parent.mkdir(parents=True, exist_ok=True)
        
        entry = {
            "timestamp": timestamp,
            "session_id": self.session_id,
            "summary": summary
        }
        
        with self._file_lock(jsonl_file):
            with open(jsonl_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(entry, ensure_ascii=False) + '\n')
        
        # Render to MD
        md_file = self.memory_root / "medium_term" / "task_logs.md"
        md_entry = f"\n## [{timestamp}] Session: {self.session_id}\n{summary}\n"
        
        with self._file_lock(md_file):
            with open(md_file, 'a', encoding='utf-8') as f:
                f.write(md_entry)

    def get_medium_term_recent(self, n: int = 5) -> List[Dict]:
        """Get recent N task logs from JSONL."""
        jsonl_file = self.memory_root / "medium_term" / "task_logs.jsonl"
        
        if not jsonl_file.exists():
            return []
        
        with self._file_lock(jsonl_file):
            entries = []
            with open(jsonl_file, 'r', encoding='utf-8') as f:
                for line in f:
                    try:
                        entries.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
            
            return entries[-n:]

    # Long-Term Memory
    def search_long_term(self, query: str) -> List[Dict]:
        """Search long-term memory metadata."""
        import re
        
        meta_file = self.memory_root / "long_term" / "system_meta.md"
        
        if not meta_file.exists():
            return []
        
        with self._file_lock(meta_file):
            content = meta_file.read_text(encoding='utf-8')
        
        results = []
        pattern = r'^-\s*\[([^\]]+)\]\s*(.+)$'
        
        for line in content.split('\n'):
            if query.lower() not in line.lower():
                continue
            
            try:
                match = re.match(pattern, line.strip())
                if match:
                    results.append({
                        "id": match.group(1),
                        "desc": match.group(2)
                    })
            except Exception:
                continue
        
        return results

    def get_long_term_detail(self, meta_id: str) -> str:
        """Get detailed content from long-term memory."""
        detail_file = self.memory_root / "long_term" / "details" / f"{meta_id}.md"
        
        if not detail_file.exists():
            return ""
        
        with self._file_lock(detail_file):
            return detail_file.read_text(encoding='utf-8')
