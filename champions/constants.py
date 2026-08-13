from typing import Dict


CURRENT_REGULATION = "M-B"


TYPE_COLORS = {
    "Normal": "#A8A77A", "Fire": "#EE8130", "Water": "#6390F0", "Electric": "#F7D02C",
    "Grass": "#7AC74C", "Ice": "#96D9D6", "Fighting": "#C22E28", "Poison": "#A33EA1",
    "Ground": "#E2BF65", "Flying": "#A98FF3", "Psychic": "#F95587", "Bug": "#A6B91A",
    "Rock": "#B6A136", "Ghost": "#735797", "Dragon": "#6F35FC", "Dark": "#705746",
    "Steel": "#B7B7CE", "Fairy": "#D685AD"
}


TYPE_SVG_URLS = {
    "Normal": "https://raw.githubusercontent.com/duiker101/pokemon-type-svg-icons/master/icons/normal.svg",
    "Fire": "https://raw.githubusercontent.com/duiker101/pokemon-type-svg-icons/master/icons/fire.svg",
    "Water": "https://raw.githubusercontent.com/duiker101/pokemon-type-svg-icons/master/icons/water.svg",
    "Electric": "https://raw.githubusercontent.com/duiker101/pokemon-type-svg-icons/master/icons/electric.svg",
    "Grass": "https://raw.githubusercontent.com/duiker101/pokemon-type-svg-icons/master/icons/grass.svg",
    "Ice": "https://raw.githubusercontent.com/duiker101/pokemon-type-svg-icons/master/icons/ice.svg",
    "Fighting": "https://raw.githubusercontent.com/duiker101/pokemon-type-svg-icons/master/icons/fighting.svg",
    "Poison": "https://raw.githubusercontent.com/duiker101/pokemon-type-svg-icons/master/icons/poison.svg",
    "Ground": "https://raw.githubusercontent.com/duiker101/pokemon-type-svg-icons/master/icons/ground.svg",
    "Flying": "https://raw.githubusercontent.com/duiker101/pokemon-type-svg-icons/master/icons/flying.svg",
    "Psychic": "https://raw.githubusercontent.com/duiker101/pokemon-type-svg-icons/master/icons/psychic.svg",
    "Bug": "https://raw.githubusercontent.com/duiker101/pokemon-type-svg-icons/master/icons/bug.svg",
    "Rock": "https://raw.githubusercontent.com/duiker101/pokemon-type-svg-icons/master/icons/rock.svg",
    "Ghost": "https://raw.githubusercontent.com/duiker101/pokemon-type-svg-icons/master/icons/ghost.svg",
    "Dragon": "https://raw.githubusercontent.com/duiker101/pokemon-type-svg-icons/master/icons/dragon.svg",
    "Dark": "https://raw.githubusercontent.com/duiker101/pokemon-type-svg-icons/master/icons/dark.svg",
    "Steel": "https://raw.githubusercontent.com/duiker101/pokemon-type-svg-icons/master/icons/steel.svg",
    "Fairy": "https://raw.githubusercontent.com/duiker101/pokemon-type-svg-icons/master/icons/fairy.svg"
}


NATURES = [
    "Adamant (+Atk, -SpA)", "Bold (+Def, -Atk)", "Brave (+Atk, -Spe)", "Calm (+SpD, -Atk)",
    "Careful (+SpD, -SpA)", "Gentle (+SpD, -Def)", "Hardy", "Hasty (+Spe, -Def)",
    "Impish (+Def, -SpA)", "Jolly (+Spe, -SpA)", "Lax (+Def, -SpD)", "Lonely (+Atk, -Def)",
    "Mild (+SpA, -Def)", "Modest (+SpA, -Atk)", "Naive (+Spe, -SpD)", "Naughty (+Atk, -SpD)",
    "Quiet (+SpA, -Spe)", "Rash (+SpA, -SpD)", "Relaxed (+Def, -Spe)", "Sassy (+SpD, -Spe)",
    "Serious", "Timid (+Spe, -Atk)"
]


