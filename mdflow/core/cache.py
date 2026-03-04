"""Compilation cache for workflow graphs."""
import hashlib
import pickle
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime
import json


class CompilationCache:
    """Cache compiled workflow graphs to avoid recompilation."""

    def __init__(self, cache_dir: str = ".cache/compiled"):
        """Initialize compilation cache.

        Args:
            cache_dir: Directory to store cached compiled graphs
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._metadata_file = self.cache_dir / "metadata.json"
        self._metadata = self._load_metadata()

    def _load_metadata(self) -> Dict[str, Any]:
        """Load cache metadata."""
        if self._metadata_file.exists():
            return json.loads(self._metadata_file.read_text())
        return {}

    def _save_metadata(self):
        """Save cache metadata."""
        self._metadata_file.write_text(json.dumps(self._metadata, indent=2))

    def _compute_hash(self, workflow_dir: str) -> str:
        """Compute hash of workflow files.

        Args:
            workflow_dir: Workflow directory path

        Returns:
            SHA256 hash of all workflow files
        """
        workflow_path = Path(workflow_dir)
        hasher = hashlib.sha256()

        # Hash flow.md
        flow_file = workflow_path / "flow.md"
        if flow_file.exists():
            hasher.update(flow_file.read_bytes())

        # Hash all agent files
        agents_dir = workflow_path / "agents"
        if agents_dir.exists():
            for agent_file in sorted(agents_dir.glob("*.md")):
                hasher.update(agent_file.read_bytes())

        return hasher.hexdigest()

    def get(self, workflow_dir: str) -> Optional[Any]:
        """Get cached compiled graph.

        Args:
            workflow_dir: Workflow directory path

        Returns:
            Cached compiled graph or None if not found/invalid
        """
        workflow_hash = self._compute_hash(workflow_dir)
        cache_file = self.cache_dir / f"{workflow_hash}.pkl"

        if not cache_file.exists():
            return None

        # Check if cache is still valid
        if workflow_hash not in self._metadata:
            return None

        metadata = self._metadata[workflow_hash]
        workflow_path = Path(workflow_dir)

        # Check if any file has been modified since cache
        cache_time = datetime.fromisoformat(metadata["cached_at"])

        flow_file = workflow_path / "flow.md"
        if flow_file.exists():
            if datetime.fromtimestamp(flow_file.stat().st_mtime) > cache_time:
                return None

        agents_dir = workflow_path / "agents"
        if agents_dir.exists():
            for agent_file in agents_dir.glob("*.md"):
                if datetime.fromtimestamp(agent_file.stat().st_mtime) > cache_time:
                    return None

        # Load cached graph
        try:
            with open(cache_file, 'rb') as f:
                return pickle.load(f)
        except Exception:
            # Cache corrupted, remove it
            cache_file.unlink()
            if workflow_hash in self._metadata:
                del self._metadata[workflow_hash]
                self._save_metadata()
            return None

    def set(self, workflow_dir: str, compiled_graph: Any):
        """Cache compiled graph.

        Args:
            workflow_dir: Workflow directory path
            compiled_graph: Compiled graph to cache
        """
        workflow_hash = self._compute_hash(workflow_dir)
        cache_file = self.cache_dir / f"{workflow_hash}.pkl"

        # Save compiled graph
        with open(cache_file, 'wb') as f:
            pickle.dump(compiled_graph, f)

        # Update metadata
        self._metadata[workflow_hash] = {
            "workflow_dir": str(workflow_dir),
            "cached_at": datetime.now().isoformat(),
            "cache_file": str(cache_file)
        }
        self._save_metadata()

    def clear(self, workflow_dir: Optional[str] = None):
        """Clear cache.

        Args:
            workflow_dir: If provided, clear only this workflow's cache.
                         If None, clear all cache.
        """
        if workflow_dir:
            workflow_hash = self._compute_hash(workflow_dir)
            cache_file = self.cache_dir / f"{workflow_hash}.pkl"
            if cache_file.exists():
                cache_file.unlink()
            if workflow_hash in self._metadata:
                del self._metadata[workflow_hash]
                self._save_metadata()
        else:
            # Clear all cache
            for cache_file in self.cache_dir.glob("*.pkl"):
                cache_file.unlink()
            self._metadata = {}
            self._save_metadata()

    def stats(self) -> Dict[str, Any]:
        """Get cache statistics.

        Returns:
            Dictionary with cache statistics
        """
        cache_files = list(self.cache_dir.glob("*.pkl"))
        total_size = sum(f.stat().st_size for f in cache_files)

        return {
            "cached_workflows": len(self._metadata),
            "cache_files": len(cache_files),
            "total_size_bytes": total_size,
            "total_size_mb": round(total_size / (1024 * 1024), 2),
            "cache_dir": str(self.cache_dir)
        }


# Global cache instance
_cache = None


def get_compilation_cache() -> CompilationCache:
    """Get global compilation cache instance."""
    global _cache
    if _cache is None:
        _cache = CompilationCache()
    return _cache
