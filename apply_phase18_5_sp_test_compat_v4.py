from pathlib import Path
import re

APP = Path("app.py")
text = APP.read_text(encoding="utf-8")

# Locate the actual Champions SP widget loop rather than depending on the
# exact intermediate patch text. This survives the runtime-sanitisation fix.
section_start = text.find('strlit.markdown("##### Champions SP Allocation")')
if section_start < 0:
    raise RuntimeError("Could not locate Champions SP Allocation section in app.py. No changes were made.")

section_end = text.find('strlit.markdown("##### Type matchup")', section_start)
if section_end < 0:
    raise RuntimeError("Could not locate end of Champions SP Allocation section. No changes were made.")

section = text[section_start:section_end]

# Replace only the number_input call's dynamic cap with an explicit 32 cap.
# Keep the existing surrounding total-budget logic intact.
pattern = re.compile(
    r'(new_value\s*=\s*strlit\.number_input\(\s*'
    r'label,\s*min_value=0,\s*max_value=)max_allowed(,\s*step=1,\s*'
    r'value=min\(current_value,\s*max_allowed\),\s*key=f"stat_sp_\{i\}_\{key\}"\s*\))'
)

updated, count = pattern.subn(r'\g<1>32\2', section, count=1)

if count != 1:
    # Alternate form used by the runtime-fix-v2 block.
    pattern2 = re.compile(
        r'(new_value\s*=\s*strlit\.number_input\(\s*'
        r'label,\s*min_value=0,\s*max_value=)max_allowed(,\s*step=1,\s*'
        r'value=current_value,\s*key=f"stat_sp_\{i\}_\{key\}"\s*\))'
    )
    updated, count = pattern2.subn(r'\g<1>32\2', section, count=1)

if count != 1:
    raise RuntimeError("Could not locate the current Phase 18.5 SP number_input call. No changes were made.")

text = text[:section_start] + updated + text[section_end:]
APP.write_text(text, encoding="utf-8")
print("Phase 18.5 SP diagnostic compatibility v4 applied: explicit 32 per-stat widget cap retained with existing 66-total logic.")
