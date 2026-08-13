from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "app.py"
CONSTANTS = ROOT / "champions" / "constants.py"

app = APP.read_text(encoding="utf-8")
constants = CONSTANTS.read_text(encoding="utf-8")

# Extract the static TYPE_DEFENSES dictionary from app.py.
match = re.search(
    r"^TYPE_DEFENSES\s*=\s*\{.*?^\}\n",
    app,
    flags=re.MULTILINE | re.DOTALL,
)
if not match:
    raise SystemExit("TYPE_DEFENSES was not found in app.py; nothing changed.")

block = match.group(0).rstrip() + "\n\n"

if "TYPE_DEFENSES" not in constants:
    constants = constants.rstrip() + "\n\n" + block

# Add the import if it is not already present.
if "    TYPE_DEFENSES,\n" not in app:
    app = app.replace("    MOVE_DISPLAY_OVERRIDES,\n", "    MOVE_DISPLAY_OVERRIDES,\n    TYPE_DEFENSES,\n", 1)

# Remove the old local definition while keeping TYPE_ORDER and following code.
app = app[:match.start()] + app[match.end():]

APP.write_text(app, encoding="utf-8")
CONSTANTS.write_text(constants, encoding="utf-8")

print("Done: TYPE_DEFENSES moved to champions/constants.py and imported by app.py.")
