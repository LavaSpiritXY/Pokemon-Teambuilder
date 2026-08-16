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
    """
    Convert a displayed Pokémon name into the exact
    Champions/Showdown species key.

    IMPORTANT:
    Forms are deliberately preserved.
    """

    if not mon_name:
        return ""

    name = str(mon_name).strip()

    SPECIES_KEYS = {

        # =====================================================
        # TAUROS
        # =====================================================

        "Tauros Paldea Combat Breed": "tauros-paldea-combat-breed",
        "Tauros Paldea Blaze Breed": "tauros-paldea-blaze-breed",
        "Tauros Paldea Aqua Breed": "tauros-paldea-aqua-breed",

        # =====================================================
        # BASCULEGION
        # =====================================================

        "Basculegion": "basculegion-male",
        "Basculegion Female": "basculegion-female",

        # =====================================================
        # FLOETTE
        # =====================================================

        "Floette Eternal": "floetteeternal",

        # =====================================================
        # INDEEDEE
        # =====================================================

        "Indeedee Male": "indeedeem",
        "Indeedee Female": "indeedeef",

        # =====================================================
        # MEOWSTIC
        # =====================================================

        "Meowstic Male": "meowsticm",
        "Meowstic Female": "meowsticf",

        # =====================================================
        # OINKOLOGNE
        # =====================================================

        "Oinkologne Male": "oinkolognem",
        "Oinkologne Female": "oinkolognef",

        # =====================================================
        # LYCANROC
        # =====================================================

        "Lycanroc Midday": "lycanrocmidday",
        "Lycanroc Midnight": "lycanrocmidnight",
        "Lycanroc Dusk": "lycanrocdusk",

        # =====================================================
        # HISUI
        # =====================================================

        "Growlithe Hisui": "growlithehisui",
        "Arcanine Hisui": "arcaninehisui",
        "Voltorb Hisui": "voltorbhisui",
        "Electrode Hisui": "electrodehisui",
        "Qwilfish Hisui": "qwilfishhisui",
        "Sneasel Hisui": "sneaselhisui",
        "Samurott Hisui": "samurotthisui",
        "Lilligant Hisui": "lilliganthisui",
        "Zorua Hisui": "zoruahisui",
        "Zoroark Hisui": "zoroarkhisui",
        "Braviary Hisui": "braviaryhisui",
        "Sliggoo Hisui": "sliggoohisui",
        "Goodra Hisui": "goodrahisui",
        "Avalugg Hisui": "avalugghisui",
        "Decidueye Hisui": "decidueyehisui",
        "Typhlosion Hisui": "typhlosionhisui",
    }

    if name in SPECIES_KEYS:
        return SPECIES_KEYS[name]

    # =====================================================
    # NORMAL SPECIES
    # =====================================================

    clean = (
        name
        .lower()
        .replace("’", "")
        .replace("'", "")
        .replace(".", "")
        .replace("♀", "f")
        .replace("♂", "m")
    )

    # Preserve the form separator rather than deleting it.
    clean = clean.replace(" ", "-")

    # Remove Mega prefix only for Mega lookup compatibility.
    if clean.startswith("mega-"):
        clean = clean[5:]

    return clean

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
