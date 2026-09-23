from typing import Dict

from champions.registry import load_registry



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
    "persianalola": "Persian Alola",
    "persian-alola": "Persian Alola",
    "toxtricityamped": "Toxtricity Amped",
    "toxtricity-amped": "Toxtricity Amped",
    "toxtricitylowkey": "Toxtricity Low Key",
    "toxtricity-low-key": "Toxtricity Low Key",
    "squawkabillygreen": "Squawkabilly Green",
    "squawkabilly-green": "Squawkabilly Green",
    "squawkabillyblue": "Squawkabilly Blue",
    "squawkabilly-blue": "Squawkabilly Blue",
    "squawkabillyyellow": "Squawkabilly Yellow",
    "squawkabilly-yellow": "Squawkabilly Yellow",
    "squawkabillywhite": "Squawkabilly White",
    "squawkabilly-white": "Squawkabilly White",
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
    "Fairy": {"Fire": 0.5, "Fighting": 2.0, "Poison": 0.5}
    entry["display_name"]: {
        "ability": (entry.get("abilities") or ["Standard"])[0],
        "hp": entry["base_stats"]["hp"],
        "atk": entry["base_stats"]["atk"],
        "def": entry["base_stats"]["def"],
        "spa": entry["base_stats"]["spa"],
        "spd": entry["base_stats"]["spd"],
        "spd_stat": entry["base_stats"]["spe"],
    }
    for entry in load_registry()["megas"].values()
    if entry.get("display_name")
}


7, "spa": 105, "spd": 101, "spd_stat": 87}
}

BASE_HELD_ITEMS = [
    "Air Balloon", "Assault Vest", "Babiri Berry", "Binding Band", "Black Belt", "Black Sludge",
    "Choice Band", "Choice Scarf", "Choice Specs", "Clear Amulet", "Covert Cloak", "Damp Rock",
    "Eviolite", "Expert Belt", "Focus Sash", "Heat Rock", "Heavy-Duty Boots", "Iapapa Berry",
    "Ice Rock", "Kee Berry", "Kings Rock", "Leftovers", "Life Orb", "Light Clay", "Loaded Dice",
    "Lum Berry", "Maranga Berry", "Mental Herb", "Miracle Seed", "Mystic Water", "Never-Melt Ice",
    "Normal Gem", "Occa Berry", "Passho Berry", "Payapa Berry", "Protective Pads", "Punching Glove",
    "Rawst Berry", "Red Card", "Rindo Berry", "Rocky Helmet", "Safety Goggles", "Salac Berry",
    "Scope Lens", "Shuca Berry", "Silk Scarf", "Sitrus Berry", "Smooth Rock", "Soft Sand",
    "Spell Tag", "Throat Spray", "Toxic Orb", "Twisted Spoon", "Weakness Policy", "White Herb", "Yache Berry"
]

MOVE_TYPE_OVERRIDES = {
    "dragon dance": "Dragon", "dragon claw": "Dragon", "draco meteor": "Dragon", "outrage": "Dragon",
    "flare blitz": "Fire", "flamethrower": "Fire", "fire blast": "Fire", "overheat": "Fire", "heat wave": "Fire",
    "roost": "Flying", "brave bird": "Flying", "air slash": "Flying", "hurricane": "Flying", "acrobatics": "Flying",
    "earthquake": "Ground", "earth power": "Ground", "high horsepower": "Ground", "spikes": "Ground",
    "stealth rock": "Rock", "stone edge": "Rock", "rock slide": "Rock", "rock blast": "Rock",
    "close combat": "Fighting", "drain punch": "Fighting", "aura sphere": "Fighting", "focus blast": "Fighting",
    "ice punch": "Ice", "ice beam": "Ice", "blizzard": "Ice", "icicle spear": "Ice", "freeze-dry": "Ice",
    "thunder punch": "Electric", "thunderbolt": "Electric", "thunder": "Electric", "volt switch": "Electric",
    "swords dance": "Normal", "protect": "Normal", "substitute": "Normal", "extreme speed": "Normal", "rapid spin": "Normal",
    "toxic": "Poison", "sludge wave": "Poison", "sludge bomb": "Poison", "gunk shot": "Poison", "mortal spin": "Poison",
    "shadow ball": "Ghost", "shadow claw": "Ghost", "poltergeist": "Ghost", "destiny bond": "Ghost", "hex": "Ghost",
    "psychic": "Psychic", "psyshock": "Psychic", "zen headbutt": "Psychic", "calm mind": "Psychic", "trick room": "Psychic",
    "play rough": "Fairy", "moonblast": "Fairy", "dazzling gleam": "Fairy", "spirit break": "Fairy",
    "iron head": "Steel", "bullet punch": "Steel", "meteor mash": "Steel", "flash cannon": "Steel", "defog": "Flying",
    "hydro pump": "Water", "surf": "Water", "liquidation": "Water", "flip turn": "Water", "water shuriken": "Water",
    "giga drain": "Grass", "leaf blade": "Grass", "power whip": "Grass", "energy ball": "Grass", "wood hammer": "Grass",
    "dark pulse": "Dark", "crunch": "Dark", "sucker punch": "Dark", "knock off": "Dark", "parting shot": "Dark",
    "u-turn": "Bug", "quiver dance": "Bug", "bug buzz": "Bug", "first impression": "Bug"
}

# ==========================================
# ARCHETYPE & ENABLER REGISTRY
# ==========================================

ARCHETYPE_DEFINITIONS = {
    "Tailwind Enabler": {
        "abilities": ["Prankster", "Gale Wings", "Wind Power"],
        "moves": ["Tailwind"],
        "role_label": "Dedicated Speed Control / Tailwind Lead",
        "boost": 25
    },
    "Rain Setter": {
        "abilities": ["Drizzle"],
        "moves": ["Rain Dance"],
        "role_label": "Weather Anchor (Rain)",
        "boost": 20
    },
    "Sun Setter": {
        "abilities": ["Drought", "Orichalcum Pulse"],
        "moves": ["Sunny Day"],
        "role_label": "Weather Anchor (Sun)",
        "boost": 20
    },
    "Terrain Anchor": {
        "abilities": [
            "Psychic Surge",
            "Grassy Surge",
            "Electric Surge",
            "Misty Surge",
            "Sand Stream"
        ],
        "moves": [
            "Psychic Terrain",
            "Grassy Terrain",
            "Electric Terrain",
            "Misty Terrain",
            "Sandstorm"
        ],
        "role_label": "Terrain / Weather Anchor",
        "boost": 20
    },
    "Priority Blocker": {
        "abilities": ["Armor Tail", "Queenly Majesty", "Psychic Surge"],
        "moves": [],
        "role_label": "Defensive Utility / Anti-Priority",
        "boost": 18
    }
}

MOVE_DISPLAY_OVERRIDES = {
    "storedpower": "Stored Power",
    "stompingtantrum": "Stomping Tantrum",
    "doubleironbash": "Double Iron Bash",
    "populationbomb": "Population Bomb",
    "gigatonhammer": "Gigaton Hammer",
    "lastrespects": "Last Respects",
    "tripleaxel": "Triple Axel",
}

TYPE_DEFENSES = {
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
    "Steel": {"Fire": 0.5, "Water": 0.5, "Electric": 0.5, "Ice": 2.0, "Rock": 2.0, "Fairy": 2.0, "Steel": 0.5},
    "Fairy": {"Fire": 0.5, "Fighting": 2.0, "Poison": 0.5, "Dragon": 2.0, "Dark": 2.0, "Steel": 0.5},
}
