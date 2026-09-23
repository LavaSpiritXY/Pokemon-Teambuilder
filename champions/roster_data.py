import re

import requests
import streamlit as strlit

from champions.registry import (
    get_species,
    get_species_by_canonical_key,
    get_species_by_display_name,
    load_registry,
)
def fetch_champions_learnsets():
    url = "https://raw.githubusercontent.com/smogon/pokemon-showdown/master/data/mods/champions/learnsets.ts"
    try:
        res = requests.get(url, timeout=20)
        if res.status_code != 200:
            return {}

        text = res.text
        lines = text.splitlines()
        parsed = {}
        current_species = None
        current_block_lines = []
        in_species_block = False
        brace_depth = 0

        for line in lines:
            stripped = line.strip()
            if not stripped or stripped.startswith("//"):
                continue

            if not in_species_block:
                match = re.match(r"^\t([a-z0-9]+(?:-[a-z0-9]+)*)\s*:\s*\{$", line)
                if match:
                    current_species = match.group(1)
                    current_block_lines = [line]
                    in_species_block = True
                    brace_depth = line.count("{") - line.count("}")
                continue

            current_block_lines.append(line)
            brace_depth += line.count("{") - line.count("}")

            if brace_depth <= 0:
                in_species_block = False
                moves = []
                in_learnset = False
                learnset_depth = 0
                for block_line in current_block_lines:
                    if not in_learnset:
                        if re.match(r"^\s*learnset\s*:\s*\{", block_line):
                            in_learnset = True
                            learnset_depth = block_line.count("{") - block_line.count("}")
                        continue

                    move_match = re.match(r"^\s*([a-z0-9]+(?:-[a-z0-9]+)*)\s*:\s*\[", block_line)
                    if move_match:
                        moves.append(move_match.group(1))

                    learnset_depth += block_line.count("{") - block_line.count("}")
                    if learnset_depth <= 0:
                        in_learnset = False

                if moves:
                    parsed[current_species] = sorted(set(moves))

                current_species = None
                current_block_lines = []
                brace_depth = 0

        return parsed
    except Exception:
        return {}

def fetch_champions_pokedex_entries():
    url = "https://raw.githubusercontent.com/smogon/pokemon-showdown/master/data/mods/champions/pokedex.ts"
    try:
        res = requests.get(url, timeout=20)
        if res.status_code != 200:
            return []

        entries = []
        for match in re.finditer(r"(?m)^\s*([a-z0-9]+(?:-[a-z0-9]+)*)\s*:\s*\{\s*$", res.text):
            species_id = match.group(1)
            if species_id not in {"export"}:
                entries.append(species_id)
        return sorted(set(entries))
    except Exception:
        return []

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

    name = re.sub(r"^Mega\\s+", "", str(mon_name or "")).strip()
    name = re.sub(r"\\s+(?:X|Y|Z)$", "", name, flags=re.IGNORECASE)
    return get_clean_api_name(name)

