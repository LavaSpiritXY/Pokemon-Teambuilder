from pathlib import Path
import ast

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "app.py"
MODULE = ROOT / "champions" / "roster_data.py"

text = APP.read_text(encoding="utf-8")
tree = ast.parse(text)

wanted = {"fetch_champions_learnsets", "fetch_champions_pokedex_entries", "display_name_for_species_key"}
functions = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name in wanted]
if len(functions) != len(wanted):
    missing = wanted - {n.name for n in functions}
    raise SystemExit(f"Missing functions: {sorted(missing)}")

functions.sort(key=lambda n: n.lineno)
chunks = [ast.get_source_segment(text, n) for n in functions]
module_text = '''import re\n\nimport requests\nimport streamlit as strlit\n\nfrom champions.constants import SPECIES_DISPLAY_OVERRIDES\n\n''' + "\n\n".join(chunks) + "\n"
MODULE.write_text(module_text, encoding="utf-8")

lines = text.splitlines(keepends=True)
ranges = []
for node in functions:
    end = getattr(node, "end_lineno", None)
    if end is None:
        raise SystemExit(f"No end_lineno for {node.name}")
    ranges.append((node.lineno - 1, end))
for start, end in sorted(ranges, reverse=True):
    del lines[start:end]
new_text = "".join(lines)
needle = "from champions.meta_engine import (\n"
insert = "from champions.roster_data import (\n    fetch_champions_learnsets,\n    fetch_champions_pokedex_entries,\n    display_name_for_species_key,\n)\n\n"
if "from champions.roster_data import" not in new_text:
    new_text = new_text.replace(needle, insert + needle, 1)
APP.write_text(new_text, encoding="utf-8")
print("Extracted roster data helpers")
