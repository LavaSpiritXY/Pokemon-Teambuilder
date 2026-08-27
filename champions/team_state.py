from typing import Any, Dict

import streamlit as strlit

from champions.constants import CUSTOM_MEGAS_DATA
from champions.item_data import MEGA_STONE_MAP

from champions.pokemon_data import fetch_pokemon_details
from champions.smogon_data import get_smogon_stats_for
from champions.team_moves import generate_synergistic_moveset, normalize_moves
from champions.move_data import fetch_move_type


def ensure_slot_structure(slot_idx, fallback_name="-- Choose a Pokémon --"):
    if "team_slots" not in strlit.session_state:
        strlit.session_state.team_slots = {}

    if slot_idx not in strlit.session_state.team_slots:
        strlit.session_state.team_slots[slot_idx] = {
            "name": fallback_name,
            "ability": "Standard",
            "item": "",
            "nature": "Hardy",
            "moves": ["Protect", "Substitute", "Toxic", "Rest"],
            "evs": {
                "HP": 0,
                "Atk": 0,
                "Def": 0,
                "SpA": 0,
                "SpD": 0,
                "Spe": 0,
            },
        }

    return strlit.session_state.team_slots[slot_idx]


def on_species_change(slot_idx):
    new_species = strlit.session_state.get(
        f"species_select_{slot_idx}",
        "-- Choose a Pokémon --",
    )

    slot = ensure_slot_structure(slot_idx, new_species)

    if new_species == "-- Choose a Pokémon --":
        return

    ability = CUSTOM_MEGAS_DATA.get(
        new_species,
        {},
    ).get(
        "ability",
        "Standard",
    )

    item = MEGA_STONE_MAP.get(
        new_species,
        "Focus Sash",
    )

    mon_data = fetch_pokemon_details(new_species)

    atk = mon_data["stats"].get("attack", 80)
    spa = mon_data["stats"].get("special-attack", 80)

    nature = (
        "Jolly (+Spe, -SpA)"
        if atk >= spa
        else "Timid (+Spe, -Atk)"
    )

    evs = (
        {
            "HP": 0,
            "Atk": 252,
            "Def": 4,
            "SpA": 0,
            "SpD": 0,
            "Spe": 252,
        }
        if atk >= spa
        else {
            "HP": 0,
            "Atk": 0,
            "Def": 4,
            "SpA": 252,
            "SpD": 0,
            "Spe": 252,
        }
    )

    recommended_moves = generate_synergistic_moveset(
        new_species,
        slot_idx,
        fetch_pokemon_details,
        get_smogon_stats_for,
        fetch_move_type,
    )

    slot.update({
        "name": new_species,
        "ability": ability,
        "item": item,
        "nature": nature,
        "moves": normalize_moves(
            recommended_moves,
            mon_data["moves"],
        ),
        "evs": evs,
    })


def _base_species_for_mega(mega_species: str) -> str:
    """Return the base species for a supported Mega form.

    Mega variants such as Charizard X/Y and Raichu X/Y share the same base
    species even though their full Mega display names include the variant.
    """
    value = str(mega_species or "").strip()
    if value.lower().startswith("mega "):
        value = value[5:].strip()
    if value.endswith((" X", " Y")):
        value = value[:-2].rstrip()
    return value


def on_item_change(slot_idx):
    """Use the selected Mega Stone to control the slot's Mega form.

    Base species and its X/Y Mega variants share one family. Selecting the
    matching stone promotes the base slot; selecting another matching stone
    switches Mega forms; selecting a non-Mega item demotes back to the base.
    """
    selected_item = strlit.session_state.get(f"item_{slot_idx}", "")
    if not selected_item:
        return

    def mega_base(name):
        value = str(name or "").strip()
        if value.lower().startswith("mega "):
            value = value[5:].strip()
        if value.endswith(" X") or value.endswith(" Y"):
            value = value[:-2].strip()
        return value

    current_slot = ensure_slot_structure(slot_idx)
    current_species = str(current_slot.get("name") or "")
    current_base = mega_base(current_species)

    target_mega = next(
        (species for species, stone in MEGA_STONE_MAP.items() if stone == selected_item),
        None,
    )

    # Matching Mega Stone: promote from the base or switch between Mega forms.
    if target_mega and current_base.casefold() == mega_base(target_mega).casefold():
        current_slot["name"] = target_mega
        current_slot["ability"] = CUSTOM_MEGAS_DATA.get(target_mega, {}).get("ability", "Standard")
        current_slot["item"] = selected_item
        strlit.session_state[f"species_select_{slot_idx}"] = current_base
        return

    # Picking any ordinary item while a Mega form is active returns the slot
    # to its base species. This keeps the base+stone model reversible.
    if current_species.lower().startswith("mega ") and not target_mega:
        current_slot["name"] = current_base
        current_slot["item"] = selected_item
        strlit.session_state[f"species_select_{slot_idx}"] = current_base

