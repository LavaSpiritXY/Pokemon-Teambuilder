import re

import requests
import streamlit as strlit

from champions.registry import (
    get_species,
    get_species_by_canonical_key,
    get_species_by_display_name,
    load_registry,
)
def display_name_for_species_key(species_key):
    """Convert a generated Champions species key to its current UI name."""
    if not species_key:
        return species_key

    key = str(species_key).strip().casefold()
    entry = get_species(key) or get_species_by_canonical_key(key)
    if entry:
        return str(entry.get("display_name") or entry.get("source_name") or species_key)

    # Registry fallback for an unseen key that follows Showdown's normal ID
    # convention. Unknown data remains readable without a new alias table.
    return " ".join(
        part.title()
        for part in re.sub(r"[-_]+", " ", key).split()
    )

def fetch_pokemon_roster():
    """Return the generated Champions base-species roster.

    Mega forms are intentionally excluded from the species selector. The
    matching Mega Stone controls promotion to a Mega form in team state.
    """
    registry = load_registry()
    return ["-- Choose a Pokémon --"] + list(registry["base_roster"])

def get_clean_api_name(mon_name):
    """Return the generated registry's PokeAPI slug for a Pokémon/form."""
    if not mon_name or mon_name == "-- Choose a Pokémon --":
        return "charizard"

    entry = get_species_by_display_name(str(mon_name).strip())
    if entry and entry.get("api_slug"):
        return str(entry["api_slug"])

    # Unknown future names still get a deterministic fallback slug.
    clean = (
        str(mon_name)
        .strip()
        .lower()
        .replace("’", "")
        .replace("'", "")
        .replace(".", "")
    )
    if clean.startswith("mega "):
        clean = clean[5:].strip()
    return re.sub(r"[^a-z0-9]+", "-", clean).strip("-")

def get_base_api_name(mon_name):
    """Return the PokeAPI slug for the base species of a form/Mega."""
    entry = get_species_by_display_name(str(mon_name or "").strip())
    if entry:
        base_key = entry.get("base_species_key")
        base_entry = get_species(base_key or "")
        if base_entry.get("api_slug"):
            return str(base_entry["api_slug"])

    name = re.sub(r"^Mega\s+", "", str(mon_name or "")).strip()
    name = re.sub(r"\s+(?:X|Y|Z)$", "", name, flags=re.IGNORECASE)
    return get_clean_api_name(name)

