from pathlib import Path
import re

APP = Path("app.py")
text = APP.read_text(encoding="utf-8")

OLD = '''            current_sp = {k: max(0, min(32, int(slot["evs"].get(k, 0) or 0))) for k in sp_keys}\n            used_sp = sum(current_sp.values())\n            for idx, (key, label) in enumerate(zip(sp_keys, sp_labels)):\n                with sp_cols[idx % 3]:\n                    other_sp = used_sp - current_sp[key]\n                    max_allowed = min(32, 66 - other_sp)\n                    current_value = current_sp[key]\n                    new_value = strlit.number_input(\n                        label, min_value=0, max_value=max_allowed, step=1,\n                        value=min(current_value, max_allowed), key=f"stat_sp_{i}_{key}"\n                    )\n'''

NEW = '''            # Sanitize legacy/custom allocations before rendering the widgets.\n            # Champions allows at most 32 SP in one stat and 66 SP total.\n            current_sp = {\n                k: max(0, min(32, int(slot["evs"].get(k, 0) or 0)))\n                for k in sp_keys\n            }\n\n            # If an older saved allocation exceeds 66 total, trim the excess\n            # before Streamlit sees any number_input value. This prevents\n            # negative max_allowed/value states such as value=-2, min=0.\n            overflow = max(0, sum(current_sp.values()) - 66)\n            for key in reversed(sp_keys):\n                if overflow <= 0:\n                    break\n                reduction = min(current_sp[key], overflow)\n                current_sp[key] -= reduction\n                overflow -= reduction\n\n            for key in sp_keys:\n                slot["evs"][key] = current_sp[key]\n\n            used_sp = sum(current_sp.values())\n            for idx, (key, label) in enumerate(zip(sp_keys, sp_labels)):\n                with sp_cols[idx % 3]:\n                    other_sp = used_sp - current_sp[key]\n                    max_allowed = max(0, min(32, 66 - other_sp))\n                    current_value = max(0, min(current_sp[key], max_allowed))\n                    new_value = strlit.number_input(\n                        label, min_value=0, max_value=max_allowed, step=1,\n                        value=current_value, key=f"stat_sp_{i}_{key}"\n                    )\n'''

count = text.count(OLD)
if count != 1:
    raise RuntimeError(f"Expected current Phase 18.5 SP widget block once, found {count}. No changes were made.")

text = text.replace(OLD, NEW, 1)
APP.write_text(text, encoding="utf-8")
print("Phase 18.5 SP runtime fix applied: legacy allocations are sanitized to 32/stat and 66 total before widgets render.")
