from pathlib import Path

APP = Path("app.py")
text = APP.read_text(encoding="utf-8")

old = '''            current_sp = {k: max(0, min(32, int(slot["evs"].get(k, 0) or 0))) for k in sp_keys}\n            used_sp = sum(current_sp.values())\n            for idx, (key, label) in enumerate(zip(sp_keys, sp_labels)):\n'''
new = '''            # Sanitize legacy allocations before rendering Streamlit widgets.\n            # Champions allows at most 32 SP in one stat and 66 SP total.\n            current_sp = {\n                k: max(0, min(32, int(slot["evs"].get(k, 0) or 0)))\n                for k in sp_keys\n            }\n            overflow = max(0, sum(current_sp.values()) - 66)\n            for key in reversed(sp_keys):\n                if overflow <= 0:\n                    break\n                reduction = min(current_sp[key], overflow)\n                current_sp[key] -= reduction\n                overflow -= reduction\n            for key in sp_keys:\n                slot["evs"][key] = current_sp[key]\n            used_sp = sum(current_sp.values())\n            for idx, (key, label) in enumerate(zip(sp_keys, sp_labels)):\n'''

if old not in text:
    raise RuntimeError("Current app.py uses a different Phase 18.5 SP block than the patch anchor.")

text = text.replace(old, new, 1)
APP.write_text(text, encoding="utf-8")
print("Phase 18.5 SP runtime fix applied: legacy allocations are sanitized to 32/stat and 66 total before widgets render.")
