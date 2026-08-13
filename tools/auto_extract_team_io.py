"""Extract Showdown team I/O helpers from app.py into champions.team_io."""
from pathlib import Path
import ast

APP = Path("app.py")
TARGETS = {"export_slot_to_showdown", "export_team_to_showdown", "parse_showdown_text"}
IMPORT = "from champions.team_io import export_slot_to_showdown, export_team_to_showdown, parse_showdown_text\n"

def main():
    source = APP.read_text(encoding="utf-8")
    tree = ast.parse(source)
    spans = []
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name in TARGETS:
            spans.append((node.lineno - 1, getattr(node, "end_lineno", node.lineno)))
    if not spans:
        print("No Showdown team I/O functions remain in app.py; nothing to do.")
        return
    lines = source.splitlines(keepends=True)
    for start, end in reversed(sorted(spans)):
        del lines[start:end]
    result = "".join(lines)
    if "from champions.team_io import" not in result:
        lines = result.splitlines(keepends=True)
        insert_at = 0
        for i, line in enumerate(lines):
            if line.startswith("from ") or line.startswith("import ") or not line.strip():
                insert_at = i + 1
            else:
                break
        lines.insert(insert_at, IMPORT)
        result = "".join(lines)
    APP.write_text(result, encoding="utf-8")
    print(f"Removed {len(spans)} Showdown I/O functions from app.py.")

if __name__ == "__main__":
    main()
