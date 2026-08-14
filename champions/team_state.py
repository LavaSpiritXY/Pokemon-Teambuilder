from typing import Any, Dict

import streamlit as strlit

from champions.constants import CUSTOM_MEGAS_DATA, MEGA_STONE_MAP
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