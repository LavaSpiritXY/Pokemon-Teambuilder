from pathlib import Path
import re

APP = Path("app.py")
text = APP.read_text(encoding="utf-8")

# Match the live Phase 18.5 SP setup without depending on exact whitespace.
pattern = re.compile(
    r'(?P<indent>\s*)current_sp\s*=\s*\{k:\s*max\(0,\s*min\(32,\s*int\(slot\["evs"\]\.get\(k,\s*0\)\s*or\s*0\)\)\)\s*for\s*k\s*in\s*sp_keys\}\s*\n'
    r'(?P=indent)used_sp\s*=\s*sum\(current_sp\.values\(\)\)\s*\n'
    r'(?P=indent)for\s+idx,\s*\(key,\s*label\)\s+in\s+enumerate\(zip\(sp_keys,\s*sp_labels\)\):\s*\n'
)

match = pattern.search(text)
if not match:
    raise RuntimeError("Could not locate the current Phase 18.5 SP setup in app.py. No changes were made.")

indent = match.group("indent")
replacement = (
    f"{indent}# Sanitize legacy/custom allocations before rendering widgets.\n"
    f"{indent}# Champions allows at most 32 SP in one stat and 66 SP total.\n"
    f"{indent}current_sp = {{\n"
    f"{indent}    k: max(0, min(32, int(slot[\"evs\"].get(k, 0) or 0)))\n"
    f"{indent}    for k in sp_keys\n"
    f"{indent}}}\n"
    f"{indent}overflow = max(0, sum(current_sp.values()) - 66)\n"
    f"{indent}for key in reversed(sp_keys):\n"
    f"{indent}    if overflow <= 0:\n"
    f"{indent}        break\n"
    f"{indent}    reduction = min(current_sp[key], overflow)\n"
    f"{indent}    current_sp[key] -= reduction\n"
    f"{indent}    overflow -= reduction\n"
    f"{indent}for key in sp_keys:\n"
    f"{indent}    slot[\"evs\"][key] = current_sp[key]\n"
    f"{indent}used_sp = sum(current_sp.values())\n"
    f"{indent}for idx, (key, label) in enumerate(zip(sp_keys, sp_labels)):\n"
)

text = text[:match.start()] + replacement + text[match.end():]
APP.write_text(text, encoding="utf-8")
print("Phase 18.5 SP runtime fix applied: legacy allocations are sanitized to 32/stat and 66 total before widgets render.")
