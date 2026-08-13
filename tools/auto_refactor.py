from pathlib import Path
import re

APP = Path("app.py")


def extract_slot_role(text: str) -> str:
    """Remove the old inline role function and wire the dedicated module."""
    start = text.find("def infer_slot_role(slot):")
    end = text.find("def ensure_slot_structure(slot_idx", start)
    if start == -1 or end == -1:
        return text
    text = text[:start] + text[end:]
    import_line = "from champions.roles import infer_slot_role\n"
    if import_line not in text:
        anchor = "from champions.roster_data import (\n"
        text = text.replace(anchor, import_line + "\n" + anchor, 1)
    return text


def extract_team_moves(text: str) -> str:
    """Remove inline move helpers and wire champions.team_moves."""
    start = text.find("def normalize_moves(moves, available_moves):")
    end = text.find("def on_species_change(slot_idx):", start)
    if start == -1 or end == -1:
        return text
    text = text[:start] + text[end:]
    import_line = "from champions.team_moves import generate_synergistic_moveset, normalize_moves\n"
    if import_line not in text:
        anchor = "from champions.roles import infer_slot_role\n"
        text = text.replace(anchor, anchor + import_line, 1)
    old_call = "generate_synergistic_moveset(new_species, slot_idx)"
    new_call = ("generate_synergistic_moveset(\n        new_species,\n        slot_idx,\n        fetch_pokemon_details,\n        get_smogon_stats_for,\n        fetch_move_type\n    )")
    text = text.replace(old_call, new_call, 1)
    return text


def extract_species_key(text: str) -> str:
    """Move the canonical species-key normaliser into its own module."""
    start = text.find("def canonical_species_key(name):")
    end = text.find("MEGA_STONE_MAP =", start)
    if start == -1 or end == -1:
        return text
    text = text[:start] + text[end:]
    import_line = "from champions.species_keys import canonical_species_key\n"
    if import_line not in text:
        anchor = "from champions.roster_data import (\n"
        text = text.replace(anchor, import_line + "\n" + anchor, 1)
    return text


def extract_type_relationships(text: str) -> str:
    """Move the cached PokeAPI type-relation helper into champions.type_chart."""
    start = text.find("@strlit.cache_data(ttl=86400, show_spinner=False)\ndef get_type_relationships(type_name):")
    if start == -1:
        return text
    end = text.find("# -----------------------------------------------------------------------------\n# 3.5 SMOGON", start)
    if end == -1:
        return text
    text = text[:start] + text[end:]
    import_line = "from champions.type_chart import get_type_relationships\n"
    if import_line not in text:
        anchor = "from champions.type_chart import (\n"
        if anchor in text:
            text = text.replace(anchor, anchor + "    get_type_relationships,\n", 1)
        else:
            text = text.replace("from champions.team_io import", import_line + "\nfrom champions.team_io import", 1)
    return text


def main():
    text = APP.read_text(encoding="utf-8")
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
    updated = extract_team_moves(updated)
    updated = extract_species_key(updated)
    updated = extract_type_relationships(updated)
    for name in ["Dict", "List", "Set", "Tuple"]:
        if updated.count(name) == 1:
            updated = updated.replace(f"from typing import {name}\n", "")
    APP.write_text(updated, encoding="utf-8")
    print("General app refactor completed.")


if __name__ == "__main__":
    main()
