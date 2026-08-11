from pathlib import Path

APP = Path("app.py")
OLD = '''            current_sp = {k: max(0, min(32, int(slot["evs"].get(k, 0) or 0))) for k in sp_keys}\n            used_sp = sum(current_sp.values())\n            for idx, (key, label) in enumerate(zip(sp_keys, sp_labels)):\n'''
NEW = '''            # Sanitize legacy/custom allocations before rendering widgets.\n            # Champions allows at most 32 SP in one stat and 66 SP total.\n            # Older saved slot data can exceed 66, which would make the\n            # per-widget remaining allowance negative and crash Streamlit.\n            current_sp = {\n                k: max(0, min(32, int(slot["evs"].get(k, 0) or 0)))\n                for k in sp_keys\n            }\n            overflow = max(0, sum(current_sp.values()) - 66)\n            for key in reversed(sp_keys):\n                if overflow <= 0:\n                    break\n                reduction = min(current_sp[key], overflow)\n                current_sp[key] -= reduction\n                overflow -= reduction\n            for key in sp_keys:\n                slot["evs"][key] = current_sp[key]\n            used_sp = sum(current_sp.values())\n            for idx, (key, label) in enumerate(zip(sp_keys, sp_labels)):\n'''

text = APP.read_text(encoding="utf-8")
if text.count(OLD) != 1:
    raise RuntimeError(f"Expected Phase 18.5 SP runtime block once, found {text.count(OLD)}")
text = text.replace(OLD, NEW)
APP.write_text(text, encoding="utf-8")
print("Phase 18.5 SP runtime fix applied: legacy allocations are clamped to 32/stat and 66 total before widgets render.")
