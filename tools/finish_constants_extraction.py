from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "app.py"
CONSTANTS = ROOT / "champions" / "constants.py"

app = APP.read_text(encoding="utf-8")
constants = CONSTANTS.read_text(encoding="utf-8")

# Find the complete TYPE_DEFENSES assignment by counting braces, so nested
# dictionaries/lists do not cause the extraction to stop early.
start_marker = "TYPE_DEFENSES = {"
start = app.find(start_marker)
if start == -1:
    raise SystemExit("TYPE_DEFENSES was not found in app.py; nothing changed.")

brace_start = app.find("{", start)
depth = 0
end = None
in_string = False
quote = None
escaped = False

for i in range(brace_start, len(app)):
    ch = app[i]

    if in_string:
        if escaped:
            escaped = False
        elif ch == "\\":
            escaped = True
        elif ch == quote:
            in_string = False
        continue

    if ch in ('\"', "'"):
        in_string = True
        quote = ch
        continue

    if ch == "{":
        depth += 1
    elif ch == "}":
        depth -= 1
        if depth == 0:
            end = i + 1
            break

if end is None:
    raise SystemExit("TYPE_DEFENSES dictionary appears to be unterminated; nothing changed.")

block = app[start:end].rstrip() + "\n\n"

if "TYPE_DEFENSES = {" not in constants:
    constants = constants.rstrip() + "\n\n" + block

# Import the extracted constant from the constants module.
if "    TYPE_DEFENSES,\n" not in app:
    app = app.replace(
        "    MOVE_DISPLAY_OVERRIDES,\n",
        "    MOVE_DISPLAY_OVERRIDES,\n    TYPE_DEFENSES,\n",
        1,
    )

# Re-find the local definition after the import edit, then remove it.
start = app.find(start_marker)
brace_start = app.find("{", start)
depth = 0
end = None
in_string = False
quote = None
escaped = False

for i in range(brace_start, len(app)):
    ch = app[i]
    if in_string:
        if escaped:
            escaped = False
        elif ch == "\\":
            escaped = True
        elif ch == quote:
            in_string = False
        continue
    if ch in ('\"', "'"):
        in_string = True
        quote = ch
        continue
    if ch == "{":
        depth += 1
    elif ch == "}":
        depth -= 1
        if depth == 0:
            end = i + 1
            break

if end is None:
    raise SystemExit("Could not locate the end of TYPE_DEFENSES after import edit.")

# Also remove the blank lines immediately following the dictionary, but keep
# the next function definition intact.
while end < len(app) and app[end] == "\n":
    end += 1

app = app[:start] + app[end:]

APP.write_text(app, encoding="utf-8")
CONSTANTS.write_text(constants, encoding="utf-8")

print("Done: TYPE_DEFENSES moved to champions/constants.py and imported by app.py.")
