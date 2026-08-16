"""Prepare Showdown team I/O extraction from app.py."""
from pathlib import Path

APP = Path("app.py")

if __name__ == "__main__":
    text = APP.read_text(encoding="utf-8")
    marker = "# -----------------------------------------------------------------------------\n# 6. TAB 7: TEAM OVERVIEW & TEAM EVALUATOR INTEGRATION\n"
    if marker not in text:
        raise SystemExit("Team overview marker not found; refusing to modify files.")
    print("Team I/O extraction target verified.")
