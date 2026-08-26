from pathlib import Path
import re

APP = Path("app.py")
STATE = Path("champions/team_state.py")


def patch_app() -> bool:
    text = APP.read_text(encoding="utf-8")
    changed = False

    old_import = "from champions.team_state import ensure_slot_structure, on_species_change"
    new_import = "from champions.team_state import ensure_slot_structure, on_species_change, on_item_change"
    if "on_item_change" not in text:
        if old_import not in text:
            raise RuntimeError("Cannot find team_state import in app.py")
        text = text.replace(old_import, new_import, 1)
        changed = True

    pattern = re.compile(
        r"(?ms)^                mega_items, species_items, standard_items = get_contextual_item_groups\(slot_name\)\n.*?^                slot\[\"item\"\] = selected_item\n"
    )

    replacement = '''                mega_items, species_items, standard_items = get_contextual_item_groups(slot_name)
                mega_items = list(mega_items)
                species_items = list(species_items)
                standard_items = list(standard_items)

                # Category labels are display text only. They are never values
                # in the selectbox, so "General Held Items" cannot become an item.
                item_options = mega_items + species_items + standard_items
                mega_set = set(mega_items)
                species_set = set(species_items)

                current_item = slot.get("item", "")
                if current_item not in item_options:
                    current_item = item_options[0] if item_options else ""

                def _format_item_option(item):
                    if item in mega_set:
                        return f"⭐ Mega Stone  •  {item}"
                    if item in species_set:
                        return f"◆ Pokémon-specific  •  {item}"
                    return item

                selected_item = strlit.selectbox(
                    "Held Item",
                    options=item_options,
                    index=item_options.index(current_item) if current_item in item_options else 0,
                    key=f"item_{i}",
                    format_func=_format_item_option,
                    on_change=on_item_change,
                    args=(i,),
                )
                slot["item"] = selected_item
'''

    match = pattern.search(text)
    if match:
        text = text[:match.start()] + replacement + text[match.end():]
        changed = True
    elif "item_options = mega_items + species_items + standard_items" not in text:
        raise RuntimeError("Cannot find the old contextual item selector block in app.py")

    if changed:
        APP.write_text(text, encoding="utf-8")
    return changed


def patch_state() -> bool:
    text = STATE.read_text(encoding="utf-8")
    if "def on_item_change(" in text:
        return False

    callback = '''\n\n\ndef on_item_change(slot_idx):
    """Promote a base Pokémon when its matching Mega Stone is selected."""
    selected_item = strlit.session_state.get(f"item_{slot_idx}", "")
    if not selected_item:
        return

    mega_species = next(
        (species for species, stone in MEGA_STONE_MAP.items() if stone == selected_item),
        None,
    )
    if not mega_species:
        return

    slot = ensure_slot_structure(slot_idx)
    current_species = str(slot.get("name") or "")
    base_species = mega_species.removeprefix("Mega ")

    # Only the matching base species can promote to this Mega form.
    if current_species.casefold() != base_species.casefold():
        return

    slot["name"] = mega_species
    slot["ability"] = CUSTOM_MEGAS_DATA.get(mega_species, {}).get("ability", "Standard")
    slot["item"] = selected_item
    strlit.session_state[f"species_select_{slot_idx}"] = mega_species
'''
    STATE.write_text(text.rstrip() + callback + "\n", encoding="utf-8")
    return True


def main() -> None:
    app_changed = patch_app()
    state_changed = patch_state()

    # Hard guarantees for the migration result.
    app = APP.read_text(encoding="utf-8")
    state = STATE.read_text(encoding="utf-8")
    assert "on_change=on_item_change" in app
    assert "item_options = mega_items + species_items + standard_items" in app
    assert "── General Held Items ──" not in app
    assert "def on_item_change(" in state

    print(f"app.py changed: {app_changed}")
    print(f"team_state.py changed: {state_changed}")
    print("Item selector / Mega promotion migration validated.")


if __name__ == "__main__":
    main()
