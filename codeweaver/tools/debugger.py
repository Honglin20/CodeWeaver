import libcst as cst
from pathlib import Path


class _BreakpointInserter(cst.CSTTransformer):
    def __init__(self, target_line: int) -> None:
        self._target_line = target_line
        self._current_line = 0
        self._done = False

    def on_visit(self, node: cst.CSTNode) -> bool:
        return True

    def leave_Module(self, original_node: cst.Module, updated_node: cst.Module) -> cst.Module:
        new_body = list(updated_node.body)
        # Find the statement index whose position corresponds to target_line.
        # We re-parse the original to get positions.
        wrapper = cst.metadata.MetadataWrapper(original_node)  # type: ignore[attr-defined]
        positions = wrapper.resolve(cst.metadata.PositionProvider)

        insert_idx = None
        for i, stmt in enumerate(original_node.body):
            pos = positions.get(stmt)
            if pos and pos.start.line >= self._target_line:
                insert_idx = i
                break

        if insert_idx is None:
            return updated_node

        import_stmt = cst.parse_statement("import debugpy\n")
        bp_stmt = cst.parse_statement("debugpy.breakpoint()\n")
        new_body.insert(insert_idx, bp_stmt)
        new_body.insert(insert_idx, import_stmt)
        return updated_node.with_changes(body=new_body)


def insert_breakpoint(file_path: str, line: int) -> None:
    """
    Insert a debugpy breakpoint call before the given line number in file_path.
    Uses LibCST to preserve formatting.
    """
    source = Path(file_path).read_text()
    tree = cst.parse_module(source)
    wrapper = cst.metadata.MetadataWrapper(tree)
    positions = wrapper.resolve(cst.metadata.PositionProvider)

    body = list(tree.body)
    insert_idx = len(body)  # default: append
    for i, stmt in enumerate(body):
        pos = positions.get(stmt)
        if pos and pos.start.line >= line:
            insert_idx = i
            break

    import_stmt = cst.parse_statement("import debugpy\n")
    bp_stmt = cst.parse_statement("debugpy.breakpoint()\n")
    new_body = body[:insert_idx] + [import_stmt, bp_stmt] + body[insert_idx:]
    modified = tree.with_changes(body=new_body)
    Path(file_path).write_text(modified.code)
