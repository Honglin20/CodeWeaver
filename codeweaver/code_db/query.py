from pathlib import Path
import re
from typing import Callable


def get_file_list(code_db_root: Path) -> str:
    return (code_db_root / "index.md").read_text()


def get_file_dependencies(code_db_root: Path, file_path: str) -> str:
    for line in (code_db_root / "index.md").read_text().splitlines():
        if line.startswith(f"- {file_path}:"):
            return line
    return f"- {file_path}: no imports found"


def _symbol_path(code_db_root: Path, file_path: str) -> Path:
    escaped = file_path.replace("/", "__").replace("\\", "__")
    if escaped.endswith(".py"):
        escaped = escaped[:-3]
    return code_db_root / "symbols" / f"{escaped}.md"


def get_file_symbols(code_db_root: Path, file_path: str) -> str:
    text = _symbol_path(code_db_root, file_path).read_text()
    # Strip source blocks
    return re.sub(r"\*\*Source:\*\*\n```python\n.*?\n```\n", "", text, flags=re.DOTALL)


def get_symbol_source(code_db_root: Path, file_path: str, symbol: str) -> str:
    text = _symbol_path(code_db_root, file_path).read_text()
    pattern = rf"### {re.escape(symbol)}[^\n]*\n.*?\*\*Source:\*\*\n```python\n(.*?)\n```"
    m = re.search(pattern, text, re.DOTALL)
    return m.group(1) if m else f"Symbol '{symbol}' not found in {file_path}"


def search_symbols(code_db_root: Path, query: str) -> str:
    results = []
    for md in (code_db_root / "symbols").glob("*.md"):
        for line in md.read_text().splitlines():
            if line.startswith("### ") and query.lower() in line.lower():
                results.append(f"{md.stem}: {line[4:]}")
    return "\n".join(results) if results else "No matches found"


def _parse_symbols_from_md(content: str, file_name: str) -> list[dict]:
    """Parse symbols from markdown content."""
    symbols = []
    lines = content.split("\n")

    current_symbol = None
    current_description = None

    for line in lines:
        if line.startswith("### "):
            # Save previous symbol
            if current_symbol:
                symbols.append({
                    "name": current_symbol,
                    "description": current_description or "(no description)",
                    "file": file_name,
                })

            # Start new symbol
            current_symbol = line[4:].strip()
            current_description = None

        elif line.startswith("**Description:**"):
            current_description = line.split("**Description:**")[1].strip()

    # Save last symbol
    if current_symbol:
        symbols.append({
            "name": current_symbol,
            "description": current_description or "(no description)",
            "file": file_name,
        })

    return symbols


def search_symbols_semantic(
    code_db_root: Path,
    query: str,
    llm_fn: Callable[[list[dict]], str],
    top_k: int = 5,
) -> str:
    """
    Semantic search using LLM to rank symbols by relevance.

    Args:
        code_db_root: Root directory of code database
        query: Search query
        llm_fn: LLM function for ranking
        top_k: Number of top results to return

    Returns:
        Markdown with top_k most relevant symbols
    """
    # Get all symbols
    all_symbols = []
    symbols_dir = code_db_root / "symbols"

    if not symbols_dir.exists():
        return "# Semantic Search Results\n\nNo symbols found. Run `codeweaver index` first."

    for symbol_file in symbols_dir.glob("*.md"):
        content = symbol_file.read_text()
        symbols = _parse_symbols_from_md(content, symbol_file.stem)
        all_symbols.extend(symbols)

    if not all_symbols:
        return "# Semantic Search Results\n\nNo symbols found."

    # Build symbol list for LLM
    symbols_text = "\n".join([
        f"{i}. {s['name']} ({s['file']}): {s['description']}"
        for i, s in enumerate(all_symbols)
    ])

    # Ask LLM to rank by relevance
    messages = [
        {
            "role": "user",
            "content": f"""Given this search query: "{query}"

Rank these Python symbols by relevance to the query. Return the top {top_k} most relevant symbol indices as a comma-separated list.

Symbols:
{symbols_text}

Reply with ONLY the indices (e.g., "3,7,12,1,5"), no explanation.""",
        }
    ]

    try:
        response = llm_fn(messages)
        # Parse indices
        indices_str = response.strip().strip('"').strip("'")
        indices = [int(x.strip()) for x in indices_str.split(",") if x.strip().isdigit()][:top_k]
    except Exception as e:
        return f"# Semantic Search Results\n\nError ranking symbols: {e}"

    # Build result markdown
    result = f"# Semantic Search Results for: {query}\n\n"

    if not indices:
        result += "No relevant symbols found.\n"
    else:
        for idx in indices:
            if 0 <= idx < len(all_symbols):
                s = all_symbols[idx]
                result += f"## {s['name']} ({s['file']})\n"
                result += f"{s['description']}\n\n"

    return result

