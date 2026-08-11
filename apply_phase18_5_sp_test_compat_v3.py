from pathlib import Path

APP = Path("app.py")
text = APP.read_text(encoding="utf-8")

old = '''                    other_sp = used_sp - current_sp[key]\n                    max_allowed = min(32, 66 - other_sp)\n                    current_value = current_sp[key]\n                    new_value = strlit.number_input(\n                        label, min_value=0, max_value=max_allowed, step=1,\n                        value=min(current_value, max_allowed), key=f"stat_sp_{i}_{key}"\n                    )\n                    current_sp[key] = int(new_value)\n                    slot["evs"][key] = int(new_value)\n                    used_sp = other_sp + int(new_value)\n'''

new = '''                    other_sp = used_sp - current_sp[key]\n                    remaining = max(0, 66 - other_sp)\n                    current_value = max(0, min(32, current_sp[key]))\n                    new_value = strlit.number_input(\n                        label, min_value=0, max_value=32, step=1,\n                        value=current_value, key=f"stat_sp_{i}_{key}"\n                    )\n                    # The widget exposes the real per-stat cap (32); enforce\n                    # the separate 66-point team total immediately afterwards.\n                    new_value = min(int(new_value), remaining)\n                    current_sp[key] = new_value\n                    slot["evs"][key] = new_value\n                    used_sp = other_sp + new_value\n'''

count = text.count(old)
if count != 1:
    raise RuntimeError(f"Expected current Phase 18.5 SP widget block once, found {count}. No changes were made.")

APP.write_text(text.replace(old, new), encoding="utf-8")
print("Phase 18.5 SP widget v3 applied: 32-per-stat widget cap with 66-total enforcement.")
