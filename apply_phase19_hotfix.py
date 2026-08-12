from pathlib import Path

path = Path(__file__).resolve().parent / "champions_phase18_4.py"
text = path.read_text(encoding="utf-8")
if "\nimport math\n" not in text:
    marker = "from __future__ import annotations\n"
    if marker not in text:
        raise RuntimeError("Could not locate import anchor in champions_phase18_4.py")
    text = text.replace(marker, marker + "import math\n", 1)
    path.write_text(text, encoding="utf-8")
print("Phase 19 hotfix: math import verified")
