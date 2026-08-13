from pathlib import Path

APP = Path("app.py")


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

    # Remove now-unused typing names only when they are genuinely absent
    # from the application body.
    for name in ["Dict", "List", "Set", "Tuple"]:
        if updated.count(name) == 1:
            updated = updated.replace(f"from typing import {name}\n", "")

    APP.write_text(updated, encoding="utf-8")
    print("General app refactor completed.")


if __name__ == "__main__":
    main()
