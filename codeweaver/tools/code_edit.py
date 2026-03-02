"""Code editing tool with LibCST and change notification integration."""

from pathlib import Path
from typing import Callable
import libcst as cst


def edit_code(
    file_path: str,
    old_code: str,
    new_code: str,
    memory_root: Path,
    code_db_root: Path,
    project_root: Path,
    llm_fn: Callable[[list[dict]], str] | None = None,
) -> dict:
    """
    Edit code using LibCST, then notify change for re-indexing.

    Args:
        file_path: Path to the file to edit
        old_code: Code to replace
        new_code: New code to insert
        memory_root: Root directory for memory
        code_db_root: Root directory for code database
        project_root: Root directory of the project
        llm_fn: Optional LLM function for generating descriptions

    Returns:
        {"success": bool, "message": str}
    """
    from codeweaver.code_db.watcher import notify_code_change

    path = Path(file_path)

    if not path.exists():
        return {"success": False, "message": f"File not found: {file_path}"}

    try:
        # Read file
        source = path.read_text()

        # Simple string replacement (LibCST transformer would be more robust)
        # For Phase 3, we use simple replacement as the plan suggests
        if old_code not in source:
            return {
                "success": False,
                "message": f"Old code not found in {file_path}",
            }

        new_source = source.replace(old_code, new_code)

        # Validate new source is valid Python
        try:
            cst.parse_module(new_source)
        except Exception as e:
            return {
                "success": False,
                "message": f"New code is not valid Python: {e}",
            }

        # Write back
        path.write_text(new_source)

        # Notify change for re-indexing
        notify_code_change(
            path, "modified", memory_root, code_db_root, project_root, llm_fn
        )

        return {
            "success": True,
            "message": f"Edited {file_path} and updated code database",
        }

    except Exception as e:
        return {"success": False, "message": f"Error editing file: {e}"}


def insert_code(
    file_path: str,
    code: str,
    position: str,  # "start" | "end" | "after:<pattern>"
    memory_root: Path,
    code_db_root: Path,
    project_root: Path,
    llm_fn: Callable[[list[dict]], str] | None = None,
) -> dict:
    """
    Insert code at specified position using LibCST.

    Args:
        file_path: Path to the file
        code: Code to insert
        position: Where to insert ("start", "end", or "after:<pattern>")
        memory_root: Root directory for memory
        code_db_root: Root directory for code database
        project_root: Root directory of the project
        llm_fn: Optional LLM function

    Returns:
        {"success": bool, "message": str}
    """
    from codeweaver.code_db.watcher import notify_code_change

    path = Path(file_path)

    if not path.exists():
        return {"success": False, "message": f"File not found: {file_path}"}

    try:
        source = path.read_text()

        if position == "start":
            new_source = code + "\n" + source
        elif position == "end":
            new_source = source + "\n" + code
        elif position.startswith("after:"):
            pattern = position.split(":", 1)[1]
            if pattern not in source:
                return {"success": False, "message": f"Pattern not found: {pattern}"}
            new_source = source.replace(pattern, pattern + "\n" + code)
        else:
            return {"success": False, "message": f"Invalid position: {position}"}

        # Validate new source
        try:
            cst.parse_module(new_source)
        except Exception as e:
            return {"success": False, "message": f"Invalid Python code: {e}"}

        # Write back
        path.write_text(new_source)

        # Notify change
        notify_code_change(
            path, "modified", memory_root, code_db_root, project_root, llm_fn
        )

        return {
            "success": True,
            "message": f"Inserted code into {file_path} and updated code database",
        }

    except Exception as e:
        return {"success": False, "message": f"Error inserting code: {e}"}
