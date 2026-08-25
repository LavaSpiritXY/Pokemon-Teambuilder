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

CUSTOM_MEGAS_DATA = {
    "Mega Abomasnow": {"ability": "Snow Warning", "hp": 90, "atk": 132, "def": 105, "spa": 132, "spd": 105, "spd_stat": 30},
    "Mega Venusaur": {"ability": "Thick Fat", "hp": 80, "atk": 100, "def": 123, "spa": 122, "spd": 120, "spd_stat": 80},
    "Mega Charizard X": {"ability": "Tough Claws", "hp": 78, "atk": 130, "def": 111, "spa": 130, "spd": 85, "spd_stat": 100},
    "Mega Charizard Y": {"ability": "Drought", "hp": 78, "atk": 104, "def": 78, "spa": 159, "spd": 115, "spd_stat": 100},
    "Mega Blastoise": {"ability": "Mega Launcher", "hp": 79, "atk": 103, "def": 120, "spa": 135, "spd": 115, "spd_stat": 78},
    "Mega Beedrill": {"ability": "Adaptability", "hp": 65, "atk": 150, "def": 40, "spa": 15, "spd": 80, "spd_stat": 145},
    "Mega Pidgeot": {"ability": "No Guard", "hp": 83, "atk": 80, "def": 80, "spa": 135, "spd": 80, "spd_stat": 121},
    "Mega Raichu X": {"ability": "Electric Surge", "hp": 60, "atk": 135, "def": 95, "spa": 90, "spd": 95, "spd_stat": 110},
    "Mega Raichu Y": {"ability": "No Guard", "hp": 60, "atk": 100, "def": 55, "spa": 160, "spd": 80, "spd_stat": 130},
    "Mega Clefable": {"ability": "Magic Bounce", "hp": 95, "atk": 80, "def": 93, "spa": 135, "spd": 110, "spd_stat": 70},
    "Mega Alakazam": {"ability": "Trace", "hp": 55, "atk": 50, "def": 65, "spa": 175, "spd": 105, "spd_stat": 150},
    "Mega Victreebel": {"ability": "Innards Out", "hp": 80, "atk": 125, "def": 85, "spa": 135, "spd": 95, "spd_stat": 70},
    "Mega Slowbro": {"ability": "Shell Armor", "hp": 95, "atk": 75, "def": 180, "spa": 130, "spd": 80, "spd_stat": 30},
    "Mega Gengar": {"ability": "Shadow Tag", "hp": 60, "atk": 65, "def": 80, "spa": 170, "spd": 95, "spd_stat": 130},
    "Mega Kangaskhan": {"ability": "Parental Bond", "hp": 105, "atk": 125, "def": 100, "spa": 60, "spd": 100, "spd_stat": 100},
    "Mega Starmie": {"ability": "Huge Power", "hp": 60, "atk": 100, "def": 105, "spa": 130, "spd": 105, "spd_stat": 120},
    "Mega Pinsir": {"ability": "Aerilate", "hp": 65, "atk": 155, "def": 120, "spa": 65, "spd": 90, "spd_stat": 105},
    "Mega Gyarados": {"ability": "Mold Breaker", "hp": 95, "atk": 155, "def": 109, "spa": 70, "spd": 130, "spd_stat": 81},
    "Mega Aerodactyl": {"ability": "Tough Claws", "hp": 80, "atk": 135, "def": 85, "spa": 70, "spd": 95, "spd_stat": 150},
    "Mega Dragonite": {"ability": "Multiscale", "hp": 91, "atk": 124, "def": 115, "spa": 145, "spd": 125, "spd_stat": 100},
    "Mega Tyranitar": {"ability": "Sand Stream", "hp": 100, "atk": 164, "def": 150, "spa": 95, "spd": 120, "spd_stat": 71},
    "Mega Sceptile": {"ability": "Lightning Rod", "hp": 70, "atk": 110, "def": 75, "spa": 145, "spd": 85, "spd_stat": 145},
    "Mega Blaziken": {"ability": "Speed Boost", "hp": 80, "atk": 160, "def": 80, "spa": 130, "spd": 80, "spd_stat": 100},
    "Mega Swampert": {"ability": "Swift Swim", "hp": 100, "atk": 150, "def": 110, "spa": 95, "spd": 110, "spd_stat": 70},
    "Mega Gardevoir": {"ability": "Pixilate", "hp": 68, "atk": 85, "def": 65, "spa": 165, "spd": 135, "spd_stat": 100},
    "Mega Sableye": {"ability": "Magic Bounce", "hp": 50, "atk": 85, "def": 125, "spa": 85, "spd": 115, "spd_stat": 20},
    "Mega Mawile": {"ability": "Huge Power", "hp": 50, "atk": 105, "def": 125, "spa": 55, "spd": 95, "spd_stat": 50},
    "Mega Aggron": {"ability": "Filter", "hp": 70, "atk": 140, "def": 230, "spa": 60, "spd": 80, "spd_stat": 50},
    "Mega Medicham": {"ability": "Pure Power", "hp": 60, "atk": 100, "def": 85, "spa": 80, "spd": 85, "spd_stat": 100},
    "Mega Manectric": {"ability": "Intimidate", "hp": 70, "atk": 75, "def": 80, "spa": 135, "spd": 80, "spd_stat": 135},
    "Mega Sharpedo": {"ability": "Strong Jaw", "hp": 70, "atk": 140, "def": 70, "spa": 110, "spd": 65, "spd_stat": 105},
    "Mega Camerupt": {"ability": "Sheer Force", "hp": 70, "atk": 120, "def": 100, "spa": 145, "spd": 105, "spd_stat": 20},
    "Mega Altaria": {"ability": "Pixilate", "hp": 75, "atk": 110, "def": 110, "spa": 110, "spd": 105, "spd_stat": 80},
    "Mega Banette": {"ability": "Prankster", "hp": 64, "atk": 165, "def": 75, "spa": 93, "spd": 83, "spd_stat": 75},
    "Mega Absol": {"ability": "Magic Bounce", "hp": 65, "atk": 150, "def": 60, "spa": 115, "spd": 60, "spd_stat": 115},
    "Mega Glalie": {"ability": "Refrigerate", "hp": 80, "atk": 120, "def": 80, "spa": 120, "spd": 80, "spd_stat": 100},
    "Mega Metagross": {"ability": "Tough Claws", "hp": 80, "atk": 145, "def": 150, "spa": 105, "spd": 110, "spd_stat": 110},
    "Mega Staraptor": {"ability": "Contrary", "hp": 85, "atk": 140, "def": 100, "spa": 60, "spd": 90, "spd_stat": 110},
    "Mega Lopunny": {"ability": "Scrappy", "hp": 65, "atk": 136, "def": 94, "spa": 54, "spd": 96, "spd_stat": 135},
    "Mega Garchomp": {"ability": "Sand Force", "hp": 108, "atk": 170, "def": 115, "spa": 120, "spd": 95, "spd_stat": 92},
    "Mega Lucario": {"ability": "Adaptability", "hp": 70, "atk": 145, "def": 88, "spa": 140, "spd": 70, "spd_stat": 112},
    "Mega Gallade": {"ability": "Inner Focus", "hp": 68, "atk": 165, "def": 95, "spa": 65, "spd": 115, "spd_stat": 110},
    "Mega Emboar": {"ability": "Mold Breaker", "hp": 110, "atk": 148, "def": 75, "spa": 110, "spd": 110, "spd_stat": 75},
    "Mega Excadrill": {"ability": "Piercing Drill", "hp": 110, "atk": 165, "def": 100, "spa": 65, "spd": 65, "spd_stat": 103},
    "Mega Audino": {"ability": "Healer", "hp": 103, "atk": 60, "def": 126, "spa": 80, "spd": 126, "spd_stat": 50},
    "Mega Scrafty": {"ability": "Intimidate", "hp": 65, "atk": 130, "def": 135, "spa": 55, "spd": 135, "spd_stat": 68},
    "Mega Chandelure": {"ability": "Infiltrator", "hp": 60, "atk": 75, "def": 110, "spa": 175, "spd": 110, "spd_stat": 90},
    "Mega Golurk": {"ability": "Unseen Fist", "hp": 89, "atk": 159, "def": 105, "spa": 70, "spd": 105, "spd_stat": 55},
    "Mega Greninja": {"ability": "Protean", "hp": 72, "atk": 125, "def": 77, "spa": 133, "spd": 81, "spd_stat": 142},
    "Mega Floette": {"ability": "Fairy Aura", "hp": 74, "atk": 85, "def": 87, "spa": 155, "spd": 148, "spd_stat": 102},
    "Mega Meowstic Male": {"ability": "Trace", "hp": 74, "atk": 48, "def": 76, "spa": 143, "spd": 101, "spd_stat": 124},
    "Mega Meowstic Female": {"ability": "Trace", "hp": 74, "atk": 48, "def": 76, "spa": 83, "spd": 81, "spd_stat": 104},
    "Mega Malamar": {"ability": "Contrary", "hp": 86, "atk": 102, "def": 88, "spa": 98, "spd": 120, "spd_stat": 88},
    "Mega Barbaracle": {"ability": "Tough Claws", "hp": 72, "atk": 140, "def": 130, "spa": 64, "spd": 106, "spd_stat": 88},
    "Mega Dragalge": {"ability": "Regenerator", "hp": 65, "atk": 85, "def": 105, "spa": 132, "spd": 163, "spd_stat": 44},
    "Mega Hawlucha": {"ability": "No Guard", "hp": 78, "atk": 137, "def": 100, "spa": 74, "spd": 93, "spd_stat": 118},
    "Mega Glimmora": {"ability": "Adaptability", "hp": 83, "atk": 90, "def": 105, "spa": 150, "spd": 96, "spd_stat": 101}
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
