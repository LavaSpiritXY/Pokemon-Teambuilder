from pathlib import Path
import re

APP = Path("app.py")


def extract_slot_role(text: str) -> str:
    """Remove the old inline role function and wire the dedicated module."""
    start = text.find("def infer_slot_role(slot):")
    end = text.find("def ensure_slot_structure(slot_idx", start)

    if start == -1 or end == -1:
        print("Slot role function was not found; nothing changed.")
        return text

    text = text[:start] + text[end:]

    import_line = "from champions.roles import infer_slot_role\n"
    if import_line not in text:
        anchor = "from champions.roster_data import (\n"
        text = text.replace(anchor, import_line + "\n" + anchor, 1)

    old_call = '''"role":\n            infer_slot_role({\n                "name": mon_name,\n                "moves": moves\n            }),'''
    new_call = '''"role":\n            infer_slot_role(\n                {\n                    "name": mon_name,\n                    "moves": moves\n                },\n                fetch_pokemon_details\n            ),'''
    if old_call in text:
        text = text.replace(old_call, new_call, 1)
    else:
        # Also support the compact form if formatting changes slightly.
        text = re.sub(
            r'"role":\s*infer_slot_role\(\{\s*"name": mon_name,\s*"moves": moves\s*\}\),',
            new_call,
            text,
            count=1,
        )

    return text


def main():
    text = APP.read_text(encoding="utf-8")

    # These symbols were moved into dedicated modules and are no longer
    # referenced directly by app.py. Keep the import surface minimal.
    replacements = {
        "    CURRENT_REGULATION,\n": "",
        "    SPECIES_DISPLAY_OVERRIDES,\n": "",
        "    MOVE_TYPE_OVERRIDES,\n": "",
        "    ARCHETYPE_DEFINITIONS,\n": "",
        "    MOVE_DISPLAY_OVERRIDES,\n": "",
        "from champions.meta_utils import (\n    get_hardcoded_move_type,\n    fetch_move_type,\n    detect_archetypes,\n)": "from champions.meta_utils import detect_archetypes",
        "from dataclasses import dataclass, field\n": "",
    }

    updated = text
    for old, new in replacements.items():
        updated = updated.replace(old, new)

    updated = extract_slot_role(updated)

    # Remove now-unused typing names only when they are genuinely absent
    # from the application body.
    for name in ["Dict", "List", "Set", "Tuple"]:
        if updated.count(name) == 1:
            updated = updated.replace(f"from typing import {name}\n", "")

    APP.write_text(updated, encoding="utf-8")
    print("General app refactor completed.")


if __name__ == "__main__":
    main()
