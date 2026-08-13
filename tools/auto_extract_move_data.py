from __future__ import annotations

import ast
from pathlib import Path

APP = Path("app.py")
MODULE = Path("champions/move_data.py")

TARGETS = {
    "fetch_master_move_dictionary",
    "get_champions_species_key",
    "get_move_api_slug",
    "get_hardcoded_move_type",
    "fetch_move_type",
    "display_name_for_move",
}


def source_for_node(lines: list[str], node: ast.AST) -> str:
    starts = [getattr(node, "lineno")]
    starts.extend(getattr(d, "lineno") for d in getattr(node, "decorator_list", []))
    start = min(starts) - 1
    end = getattr(node, "end_lineno")
    return "".join(lines[start:end])


def main() -> None:
    text = APP.read_text(encoding="utf-8")
    lines = text.splitlines(keepends=True)
    tree = ast.parse(text)

    nodes: dict[str, ast.AST] = {}
    assignment: ast.AST | None = None

    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name in TARGETS:
            nodes[node.name] = node
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "MASTER_MOVE_DICTIONARY":
                    assignment = node

    missing = TARGETS - nodes.keys()
    if missing or assignment is None:
        raise SystemExit(f"Missing extraction targets: {sorted(missing)} assignment={assignment is not None}")

    ordered = [
        "fetch_master_move_dictionary",
        "MASTER_MOVE_DICTIONARY",
        "get_move_api_slug",
        "get_hardcoded_move_type",
        "fetch_move_type",
        "get_champions_species_key",
        "display_name_for_move",
    ]

    chunks: list[str] = [
        "import re\n",
        "from typing import Dict\n\n",
        "import requests\n",
        "import streamlit as strlit\n\n",
        "from champions.constants import MOVE_DISPLAY_OVERRIDES, MOVE_TYPE_OVERRIDES\n\n",
    ]

    for name in ordered:
        node = assignment if name == "MASTER_MOVE_DICTIONARY" else nodes[name]
        chunks.append(source_for_node(lines, node).rstrip() + "\n\n")

    MODULE.parent.mkdir(parents=True, exist_ok=True)
    MODULE.write_text("".join(chunks).rstrip() + "\n", encoding="utf-8")

    remove_nodes = list(nodes.values()) + [assignment]
    ranges = []
    for node in remove_nodes:
        starts = [getattr(node, "lineno")]
        starts.extend(getattr(d, "lineno") for d in getattr(node, "decorator_list", []))
        start = min(starts) - 1
        end = getattr(node, "end_lineno")
        ranges.append((start, end))

    for start, end in sorted(ranges, reverse=True):
        del lines[start:end]

    new_text = "".join(lines)
    import_anchor = "from champions.meta_utils import ("
    if "from champions.move_data import (" not in new_text:
        insert_at = new_text.index(import_anchor)
        move_import = (
            "from champions.move_data import (\n"
            "    MASTER_MOVE_DICTIONARY,\n"
            "    display_name_for_move,\n"
            "    fetch_master_move_dictionary,\n"
            "    fetch_move_type,\n"
            "    get_champions_species_key,\n"
            "    get_hardcoded_move_type,\n"
            "    get_move_api_slug,\n"
            ")\n\n"
        )
        new_text = new_text[:insert_at] + move_import + new_text[insert_at:]

    APP.write_text(new_text, encoding="utf-8")

    compile_targets = [APP, MODULE]
    for path in compile_targets:
        compile(path)

    print(f"Extracted move/data helpers into {MODULE}")


if __name__ == "__main__":
    main()
