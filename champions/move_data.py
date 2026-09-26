import re
from typing import Dict

import requests
import streamlit as strlit

from champions.constants import MOVE_DISPLAY_OVERRIDES, MOVE_TYPE_OVERRIDES

@strlit.cache_data(ttl=86400, show_spinner=False)
def fetch_master_move_dictionary():
    urls = [
        "https://raw.githubusercontent.com/smogon/pokemon-showdown/master/data/moves.ts",
        "https://raw.githubusercontent.com/smogon/pokemon-showdown/master/data/mods/champions/moves.ts"
    ]
    move_dict = {}
    for url in urls:
        try:
            res = requests.get(url, timeout=15)
            if res.status_code == 200:
                matches = re.findall(r'([a-z0-9]+)\s*:\s*\{[^}]*?name\s*:\s*["\']([^"\']+)["\']', res.text, re.DOTALL)
                for move_id, display_name in matches:
                    move_dict[move_id.lower().replace("-", "").replace(" ", "")] = display_name
        except Exception:
            continue
    return move_dict

MASTER_MOVE_DICTIONARY = fetch_master_move_dictionary()

def get_move_api_slug(move_name):
    if not move_name:
        return ""
    slug = str(move_name).strip().lower().split(" (")[0].replace("’", "").replace("'", "").replace(".", "")
    return re.sub(r'[^a-z0-9]+', '-', slug).strip("-")

def get_hardcoded_move_type(move_name):
    move_lower = str(move_name).strip().lower()
    return MOVE_TYPE_OVERRIDES.get(move_lower, "")

@strlit.cache_data(ttl=86400, show_spinner=False)
def fetch_move_type(move_name):
    hardcoded = get_hardcoded_move_type(move_name)
    if hardcoded:
        return hardcoded
    slug = get_move_api_slug(move_name)
    if not slug:
        return "Normal"
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        res = requests.get(f"https://pokeapi.co/api/v2/move/{slug}", headers=headers, timeout=3)
        if res.status_code == 200:
            t_name = res.json().get("type", {}).get("name")
            if t_name:
                return t_name.title()
    except Exception:
        pass
    return "Normal"

def get_champions_species_key(mon_name):
    """Compatibility wrapper around the generated species-key resolver."""
    from champions.species_keys import canonical_species_key
    return canonical_species_key(mon_name)

def display_name_for_move(move_id):
    if not move_id:
        return ""

    raw = str(move_id).strip()

    clean_id = (
        raw
        .lower()
        .replace("_", "")
        .replace("-", "")
        .replace(" ", "")
    )

    # 1. Explicit canonical edge cases
    if clean_id in MOVE_DISPLAY_OVERRIDES:
        return MOVE_DISPLAY_OVERRIDES[clean_id]

    # 2. Canonical Pokémon Showdown dictionary
    if clean_id in MASTER_MOVE_DICTIONARY:
        return MASTER_MOVE_DICTIONARY[clean_id]

    # 3. Readable fallback
    spaced = re.sub(
        r'([a-z])([A-Z])',
        r'\1 \2',
        raw
    )

    return " ".join(
        part.title()
        for part in spaced.replace("-", " ").split()
    )
