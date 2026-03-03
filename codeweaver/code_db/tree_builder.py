"""
Code tree builder for generating hierarchical project structure.

This module creates a compact, hierarchical representation of a codebase
without reading full file contents, making it scalable for large projects.
"""

import ast
from pathlib import Path
from dataclasses import dataclass, field


@dataclass
class CodeNode:
    """Represents a node in the code tree (file, class, function, etc.)."""
    name: str
    type: str  # 'directory', 'file', 'class', 'function', 'method'
    signature: str | None = None
    children: list['CodeNode'] = field(default_factory=list)
    line_number: int | None = None


class CodeTreeBuilder:
    """Builds hierarchical code tree from project directory."""

    def __init__(self, project_root: str | Path, exclude_patterns: list[str] | None = None):
        self.project_root = Path(project_root)
        self.exclude_patterns = exclude_patterns or [
            '__pycache__', '.git', '.venv', 'venv', 'node_modules',
            '.pytest_cache', '.mypy_cache', 'dist', 'build', '*.pyc'
        ]

    def should_exclude(self, path: Path) -> bool:
        """Check if path should be excluded."""
        for pattern in self.exclude_patterns:
            if pattern.startswith('*.'):
                if path.suffix == pattern[1:]:
                    return True
            elif pattern in path.parts:
                return True
        return False

    def build_tree(self) -> CodeNode:
        """Build complete code tree from project root."""
        root = CodeNode(name=self.project_root.name, type='directory')
        self._build_directory_tree(self.project_root, root)
        return root

    def _build_directory_tree(self, directory: Path, parent_node: CodeNode):
        """Recursively build directory tree."""
        try:
            items = sorted(directory.iterdir(), key=lambda p: (not p.is_dir(), p.name))
        except PermissionError:
            return

        for item in items:
            if self.should_exclude(item):
                continue

            if item.is_dir():
                dir_node = CodeNode(name=item.name, type='directory')
                parent_node.children.append(dir_node)
                self._build_directory_tree(item, dir_node)
            elif item.is_file():
                file_node = self._build_file_node(item)
                if file_node:
                    parent_node.children.append(file_node)

    def _build_file_node(self, file_path: Path) -> CodeNode | None:
        """Build node for a single file."""
        file_node = CodeNode(name=file_path.name, type='file')

        # Only parse Python files for structure
        if file_path.suffix == '.py':
            try:
                content = file_path.read_text(encoding='utf-8')
                tree = ast.parse(content)
                self._extract_python_structure(tree, file_node)
            except (SyntaxError, UnicodeDecodeError):
                # If file can't be parsed, just include it without structure
                pass

        return file_node

    def _extract_python_structure(self, tree: ast.AST, parent_node: CodeNode):
        """Extract classes and functions from Python AST."""
        for node in ast.iter_child_nodes(tree):
            if isinstance(node, ast.ClassDef):
                class_node = self._build_class_node(node)
                parent_node.children.append(class_node)
            elif isinstance(node, ast.FunctionDef) or isinstance(node, ast.AsyncFunctionDef):
                func_node = self._build_function_node(node, is_method=False)
                parent_node.children.append(func_node)

    def _build_class_node(self, node: ast.ClassDef) -> CodeNode:
        """Build node for a class."""
        bases = [self._get_name(base) for base in node.bases]
        signature = f"class {node.name}({', '.join(bases)})" if bases else f"class {node.name}"

        class_node = CodeNode(
            name=node.name,
            type='class',
            signature=signature,
            line_number=node.lineno
        )

        # Extract methods
        for item in node.body:
            if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                method_node = self._build_function_node(item, is_method=True)
                class_node.children.append(method_node)

        return class_node

    def _build_function_node(self, node: ast.FunctionDef | ast.AsyncFunctionDef, is_method: bool) -> CodeNode:
        """Build node for a function or method."""
        # Extract parameter names
        args = []
        for arg in node.args.args:
            args.append(arg.arg)

        # Build signature
        async_prefix = "async " if isinstance(node, ast.AsyncFunctionDef) else ""
        signature = f"{async_prefix}def {node.name}({', '.join(args)})"

        return CodeNode(
            name=node.name,
            type='method' if is_method else 'function',
            signature=signature,
            line_number=node.lineno
        )

    def _get_name(self, node: ast.AST) -> str:
        """Get name from AST node."""
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            return f"{self._get_name(node.value)}.{node.attr}"
        return str(node)

    def to_markdown(self, node: CodeNode, indent: int = 0) -> str:
        """Convert code tree to markdown format."""
        lines = []
        prefix = "  " * indent

        if node.type == 'directory':
            lines.append(f"{prefix}📁 **{node.name}/**")
        elif node.type == 'file':
            lines.append(f"{prefix}📄 {node.name}")
        elif node.type == 'class':
            line_info = f" (line {node.line_number})" if node.line_number else ""
            lines.append(f"{prefix}  🔷 `{node.signature}`{line_info}")
        elif node.type in ('function', 'method'):
            line_info = f" (line {node.line_number})" if node.line_number else ""
            icon = "  🔹" if node.type == 'method' else "  🔸"
            lines.append(f"{prefix}{icon} `{node.signature}`{line_info}")

        # Recursively add children
        for child in node.children:
            lines.append(self.to_markdown(child, indent + 1))

        return "\n".join(lines)


def build_code_tree(project_root: str | Path, output_file: str | Path | None = None) -> str:
    """
    Build code tree and optionally save to file.

    Args:
        project_root: Root directory of the project
        output_file: Optional path to save markdown output

    Returns:
        Markdown representation of the code tree
    """
    builder = CodeTreeBuilder(project_root)
    tree = builder.build_tree()
    markdown = builder.to_markdown(tree)

    if output_file:
        Path(output_file).write_text(markdown, encoding='utf-8')

    return markdown
