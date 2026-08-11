from pathlib import Path
import re

APP = Path("app.py")
text = APP.read_text(encoding="utf-8")

# Locate the actual Champions SP section by its stable UI labels rather than
# relying on the exact whitespace/version of an earlier patch.
start_marker = '            strlit.markdown("##### 📊 Champions SP Allocation")'
end_marker = '            strlit.markdown("##### Type matchup")'

start = text.find(start_marker)
end = text.find(end_marker, start + len(start_marker)) if start >= 0 else -1
if start < 0 or end < 0:
    raise RuntimeError("Could not locate the Champions SP Allocation section in the current app.py. No changes were made.")

block = text[start:end]

# Replace only the allocation logic inside that section. This handles the
# current app even if formatting or harmless surrounding code changed.
pattern = re.compile(
    r'            current_sp\s*=\s*\{.*?\n            strlit\.caption\(f"Champions SP:.*?\n',
    re.DOTALL,
)

replacement = '''            # Sanitize any legacy allocation before Streamlit widgets render.\n            # Champions limits: 32 SP per stat, 66 SP total.\n            current_sp = {\n                k: max(0, min(32, int(slot["evs"].get(k, 0) or 0)))\n                for k in sp_keys\n            }\n\n            # Repair old allocations that exceed the 66-point total.\n            overflow = max(0, sum(current_sp.values()) - 66)\n            for key in reversed(sp_keys):\n                if overflow <= 0:\n                    break\n                reduction = min(current_sp[key], overflow)\n                current_sp[key] -= reduction\n                overflow -= reduction\n\n            for key in sp_keys:\n                slot["evs"][key] = current_sp[key]\n\n            used_sp = sum(current_sp.values())\n            for idx, (key, label) in enumerate(zip(sp_keys, sp_labels)):\n                with sp_cols[idx % 3]:\n                    other_sp = used_sp - current_sp[key]\n                    max_allowed = max(0, min(32, 66 - other_sp))\n                    current_value = max(0, min(current_sp[key], max_allowed))\n                    new_value = strlit.number_input(\n                        label,\n                        min_value=0,\n                        max_value=max_allowed,\n                        step=1,\n                        value=current_value,\n                        key=f"stat_sp_{i}_{key}",\n                    )\n                    current_sp[key] = int(new_value)\n                    slot["evs"][key] = int(new_value)\n                    used_sp = other_sp + int(new_value)\n\n            strlit.caption(\n                f"Champions SP: {sum(current_sp.values())}/66 total · maximum 32 per stat"\n            )\n'''

match = pattern.search(block)
if not match:
    raise RuntimeError("Could not locate the current SP allocation logic inside the section. No changes were made.")

new_block = block[:match.start()] + replacement + block[match.end():]
text = text[:start] + new_block + text[end:]
APP.write_text(text, encoding="utf-8")
print("Phase 18.5 SP runtime fix v2 applied successfully: allocations are sanitized before number_input widgets render.")
