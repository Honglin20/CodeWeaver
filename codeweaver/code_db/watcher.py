"""Change notification system for code database."""

from pathlib import Path
from datetime import datetime
from typing import Callable


def notify_code_change(
    file_path: Path,
    change_type: str,  # "modified" | "created" | "deleted"
    memory_root: Path,
    code_db_root: Path,
    project_root: Path,
    llm_fn: Callable[[list[dict]], str] | None = None,
) -> None:
    """
    Notify that a code file changed. Re-indexes the file and writes notification.

    Args:
        file_path: Path to the changed file
        change_type: Type of change ("modified", "created", or "deleted")
        memory_root: Root directory for memory (.codeweaver/memory/)
        code_db_root: Root directory for code database (.codeweaver/code_db/)
        project_root: Root directory of the project
        llm_fn: Optional LLM function for generating descriptions
    """
    from codeweaver.code_db.builder import _parse_file, _escape, _sig
    import ast

    symbol_count = 0

    # Re-index the changed file
    if change_type in ["modified", "created"]:
        source = file_path.read_text()
        funcs, classes, variables, imports = _parse_file(source)

        # Generate symbol file
        rel = file_path.relative_to(project_root)
        escaped = _escape(str(rel))
        symbols_dir = code_db_root / "symbols"
        symbols_dir.mkdir(parents=True, exist_ok=True)
        sym_file = symbols_dir / f"{escaped}.md"

        lines = [f"# {rel}\n"]

        if funcs:
            lines.append("## Functions\n")
            for f in funcs:
                sig = _sig(f)
                src = ast.get_source_segment(source, f) or ""

                # Generate description if LLM provided
                if llm_fn:
                    from codeweaver.code_db.builder import _generate_description

                    d = _generate_description(f.name, "function", src, llm_fn)
                else:
                    d = "(no description)"

                lines.append(f"### {sig}\n**Description:** {d}\n**Source:**\n```python\n{src}\n```\n")

        if classes:
            lines.append("## Classes\n")
            for c in classes:
                src = ast.get_source_segment(source, c) or ""

                # Generate description if LLM provided
                if llm_fn:
                    from codeweaver.code_db.builder import _generate_description

                    d = _generate_description(c.name, "class", src, llm_fn)
                else:
                    d = "(no description)"

                lines.append(f"### {c.name}\n**Description:** {d}\n**Source:**\n```python\n{src}\n```\n")

        if variables:
            lines.append("## Variables\n")
            for v in variables:
                lines.append(f"### {v}\n")

        sym_file.write_text("\n".join(lines))
        symbol_count = len(funcs) + len(classes) + len(variables)

    elif change_type == "deleted":
        # Remove symbol file
        rel = file_path.relative_to(project_root)
        escaped = _escape(str(rel))
        sym_file = code_db_root / "symbols" / f"{escaped}.md"
        if sym_file.exists():
            sym_file.unlink()

    # Write notification to memory
    notif_dir = memory_root / "notifications"
    notif_dir.mkdir(parents=True, exist_ok=True)

    notif_file = notif_dir / "code_changes.md"
    timestamp = datetime.now().isoformat()

    entry = f"""
## {timestamp}
- File: {file_path}
- Change: {change_type}
- Symbols updated: {symbol_count}
"""

    # Append to notification file
    if notif_file.exists():
        content = notif_file.read_text()
    else:
        content = "# Code Change Notifications\n"

    notif_file.write_text(content + entry)
