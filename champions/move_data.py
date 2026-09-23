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
    """Return the generated registry's canonical Champions key."""
    if not mon_name:
        return ""

    name = str(mon_name).strip()
    if not name:
        return ""

    from champions.registry import get_species_key_by_display_name, get_species

    direct = get_species(name.casefold())
    if direct.get("canonical_key"):
        return str(direct["canonical_key"])

    generated = get_species_key_by_display_name(name)
    if generated:
        return generated

    clean = (
        name.lower()
        .replace("’", "")
        .replace("'", "")
        .replace(".", "")
        .replace("♀", "f")
        .replace("♂", "m")
        .replace("_", "-")
    )
    clean = " ".join(clean.split())

    if clean.startswith("mega "):
        clean = clean[5:].strip()
        parts = clean.split()
        if parts and parts[-1] in {"x", "y", "z"}:
            return f"{'-'.join(parts[:-1])}-{parts[-1]}"
        return "-".join(parts)

    return "-".join(clean.split())

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