SPECIES_DISPLAY_OVERRIDES = {
    "taurospaldeacombat": "Tauros Paldea Combat",
    "taurospaldeacombatbreed": "Tauros Paldea Combat",
    "taurospaldeablaze": "Tauros Paldea Blaze",
    "taurospaldeaaqua": "Tauros Paldea Aqua",

    "tauros-paldea-combat-breed": "Tauros Paldea Combat",
    "tauros-paldea-blaze": "Tauros Paldea Blaze",
    "tauros-paldea-aqua": "Tauros Paldea Aqua",

    "basculegion-male": "Basculegion",
    "basculegion-m": "Basculegion",
    "basculegionm": "Basculegion",
    "basculegion-f": "Basculegion Female",
    "basculegion-female": "Basculegion Female",
    "basculegionf": "Basculegion Female",

    "indeedeef": "Indeedee Female",
    "indeedee-f": "Indeedee Female",
    "indeedee-female": "Indeedee Female",

    "indeedeem": "Indeedee Male",
    "indeedee-m": "Indeedee Male",
    "indeedee-male": "Indeedee Male",

    "meowsticmale": "Meowstic Male",
    "meowstic-m": "Meowstic Male",
    "meowstic-male": "Meowstic Male",

    "meowsticfemale": "Meowstic Female",
    "meowstic-f": "Meowstic Female",
    "meowstic-female": "Meowstic Female",

    "oinkolognem": "Oinkologne Male",
    "oinkologne-m": "Oinkologne Male",

    "oinkolognef": "Oinkologne Female",
    "oinkologne-f": "Oinkologne Female",

    "mr-mime": "Mr. Mime",
    "mime-jr": "Mime Jr.",
    "ho-oh": "Ho-Oh",
    "nidoran-f": "Nidoran Female",
    "nidoran-m": "Nidoran Male",
    "farfetchd": "Farfetch'd",
    "sirfetchd": "Sirfetch'd",
    "flabebe": "Flabébé",
    "type-null": "Type: Null",
}

TYPE_CHART_DATA: Dict[str, Dict[str, float]] = {
    "Normal": {"Rock": 0.5, "Ghost": 0.0, "Steel": 0.5},
    "Fire": {"Fire": 0.5, "Water": 0.5, "Grass": 2.0, "Ice": 2.0, "Bug": 2.0, "Rock": 0.5, "Dragon": 0.5, "Steel": 2.0},
    "Water": {"Fire": 2.0, "Water": 0.5, "Grass": 0.5, "Ground": 2.0, "Rock": 2.0, "Dragon": 0.5},
    "Electric": {"Water": 2.0, "Electric": 0.5, "Grass": 0.5, "Ground": 0.0, "Flying": 2.0, "Dragon": 0.5},
    "Grass": {"Fire": 0.5, "Water": 2.0, "Grass": 0.5, "Poison": 0.5, "Ground": 2.0, "Flying": 0.5, "Bug": 0.5, "Rock": 2.0, "Dragon": 0.5, "Steel": 0.5},
    "Ice": {"Fire": 0.5, "Water": 0.5, "Grass": 2.0, "Ice": 0.5, "Ground": 2.0, "Flying": 2.0, "Dragon": 2.0, "Steel": 0.5},
    "Fighting": {"Normal": 2.0, "Ice": 2.0, "Poison": 0.5, "Flying": 0.5, "Psychic": 0.5, "Bug": 0.5, "Rock": 2.0, "Ghost": 0.0, "Dark": 2.0, "Steel": 2.0, "Fairy": 0.5},
    "Poison": {"Grass": 2.0, "Poison": 0.5, "Ground": 0.5, "Rock": 0.5, "Ghost": 0.5, "Steel": 0.0, "Fairy": 2.0},
    "Ground": {"Fire": 2.0, "Electric": 2.0, "Grass": 0.5, "Poison": 2.0, "Flying": 0.0, "Bug": 0.5, "Rock": 2.0, "Steel": 2.0},
    "Flying": {"Electric": 0.5, "Grass": 2.0, "Fighting": 2.0, "Bug": 2.0, "Rock": 0.5, "Steel": 0.5},
    "Psychic": {"Fighting": 2.0, "Poison": 2.0, "Psychic": 0.5, "Steel": 0.5, "Dark": 0.0},
    "Bug": {"Fire": 0.5, "Grass": 2.0, "Fighting": 0.5, "Poison": 0.5, "Flying": 0.5, "Psychic": 2.0, "Ghost": 0.5, "Dark": 2.0, "Steel": 0.5, "Fairy": 0.5},
    "Rock": {"Fire": 2.0, "Ice": 2.0, "Fighting": 0.5, "Ground": 0.5, "Flying": 2.0, "Bug": 2.0, "Steel": 0.5},
    "Ghost": {"Normal": 0.0, "Psychic": 2.0, "Ghost": 2.0, "Dark": 0.5},
    "Dragon": {"Dragon": 2.0, "Steel": 0.5, "Fairy": 0.0},
    "Dark": {"Fighting": 0.5, "Psychic": 2.0, "Ghost": 2.0, "Dark": 0.5, "Fairy": 0.5},
    "Steel": {"Fire": 0.5, "Water": 0.5, "Electric": 0.5, "Ice": 2.0, "Rock": 2.0, "Steel": 0.5, "Fairy": 2.0},
    "Fairy": {"Fire": 0.5, "Fighting": 2.0, "Poison": 0.5, "Dragon": 2.0, "Dark": 2.0, "Steel": 0.5}
}