from __future__ import annotations

import re
from pathlib import Path

APP = Path("app.py")
ROSTER = Path("champions/roster_data.py")
STATE = Path("champions/team_state.py")


def patch_roster() -> bool:
    text = ROSTER.read_text(encoding="utf-8")
    old = '''    return ["-- Choose a Pokémon --"] + sorted(\n        set(roster),\n        key=lambda item: (\n            not item.startswith("Mega "),\n            item.lower(),\n        ),\n    )'''
    new = '''    # Mega forms are not independently selectable in the species dropdown.\n    # The base species is the stable selector; the matching Mega Stone drives\n    # the Mega form stored in the slot state.\n    base_only_roster = {\n        item for item in roster\n        if not str(item).startswith("Mega ")\n    }\n\n    return ["-- Choose a Pokémon --"] + sorted(\n        base_only_roster,\n        key=str.lower,\n    )'''
    if new in text:
        return False
    if old not in text:
        raise RuntimeError("fetch_pokemon_roster return block not found")
    ROSTER.write_text(text.replace(old, new, 1), encoding="utf-8")
    return True


def patch_state() -> bool:
    text = STATE.read_text(encoding="utf-8")
    pattern = re.compile(r"(?ms)^def on_item_change\(slot_idx\):\n.*?^    strlit\.session_state\[f\"species_select_\{slot_idx\}\"\] = mega_species\n?")
    replacement = '''def on_item_change(slot_idx):\n    """Use the selected Mega Stone to control the slot's Mega form.\n\n    Base species and its X/Y Mega variants share one family. Selecting the\n    matching stone promotes the base slot; selecting another matching stone\n    switches Mega forms; selecting a non-Mega item demotes back to the base.\n    """\n    selected_item = strlit.session_state.get(f"item_{slot_idx}", "")\n    if not selected_item:\n        return\n\n    def mega_base(name):\n        value = str(name or "").strip()\n        if value.lower().startswith("mega "):\n            value = value[5:].strip()\n        if value.endswith(" X") or value.endswith(" Y"):\n            value = value[:-2].strip()\n        return value\n\n    current_slot = ensure_slot_structure(slot_idx)\n    current_species = str(current_slot.get("name") or "")\n    current_base = mega_base(current_species)\n\n    target_mega = next(\n        (species for species, stone in MEGA_STONE_MAP.items() if stone == selected_item),\n        None,\n    )\n\n    # Matching Mega Stone: promote from the base or switch between Mega forms.\n    if target_mega and current_base.casefold() == mega_base(target_mega).casefold():\n        current_slot["name"] = target_mega\n        current_slot["ability"] = CUSTOM_MEGAS_DATA.get(target_mega, {}).get("ability", "Standard")\n        current_slot["item"] = selected_item\n        strlit.session_state[f"species_select_{slot_idx}"] = current_base\n        return\n\n    # Picking any ordinary item while a Mega form is active returns the slot\n    # to its base species. This keeps the base+stone model reversible.\n    if current_species.lower().startswith("mega ") and not target_mega:\n        current_slot["name"] = current_base\n        current_slot["item"] = selected_item\n        strlit.session_state[f"species_select_{slot_idx}"] = current_base\n\n'''
    match = pattern.search(text)
    if not match:
        raise RuntimeError("existing on_item_change function not found")
    STATE.write_text(text[:match.start()] + replacement + text[match.end():], encoding="utf-8")
    return True


def patch_app() -> bool:
    text = APP.read_text(encoding="utf-8")
    changed = False

    old_import = "from champions.team_state import ensure_slot_structure, on_species_change"
    new_import = "from champions.team_state import ensure_slot_structure, on_species_change, on_item_change"
    if "on_item_change" not in text:
        if old_import not in text:
            raise RuntimeError("team_state import line not found")
        text = text.replace(old_import, new_import, 1)
        changed = True

    old_default = '''        try:\n            default_index = CHAMPIONS_ALL_FORMS.index(slot_name)\n        except ValueError:\n            default_index = 0\n'''
    new_default = '''        selector_name = slot_name\n        if selector_name.startswith("Mega "):\n            selector_name = selector_name[5:].strip()\n            if selector_name.endswith(" X") or selector_name.endswith(" Y"):\n                selector_name = selector_name[:-2].strip()\n        try:\n            default_index = CHAMPIONS_ALL_FORMS.index(selector_name)\n        except ValueError:\n            default_index = 0\n'''
    if old_default in text:
        text = text.replace(old_default, new_default, 1)
        changed = True
    elif "selector_name = slot_name" not in text:
        raise RuntimeError("species select default block not found")

    pattern = re.compile(
        r"(?ms)^            if slot_name in MEGA_STONE_MAP:\n.*?^                slot\[\"item\"\] = selected_item\n"
    )
    replacement = '''            mega_items, species_items, standard_items = get_contextual_item_groups(slot_name)\n            item_options = list(mega_items) + list(species_items) + list(standard_items)\n            mega_set = set(mega_items)\n            species_set = set(species_items)\n\n            current_item = slot.get("item", "")\n            if current_item not in item_options:\n                current_item = item_options[0] if item_options else ""\n\n            def _format_item_option(item):\n                if item in mega_set:\n                    return f"⭐ Mega Stone  •  {item}"\n                if item in species_set:\n                    return f"◆ Pokémon-specific  •  {item}"\n                return item\n\n            selected_item = strlit.selectbox(\n                "Held Item",\n                options=item_options,\n                index=item_options.index(current_item) if current_item in item_options else 0,\n                key=f"item_{i}",\n                format_func=_format_item_option,\n                on_change=on_item_change,\n                args=(i,),\n            )\n            slot["item"] = selected_item\n'''
    match = pattern.search(text)
    if match:
        text = text[:match.start()] + replacement + text[match.end():]
        changed = True
    elif 'item_options = list(mega_items) + list(species_items) + list(standard_items)' not in text:
        raise RuntimeError("current item selector block not found")

    if changed:
        APP.write_text(text, encoding="utf-8")
    return changed


def main():
    changed = {"roster": patch_roster(), "state": patch_state(), "app": patch_app()}
    app = APP.read_text(encoding="utf-8")
    roster = ROSTER.read_text(encoding="utf-8")
    state = STATE.read_text(encoding="utf-8")
    assert "base_only_roster" in roster
    assert "on_change=on_item_change" in app
    assert 'item_options = list(mega_items) + list(species_items) + list(standard_items)' in app
    assert "def on_item_change(slot_idx):" in state
    print("Migration changes:", changed)


if __name__ == "__main__":
    main()
