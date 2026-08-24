from pathlib import Path

path = Path("champions/team_analyzer_ui.py")
text = path.read_text(encoding="utf-8")
old = '    height = 12 if compact else 16\n'
new = '    height = 12 if compact else 20\n'
if old not in text:
    raise SystemExit("Expected Team Analyzer score-bar height line was not found.")
text = text.replace(old, new, 1)
path.write_text(text, encoding="utf-8")
