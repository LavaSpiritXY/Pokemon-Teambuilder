import re

import requests
import streamlit as strlit

from champions.constants import SPECIES_DISPLAY_OVERRIDES

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
    """
    Convert a Champions/Showdown species ID into a stable,
    human-readable Pokémon name.

    This function deliberately handles multiple possible spellings
    of the same form so that:
        rotomwash
        rotom-wash
        Rotom Wash
    all become:
        Rotom Wash
    """

    if not species_key:
        return species_key

    raw = str(species_key).strip().lower()

    # ---------------------------------------------------------
    # NORMALISE THE INPUT FOR FORM LOOKUP
    # ---------------------------------------------------------

    # Remove punctuation and separators ONLY for the purpose
    # of matching against our aliases.
    lookup = re.sub(r"[^a-z0-9]", "", raw)

    FORM_NAMES = {

        # =====================================================
        # BASCULEGION
        # =====================================================

        "basculegionm": "Basculegion",
        "basculegion-male": "Basculegion",

        "basculegionf": "Basculegion Female",
        "basculegionfemale": "Basculegion Female",

        # =====================================================
        # FLOETTE
        # =====================================================

        "floette": "Floette",
        "floetteeternal": "Floette Eternal",

        # =====================================================
        # MEOWSTIC
        # =====================================================

        "meowstic": "Meowstic Male",
        "meowsticm": "Meowstic Male",
        "meowsticmale": "Meowstic Male",
        "meowsticf": "Meowstic Female",
        "meowsticfemale": "Meowstic Female",

        # =====================================================
        # MR. RIME
        # =====================================================

        "mrrime": "Mr. Rime",

        # =====================================================
        # ROTOM
        # =====================================================

        "rotom": "Rotom",

        "rotomheat": "Rotom Heat",
        "rotomwash": "Rotom Wash",
        "rotomfrost": "Rotom Frost",
        "rotomfan": "Rotom Fan",
        "rotommow": "Rotom Mow",

        # =====================================================
        # TAUROS PALDEA
        # =====================================================

        "tauros": "Tauros",

        "tauros-paldea-combat-breed": "Tauros Paldea Combat Breed",
        "tauros-paldea-aqua-breed": "Tauros Paldea Aqua Breed",
        "tauros-paldea-blaze-breed": "Tauros Paldea Blaze Breed",

        # =====================================================
        # LYCANROC
        # =====================================================

        "lycanroc": "Lycanroc Midday",
        "lycanrocmidday": "Lycanroc Midday",
        "lycanrocday": "Lycanroc Midday",

        "lycanrocmidnight": "Lycanroc Midnight",
        "lycanrocnight": "Lycanroc Midnight",

        "lycanrocdusk": "Lycanroc Dusk",

        # =====================================================
        # HISUI
        # =====================================================

        "growlithehisui": "Growlithe Hisui",
        "arcaninehisui": "Arcanine Hisui",

        "voltorbhisui": "Voltorb Hisui",
        "electrodehisui": "Electrode Hisui",

        "qwilfishhisui": "Qwilfish Hisui",
        "sneaselhisui": "Sneasel Hisui",

        "samurotthisui": "Samurott Hisui",
        "samurotthisuian": "Samurott Hisui",

        "lilliganthisui": "Lilligant Hisui",

        "zoruahisui": "Zorua Hisui",
        "zoroarkhisui": "Zoroark Hisui",

        "braviaryhisui": "Braviary Hisui",

        "sliggoohisui": "Sliggoo Hisui",
        "goodrahisui": "Goodra Hisui",

        "avalugghisui": "Avalugg Hisui",

        "decidueyehisui": "Decidueye Hisui",

        "typhlosionhisui": "Typhlosion Hisui",

        # =====================================================
        # ALOLA
        # =====================================================

        "raichualola": "Raichu Alola",

        "rattataalola": "Rattata Alola",
        "raticatealola": "Raticate Alola",

        "sandshrewalola": "Sandshrew Alola",
        "sandslashalola": "Sandslash Alola",

        "vulpixalola": "Vulpix Alola",
        "ninetalesalola": "Ninetales Alola",

        "diglettalola": "Diglett Alola",
        "dugtrioalola": "Dugtrio Alola",

        "meowthalola": "Meowth Alola",
        "persianalola": "Persian Alola",

        "geodudealola": "Geodude Alola",
        "graveleralola": "Graveler Alola",
        "golemalola": "Golem Alola",

        "grimeralola": "Grimer Alola",
        "mukalola": "Muk Alola",

        # =====================================================
        # GALAR
        # =====================================================

        "slowbrogalar": "Slowbro Galar",
        "slowkinggalar": "Slowking Galar",

        "mrmimegalar": "Mr. Mime Galar",

        "stunfiskgalar": "Stunfisk Galar",

        "meowthgalar": "Meowth Galar",
        "ponytagalar": "Ponyta Galar",
        "rapidashgalar": "Rapidash Galar",

        "farfetchdgalar": "Farfetch'd Galar",
        "weezinggalar": "Weezing Galar",

        "corsolagalar": "Corsola Galar",
        "zigzagoongalar": "Zigzagoon Galar",
        "linoonegalar": "Linoone Galar",

        "darumakagalar": "Darumaka Galar",
        "darmanitangalar": "Darmanitan Galar",

        "yamaskgalar": "Yamask Galar",

        # =====================================================
        # OTHER SPECIAL NAMES
        # =====================================================

        "mrmime": "Mr. Mime",
        "mimejr": "Mime Jr.",
        "farfetchd": "Farfetch'd",
        "sirfetchd": "Sirfetch'd",
        "flabebe": "Flabébé",
        "type-null": "Type: Null",
        "typenull": "Type: Null",
        "hooh": "Ho-Oh",
    }

    # ---------------------------------------------------------
    # FIRST: FORM ALIAS LOOKUP
    # ---------------------------------------------------------

    if lookup in FORM_NAMES:
        return FORM_NAMES[lookup]

    # ---------------------------------------------------------
    # SECOND: EXISTING OVERRIDES
    # ---------------------------------------------------------

    if raw in SPECIES_DISPLAY_OVERRIDES:
        return SPECIES_DISPLAY_OVERRIDES[raw]

    # ---------------------------------------------------------
    # THIRD: GENERIC FALLBACK
    # ---------------------------------------------------------

    pretty = (
        raw
        .replace("_", "-")
        .replace("-", " ")
        .replace("’", "'")
    )

    return " ".join(
        word.title()
        for word in pretty.split()
    )
