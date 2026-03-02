from pathlib import Path
import ast
import os
import hashlib
import json
from typing import Callable

_EXCLUDE = {"__pycache__", ".venv", "venv", ".git"}


def _escape(file_path: str) -> str:
    return file_path.replace(os.sep, "__").replace("/", "__").removesuffix(".py")


def _sig(node: ast.FunctionDef) -> str:
    args = [a.arg for a in node.args.args]
    defaults = node.args.defaults
    offset = len(args) - len(defaults)
    parts = []
    for i, a in enumerate(args):
        di = i - offset
        if di >= 0:
            parts.append(f"{a}={ast.unparse(defaults[di])}")
        else:
            parts.append(a)
    return f"{node.name}({', '.join(parts)})"


def _set_parents(tree: ast.AST):
    for node in ast.walk(tree):
        for child in ast.iter_child_nodes(node):
            child.parent = node  # type: ignore[attr-defined]


def _parse_file(source: str):
    tree = ast.parse(source)
    _set_parents(tree)
    funcs, classes, variables, imports = [], [], [], []
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and isinstance(node.parent, ast.Module):  # type: ignore[attr-defined]
            funcs.append(node)
        elif isinstance(node, ast.ClassDef) and isinstance(node.parent, ast.Module):  # type: ignore[attr-defined]
            classes.append(node)
        elif isinstance(node, ast.Assign) and isinstance(node.parent, ast.Module):  # type: ignore[attr-defined]
            for t in node.targets:
                if isinstance(t, ast.Name):
                    variables.append(f"{t.id} = {ast.unparse(node.value)}")
        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            if isinstance(node, ast.ImportFrom) and node.module:
                imports.append(node.module)
            else:
                for alias in node.names:
                    imports.append(alias.name)
    return funcs, classes, variables, imports


def _generate_description(
    symbol_name: str, symbol_type: str, source_code: str, llm_fn: Callable[[list[dict]], str]
) -> str:
    """Generate one-sentence description for a symbol using LLM."""
    # Truncate long source code
    truncated_source = source_code[:500] if len(source_code) > 500 else source_code

    messages = [
        {
            "role": "user",
            "content": f"""Describe this Python {symbol_type} in one sentence (max 100 characters):

Name: {symbol_name}
Type: {symbol_type}
Source:
```python
{truncated_source}
```

Reply with ONLY the description, no extra text.""",
        }
    ]

    return llm_fn(messages).strip()


def _load_cache(cache_file: Path) -> dict:
    """Load description cache from JSON file."""
    if cache_file.exists():
        return json.loads(cache_file.read_text())
    return {}


def _save_cache(cache_file: Path, cache: dict) -> None:
    """Save description cache to JSON file."""
    cache_file.parent.mkdir(parents=True, exist_ok=True)
    cache_file.write_text(json.dumps(cache, indent=2))


def _cache_key(symbol_name: str, source_code: str) -> str:
    """Generate cache key from symbol name and source code hash."""
    code_hash = hashlib.md5(source_code.encode()).hexdigest()[:8]
    return f"{symbol_name}:{code_hash}"



def build_index(project_root: Path, output_root: Path, llm_describe_fn: Callable[[list[dict]], str] | None = None) -> None:
    """
    Build code database with optional LLM-generated descriptions.

    Args:
        project_root: Root directory of the project to index
        output_root: Root directory for .codeweaver/ structure
        llm_describe_fn: Optional LLM function that takes messages and returns description.
                        If None, uses "(no description)" placeholder.
    """
    code_db = output_root / "code_db"
    symbols_dir = code_db / "symbols"
    symbols_dir.mkdir(parents=True, exist_ok=True)

    # Load description cache
    cache_file = code_db / ".description_cache.json"
    desc_cache = _load_cache(cache_file) if llm_describe_fn else {}

    py_files = []
    for p in sorted(project_root.rglob("*.py")):
        if any(part in _EXCLUDE for part in p.parts):
            continue
        py_files.append(p)

    file_imports: dict[str, list[str]] = {}

    for path in py_files:
        rel = path.relative_to(project_root)
        escaped = _escape(str(rel))
        sym_file = symbols_dir / f"{escaped}.md"

        # Incremental: skip if symbol file is newer than source
        if sym_file.exists() and sym_file.stat().st_mtime >= path.stat().st_mtime:
            # Still need imports for index.md — parse minimally
            source = path.read_text()
            tree = ast.parse(source)
            imps = []
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom) and node.module:
                    imps.append(node.module)
                elif isinstance(node, ast.Import):
                    for alias in node.names:
                        imps.append(alias.name)
            file_imports[str(rel)] = imps
            continue

        source = path.read_text()
        funcs, classes, variables, imports = _parse_file(source)
        file_imports[str(rel)] = imports

        lines = [f"# {rel}\n"]

        if funcs:
            lines.append("## Functions\n")
            for f in funcs:
                sig = _sig(f)
                src = ast.get_source_segment(source, f) or ""

                # Generate or retrieve cached description
                if llm_describe_fn:
                    cache_k = _cache_key(f.name, src)
                    if cache_k in desc_cache:
                        d = desc_cache[cache_k]
                    else:
                        d = _generate_description(f.name, "function", src, llm_describe_fn)
                        desc_cache[cache_k] = d
                else:
                    d = "(no description)"

                lines.append(f"### {sig}\n**Description:** {d}\n**Source:**\n```python\n{src}\n```\n")

        if classes:
            lines.append("## Classes\n")
            for c in classes:
                src = ast.get_source_segment(source, c) or ""

                # Generate or retrieve cached description
                if llm_describe_fn:
                    cache_k = _cache_key(c.name, src)
                    if cache_k in desc_cache:
                        d = desc_cache[cache_k]
                    else:
                        d = _generate_description(c.name, "class", src, llm_describe_fn)
                        desc_cache[cache_k] = d
                else:
                    d = "(no description)"

                lines.append(f"### {c.name}\n**Description:** {d}\n**Source:**\n```python\n{src}\n```\n")

        if variables:
            lines.append("## Variables\n")
            for v in variables:
                lines.append(f"### {v}\n")

        sym_file.write_text("\n".join(lines))

    # Save updated cache
    if llm_describe_fn:
        _save_cache(cache_file, desc_cache)

    # Write index.md
    idx = ["# File Index\n", "## Files\n"]
    for rel in [str(p.relative_to(project_root)) for p in py_files]:
        idx.append(f"- {rel}\n")

    idx.append("\n## Import Relationships\n")
    for rel, imps in file_imports.items():
        if imps:
            idx.append(f"- {rel}: imports {', '.join(imps)}\n")

    (code_db / "index.md").write_text("".join(idx))

