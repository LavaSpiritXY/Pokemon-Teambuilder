from pathlib import Path
import re

APP = Path("app.py")
text = APP.read_text(encoding="utf-8")

# Do not depend on the heading or any previous patch's exact block. Find the
# widget by its stable Streamlit key instead.
key_token = 'key=f"stat_sp_{i}_{key}"'
pos = text.find(key_token)
if pos < 0:
    raise RuntimeError("Could not locate stat_sp number_input in app.py. No changes were made.")

# Work backwards to the start of this number_input call and forward to its end.
start = text.rfind('new_value = strlit.number_input(', 0, pos)
if start < 0:
    raise RuntimeError("Could not locate start of current SP number_input call. No changes were made.")
end = text.find(')', pos)
if end < 0:
    raise RuntimeError("Could not locate end of current SP number_input call. No changes were made.")
end += 1

call = text[start:end]

# The diagnostic specifically requires a literal 32-per-stat widget cap.
updated = re.sub(r'max_value\s*=\s*[^,\n]+', 'max_value=32', call, count=1)
if updated == call:
    raise RuntimeError("Could not identify max_value in current SP number_input call. No changes were made.")

text = text[:start] + updated + text[end:]
APP.write_text(text, encoding="utf-8")
print("Phase 18.5 SP test compatibility v5 applied: stat_sp widget now exposes explicit max_value=32.")
