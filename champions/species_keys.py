def canonical_species_key(name):
    """
    Converts a Pokémon name into ONE stable internal key.

    Important:
    - Keeps meaningful form information.
    - Does NOT squash words together.
    - Does NOT try to guess a PokeAPI ID.
    - Does NOT remove form names.
    """
    if not name:
        return ""

    text = str(name).strip().lower()

    text = text.replace("’", "'")
    text = text.replace("_", "-")
    text = " ".join(text.split())
    text = text.replace(" - ", "-")
    text = text.replace(" -", "-")
    text = text.replace("- ", "-")

    aliases = {
        "basculegion male": "Basculegion",
        "basculegion female": "Basculegion Female",
        "basculegion-male": "Basculegion",
        "basculegion-female": "Basculegion Female",
        "rotom wash": "rotom-wash",
        "rotom heat": "rotom-heat",
        "rotom frost": "rotom-frost",
        "rotom fan": "rotom-fan",
        "rotom mow": "rotom-mow",
        "lycanroc midday": "lycanroc-midday",
        "lycanroc midnight": "lycanroc-midnight",
        "lycanroc dusk": "lycanroc-dusk",
        "slowbro galar": "slowbro-galar",
        "slowking galar": "slowking-galar",
        "mr mime galar": "mr-mime-galar",
        "braviary hisui": "braviary-hisui",
        "decidueye hisui": "decidueye-hisui",
        "electrode hisui": "electrode-hisui",
        "goodra hisui": "goodra-hisui",
        "lilligant hisui": "lilligant-hisui",
        "qwilfish hisui": "qwilfish-hisui",
        "samurott hisui": "samurott-hisui",
        "sliggoo hisui": "sliggoo-hisui",
        "typhlosion hisui": "typhlosion-hisui",
        "voltorb hisui": "voltorb-hisui",
        "zoroark hisui": "zoroark-hisui",
        "avalugg hisui": "avalugg-hisui",
        "arcanine hisui": "arcanine-hisui",
        "decidueye hisuian": "decidueye-hisui",
        "lilligant hisuian": "lilligant-hisui",
        "zoroark hisuian": "zoroark-hisui",
        "raichu alola": "raichu-alola",
        "rattata alola": "rattata-alola",
        "raticate alola": "raticate-alola",
        "sandshrew alola": "sandshrew-alola",
        "sandslash alola": "sandslash-alola",
        "vulpix alola": "vulpix-alola",
        "ninetales alola": "ninetales-alola",
        "diglett alola": "diglett-alola",
        "dugtrio alola": "dugtrio-alola",
        "meowth alola": "meowth-alola",
        "persian alola": "persian-alola",
        "geodude alola": "geodude-alola",
        "graveler alola": "graveler-alola",
        "golem alola": "golem-alola",
        "grimer alola": "grimer-alola",
        "muk alola": "muk-alola",
        "wooper paldea": "wooper-paldea",
    }

    if text == "taurospaldeacombat" or text == "taurospaldeacombatbreed":
        text = "tauros-paldea-combat-breed"
    elif text == "taurospaldeablaze":
        text = "tauros-paldea-blaze"
    elif text == "taurospaldeaaqua":
        text = "tauros-paldea-aqua"

    return aliases.get(text, text)
