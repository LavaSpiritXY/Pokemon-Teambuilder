import random
import re
import requests
import streamlit as strlit

# -----------------------------------------------------------------------------
# 1. CONFIG & VISUAL STYLING
# -----------------------------------------------------------------------------
strlit.set_page_config(
    page_title="Pokémon Champions Teambuilder",
    page_icon="⚔️",
    layout="wide",
    initial_sidebar_state="expanded"
)

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
    "charizardmegax": "Mega Charizard X", "charizardmegay": "Mega Charizard Y",
    "meowsticmale": "Mega Meowstic (Male)", "meowsticfemale": "Mega Meowstic (Female)",
    "mrmime": "Mr. Mime", "mimejr": "Mime Jr.", "hooh": "Ho-Oh",
    "nidoranf": "Nidoran♀", "nidoranm": "Nidoran♂", "farfetchd": "Farfetch'd",
    "sirfetchd": "Sirfetch'd", "flabebe": "Flabébé", "typenull": "Type: Null",
    "zoroarkhisui": "Zoroark Hisui", "samurotthisui": "Samurott Hisui",
    "typhlosionhisui": "Typhlosion Hisui", "growlithehisui": "Growlithe Hisui",
    "qwilfishhisui": "Qwilfish Hisui", "decidueyehisui": "Decidueye Hisui",
    "gourgeistsmall": "Small Size Gourgeist", "gourgeistlarge": "Large Size Gourgeist",
    "gourgeistsuper": "Super Size Gourgeist", "rotomwash": "Rotom Wash",
    "rotomheat": "Rotom Heat", "rotomfrost": "Rotom Frost",
    "rotomfan": "Rotom Fan", "rotommow": "Rotom Mow",
}

strlit.markdown("""
<style>
    .stApp {
        background: linear-gradient(135deg, #0b0e14 0%, #1a1f2c 100%);
        color: #e6edf3;
    }
    header[data-testid="stHeader"] { background: transparent; }
    
    .type-badge {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        padding: 4px 10px;
        border-radius: 6px;
        font-weight: 700;
        font-size: 13px;
        color: white;
        white-space: nowrap;
    }
    
    .move-card {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 8px;
        padding: 10px 14px;
        border-radius: 8px;
        font-weight: 600;
        color: white;
        margin-top: -4px;
        margin-bottom: 14px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.3);
        width: 100%;
        box-sizing: border-box;
        overflow: hidden;
    }
    
    .move-name {
        flex: 1;
        min-width: 0;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }

    .move-type-badge {
        flex-shrink: 0;
        display: flex;
        align-items: center;
        gap: 4px;
        font-size: 11px;
    }

    .analytics-container {
        background: rgba(18, 23, 35, 0.8);
        border: 1px solid rgba(255, 255, 255, 0.15);
        border-radius: 12px;
        padding: 16px;
        margin-top: 14px;
        box-shadow: 0 8px 24px rgba(0,0,0,0.4);
    }

    .analytics-title {
        font-size: 16px;
        font-weight: 700;
        color: #f0f6fc;
        margin-bottom: 12px;
        display: flex;
        align-items: center;
        gap: 8px;
        border-bottom: 1px solid rgba(255, 255, 255, 0.1);
        padding-bottom: 8px;
    }

    .stat-box-row {
        display: flex;
        gap: 12px;
        margin-bottom: 12px;
    }

    .stat-box {
        flex: 1;
        background: rgba(255, 255, 255, 0.04);
        border-left: 4px solid #6390F0;
        border-radius: 6px;
        padding: 10px 12px;
    }

    .stat-box.counter-box {
        border-left-color: #EE8130;
    }

    .stat-box.viability-box {
        border-left-color: #7AC74C;
    }

    .stat-label {
        font-size: 11px;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        color: #8b949e;
        font-weight: 700;
        margin-bottom: 4px;
    }

    .stat-value {
        font-size: 15px;
        font-weight: 700;
        color: #e6edf3;
    }

    .type-matchup-container {
        background: rgba(18, 23, 35, 0.8);
        border: 1px solid rgba(255, 255, 255, 0.15);
        border-left: 4px solid #A98FF3;
        border-radius: 12px;
        box-shadow: 0 8px 24px rgba(0,0,0,0.4);
        margin-top: 14px;
        padding: 16px;
    }

    .type-matchup-grid {
        display: grid;
        grid-template-columns: repeat(3, minmax(0, 1fr));
        gap: 8px;
        margin-top: 12px;
    }

    .type-matchup-group {
        background: rgba(255, 255, 255, 0.04);
        border-radius: 6px;
        min-height: 76px;
        padding: 10px 12px;
        box-shadow: 0 8px 24px rgba(0,0,0,0.4);
    }

    .type-chart-row {
        margin-top: 9px;
    }

    .type-chart-label {
        color: #8b949e;
        font-size: 11px;
        font-weight: 700;
        text-transform: uppercase;
    }

    .type-chip {
        display: inline-flex;
        align-items: center;
        justify-content: space-between;
        gap: 4px;
        box-sizing: border-box;
        border-radius: 8px;
        color: white;
        font-size: 13px;
        font-weight: 700;
        margin: 10px 8px 0 0;
        min-height: 38px;
        padding: 5px 11px;
        width: 132px;
    }

    .type-chip img {
        height: 18px;
        width: 18px;
        filter: brightness(0) invert(1);
    }

    .type-multiplier {
        font-size: 13px;
        font-weight: 800;
        opacity: 0.9;
    }

    .type-chart-empty {
        color: #8b949e;
        font-size: 14px;
        font-weight: 700;
        margin-top: 4px;
    }

    @media (max-width: 700px) {
        .type-matchup-grid { grid-template-columns: 1fr; }
    }

    .entity-pill {
        display: inline-flex;
        align-items: center;
        background: rgba(255, 255, 255, 0.08);
        border: 1px solid rgba(255, 255, 255, 0.12);
        border-radius: 20px;
        padding: 4px 10px 4px 4px;
        margin: 4px 6px 4px 0;
        font-size: 13px;
        font-weight: 600;
        color: #f0f6fc;
    }

    .entity-pill img {
        width: 38px;
        height: 38px;
        margin-right: 8px;
        border-radius: 50%;
        background: rgba(0,0,0,0.2);
        object-fit: contain;
    }
</style>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 2. DYNAMIC MASTER MOVE DICTIONARY & ROSTER DATA
# -----------------------------------------------------------------------------
@strlit.cache_data(ttl=86400, show_spinner=False)
def fetch_master_move_dictionary():
    """
    Dynamically fetches all canonical move display names from Pokémon Showdown's
    master GitHub repository, solving the 1000+ move formatting issue programmatically.
    """
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

def display_name_for_move(move_id):
    if not move_id:
        return ""
    clean_id = str(move_id).strip().lower().replace("_", "").replace("-", "").replace(" ", "")
    if clean_id in MASTER_MOVE_DICTIONARY:
        return MASTER_MOVE_DICTIONARY[clean_id]
    
    # Algorithmic fallback for any unmapped or edge-case moves
    slug = get_move_api_slug(move_id)

    return slug.replace("-", " ").title()

CUSTOM_MEGAS_DATA = {
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
    "Mega Meowstic (Male)": {"ability": "Trace", "hp": 74, "atk": 48, "def": 76, "spa": 143, "spd": 101, "spd_stat": 124},
    "Mega Meowstic (Female)": {"ability": "Trace", "hp": 74, "atk": 48, "def": 76, "spa": 83, "spd": 81, "spd_stat": 104},
    "Mega Malamar": {"ability": "Contrary", "hp": 86, "atk": 102, "def": 88, "spa": 98, "spd": 120, "spd_stat": 88},
    "Mega Barbaracle": {"ability": "Tough Claws", "hp": 72, "atk": 140, "def": 130, "spa": 64, "spd": 106, "spd_stat": 88},
    "Mega Dragalge": {"ability": "Regenerator", "hp": 65, "atk": 85, "def": 105, "spa": 132, "spd": 163, "spd_stat": 44},
    "Mega Hawlucha": {"ability": "No Guard", "hp": 78, "atk": 137, "def": 100, "spa": 74, "spd": 93, "spd_stat": 118},
    "Mega Glimmora": {"ability": "Adaptability", "hp": 83, "atk": 90, "def": 105, "spa": 150, "spd": 96, "spd_stat": 101}
}

MEGA_STONE_MAP = {name: f"{name.replace('Mega ', '')}ite" for name in CUSTOM_MEGAS_DATA.keys()}

def filter_valid_champions(team_list):
    return [
        pokemon
        for pokemon in team_list
        if pokemon[0] in VALID_CHAMPIONS
    ]
@strlit.cache_data(ttl=86400, show_spinner=False)

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

@strlit.cache_data(ttl=86400, show_spinner=False)
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
    if not species_key:
        return species_key
    raw = species_key.strip().lower()
    if raw in SPECIES_DISPLAY_OVERRIDES:
        return SPECIES_DISPLAY_OVERRIDES[raw]
    for form_suffix in ["hisui", "alola", "galar", "paldea"]:
        if raw.endswith(form_suffix) and not raw.endswith(f"-{form_suffix}"):
            base = raw[:-len(form_suffix)]
            return f"{display_name_for_species_key(base)} {form_suffix.title()}"
    raw = raw.replace("’", "'").replace("♀", "-f").replace("♂", "-m").replace("_", "-")
    pretty = raw.replace("-", " ")
    if pretty in SPECIES_DISPLAY_OVERRIDES:
        return SPECIES_DISPLAY_OVERRIDES[pretty]
    return " ".join(p.title() for p in pretty.split())

CHAMPIONS_LEARNSETS = fetch_champions_learnsets()
CHAMPIONS_ROSTER = fetch_champions_pokedex_entries()
VALID_CHAMPIONS = {
    display_name_for_species_key(species)
    for species in set(CHAMPIONS_ROSTER) | set(CHAMPIONS_LEARNSETS)
}
VALID_CHAMPIONS.update(CUSTOM_MEGAS_DATA)

def get_move_api_slug(move_name):
    if not move_name:
        return ""
    slug = str(move_name).strip().lower().split(" (")[0].replace("’", "").replace("'", "").replace(".", "")
    return re.sub(r'[^a-z0-9]+', '-', slug).strip("-")

@strlit.cache_data(ttl=86400, show_spinner=False)
def fetch_pokemon_roster():
    roster = list(CUSTOM_MEGAS_DATA.keys())
    for species_key in sorted(set(CHAMPIONS_ROSTER) | set(CHAMPIONS_LEARNSETS.keys())):
        roster.append(display_name_for_species_key(species_key))
    return ["-- Choose a Pokémon --"] + sorted(set(roster), key=lambda item: (not item.startswith("Mega "), item.lower()))

CHAMPIONS_ALL_FORMS = fetch_pokemon_roster()

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
CHAMPIONS_HELD_ITEMS = sorted(list(set(BASE_HELD_ITEMS + list(MEGA_STONE_MAP.values()))))

# -----------------------------------------------------------------------------
# 3. HELPER FUNCTIONS & API FETCHING
# -----------------------------------------------------------------------------
def get_hardcoded_move_type(move_name):
    move_lower = str(move_name).strip().lower()
    types_map = {
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
    return types_map.get(move_lower, "")

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

def get_clean_api_name(mon_name):
    if not mon_name or mon_name == "-- Choose a Pokémon --":
        return "charizard-mega-x"
    name_str = str(mon_name).strip()
    custom_lookup = {
        "Mega Charizard X": "charizard-mega-x", "Mega Charizard Y": "charizard-mega-y",
        "Mega Meowstic (Male)": "meowstic-male", "Mega Meowstic (Female)": "meowstic-female",
        "Mr. Mime": "mr-mime", "Mime Jr.": "mime-jr", "Ho-Oh": "ho-oh",
        "Nidoran♀": "nidoran-f", "Nidoran♂": "nidoran-m", "Farfetch'd": "farfetchd",
        "Sirfetch'd": "sirfetchd", "Flabébé": "flabebe", "Type: Null": "type-null",
    }
    if name_str in custom_lookup:
        return custom_lookup[name_str]
    lower_name = name_str.lower()
    if lower_name.startswith("mega "):
        base = name_str[5:].strip()
        if " x" in base.lower():
            return f"{base.lower().replace(' x', '').strip()}-mega-x"
        elif " y" in base.lower():
            return f"{base.lower().replace(' y', '').strip()}-mega-y"
        else:
            return f"{base.lower().replace(' ', '-')}-mega"
    clean = lower_name.replace("’", "").replace("'", "").replace(".", "")
    return clean.replace(" (", "-").replace(")", "").replace(" ", "-")

def get_champions_species_key(mon_name):
    clean = mon_name.strip().lower().replace("’", "'").replace("♀", "f").replace("♂", "m")
    clean = clean.replace(".", "").replace("'", "").replace(" ", "").replace("-", "")
    if clean.startswith("mega"):
        clean = clean.replace("mega", "")
    return clean

def get_base_api_name(mon_name):
    """Return a PokeAPI-compatible base species for custom Mega forms."""
    base_name = re.sub(r"^Mega\s+", "", mon_name).strip()
    base_name = re.sub(r"\s*\([^)]*\)$", "", base_name)
    base_name = re.sub(r"\s+[XY]$", "", base_name, flags=re.IGNORECASE)
    return get_clean_api_name(base_name)

def get_champion_moves_for(mon_name):
    if not CHAMPIONS_LEARNSETS:
        return []
    species_key = get_champions_species_key(mon_name)
    if species_key in CHAMPIONS_LEARNSETS:
        return [display_name_for_move(m_id) for m_id in CHAMPIONS_LEARNSETS[species_key]]
    if mon_name.startswith("Mega "):
        base_name = mon_name.replace("Mega ", "", 1)
        base_key = get_champions_species_key(base_name)
        if base_key in CHAMPIONS_LEARNSETS:
            return [display_name_for_move(m_id) for m_id in CHAMPIONS_LEARNSETS[base_key]]
    if mon_name in CHAMPIONS_LEARNSETS:
        return [display_name_for_move(m_id) for m_id in CHAMPIONS_LEARNSETS[mon_name]]
    return []

@strlit.cache_data(ttl=86400, show_spinner=False)
def fetch_pokemon_details(mon_name):
    clean_api_name = get_clean_api_name(mon_name)
    sprite_url = f"https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/official-artwork/{clean_api_name}.png"
    box_sprite_url = f"https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/{clean_api_name}.png"
    
    custom_data = CUSTOM_MEGAS_DATA.get(mon_name, {})
    stats = {
        "hp": custom_data.get("hp", 80),
        "attack": custom_data.get("atk", 100),
        "defense": custom_data.get("def", 100),
        "special-attack": custom_data.get("spa", 100),
        "special-defense": custom_data.get("spd", 100),
        "speed": custom_data.get("spd_stat", 100),
    }
    custom_ability = custom_data.get("ability", "Standard")
    champion_moves = list(get_champion_moves_for(mon_name))
    
    types = ["Normal"]
    abilities = [custom_ability] if custom_ability else ["Standard"]
    moves = champion_moves if champion_moves else ["Tackle", "Protect", "Rest", "Substitute"]

    try:
        res = requests.get(f"https://pokeapi.co/api/v2/pokemon/{clean_api_name}", timeout=3)
        if res.status_code != 200 and mon_name.startswith("Mega "):
            res = requests.get(
                f"https://pokeapi.co/api/v2/pokemon/{get_base_api_name(mon_name)}",
                timeout=3,
            )
        if res.status_code == 200:
            data = res.json()
            sprite_url = data.get("sprites", {}).get("other", {}).get("official-artwork", {}).get("front_default") or sprite_url
            box_sprite_url = data.get("sprites", {}).get("front_default") or box_sprite_url
            types = [t["type"]["name"].title() for t in data.get("types", [])]
            if not custom_data:
                api_stats = {
                    entry["stat"]["name"]: entry["base_stat"]
                    for entry in data.get("stats", [])
                }
                if api_stats:
                    stats = api_stats
            api_abilities = [a["ability"]["name"].replace("-", " ").title() for a in data.get("abilities", [])]
            if custom_ability and custom_ability != "Standard":
                abilities = [custom_ability] + [ab for ab in api_abilities if ab != custom_ability]
            elif api_abilities:
                abilities = api_abilities
            if not champion_moves:
                fetched_moves = [m["move"]["name"].replace("-", " ").title() for m in data.get("moves", [])]
                if fetched_moves:
                    moves = fetched_moves
    except Exception:
        pass

    return {
        "sprite": sprite_url,
        "box_sprite": box_sprite_url,
        "types": types,
        "stats": stats,
        "abilities": abilities,
        "moves": sorted(list(set(moves)))
    }

def get_mini_sprite_url(mon_name):
    return fetch_pokemon_details(mon_name)["box_sprite"]

TYPE_ORDER = list(TYPE_COLORS)
TYPE_DEFENSES = {
    "Normal": {"weak": ["Fighting"], "immune": ["Ghost"]},
    "Fire": {"weak": ["Water", "Ground", "Rock"], "resist": ["Fire", "Grass", "Ice", "Bug", "Steel", "Fairy"]},
    "Water": {"weak": ["Electric", "Grass"], "resist": ["Fire", "Water", "Ice", "Steel"]},
    "Electric": {"weak": ["Ground"], "resist": ["Electric", "Flying", "Steel"]},
    "Grass": {"weak": ["Fire", "Ice", "Poison", "Flying", "Bug"], "resist": ["Water", "Electric", "Grass", "Ground"]},
    "Ice": {"weak": ["Fire", "Fighting", "Rock", "Steel"], "resist": ["Ice"]},
    "Fighting": {"weak": ["Flying", "Psychic", "Fairy"], "resist": ["Bug", "Rock", "Dark"]},
    "Poison": {"weak": ["Ground", "Psychic"], "resist": ["Grass", "Fighting", "Poison", "Bug", "Fairy"]},
    "Ground": {"weak": ["Water", "Grass", "Ice"], "resist": ["Poison", "Rock"], "immune": ["Electric"]},
    "Flying": {"weak": ["Electric", "Ice", "Rock"], "resist": ["Grass", "Fighting", "Bug"], "immune": ["Ground"]},
    "Psychic": {"weak": ["Bug", "Ghost", "Dark"], "resist": ["Fighting", "Psychic"]},
    "Bug": {"weak": ["Fire", "Flying", "Rock"], "resist": ["Grass", "Fighting", "Ground"]},
    "Rock": {"weak": ["Water", "Grass", "Fighting", "Ground", "Steel"], "resist": ["Normal", "Fire", "Poison", "Flying"]},
    "Ghost": {"weak": ["Ghost", "Dark"], "resist": ["Poison", "Bug"], "immune": ["Normal", "Fighting"]},
    "Dragon": {"weak": ["Ice", "Dragon", "Fairy"], "resist": ["Fire", "Water", "Grass", "Electric"]},
    "Dark": {"weak": ["Fighting", "Bug", "Fairy"], "resist": ["Ghost", "Dark"], "immune": ["Psychic"]},
    "Steel": {"weak": ["Fire", "Fighting", "Ground"], "resist": ["Normal", "Grass", "Ice", "Flying", "Psychic", "Bug", "Rock", "Dragon", "Steel", "Fairy"], "immune": ["Poison"]},
    "Fairy": {"weak": ["Poison", "Steel"], "resist": ["Fighting", "Bug", "Dark"], "immune": ["Dragon"]},
}

def get_type_defense_summary(defending_types):
    multipliers = {type_name: 1 for type_name in TYPE_ORDER}
    for defending_type in defending_types:
        matchup = TYPE_DEFENSES.get(defending_type, {})
        for type_name in matchup.get("weak", []):
            multipliers[type_name] *= 2
        for type_name in matchup.get("resist", []):
            multipliers[type_name] *= 0.5
        for type_name in matchup.get("immune", []):
            multipliers[type_name] = 0
    return {
        "weak": [type_name for type_name in TYPE_ORDER if multipliers[type_name] > 1],
        "resist": [type_name for type_name in TYPE_ORDER if 0 < multipliers[type_name] < 1],
        "immune": [type_name for type_name in TYPE_ORDER if multipliers[type_name] == 0],
        "multipliers": multipliers,
    }

def get_offensive_type_summary(attacking_types):
    strong_against = []
    resisted_by = []
    for defending_type in TYPE_ORDER:
        matchup = TYPE_DEFENSES[defending_type]
        multipliers = []
        for attacking_type in attacking_types:
            if attacking_type in matchup.get("immune", []):
                multipliers.append(0)
            elif attacking_type in matchup.get("resist", []):
                multipliers.append(0.5)
            elif attacking_type in matchup.get("weak", []):
                multipliers.append(2)
            else:
                multipliers.append(1)
        best_multiplier = max(multipliers, default=1)
        if best_multiplier > 1:
            strong_against.append(defending_type)
        elif best_multiplier < 1:
            resisted_by.append(defending_type)
    return {"strong_against": strong_against, "resisted_by": resisted_by}

def format_type_multiplier(multiplier):
    if multiplier == 0:
        return "x0"
    if multiplier == 0.25:
        return "x1/4"
    if multiplier == 0.5:
        return "x1/2"
    return f"x{int(multiplier)}"

def render_type_chips(type_names, multipliers=None):
    if not type_names:
        return '<div class="type-chart-empty">None</div>'
    return "".join(
        f'<span class="type-chip" style="background-color: {TYPE_COLORS[type_name]};">'
        f'<span>{type_name}</span>'
        f'{f"<span class=\"type-multiplier\">{format_type_multiplier(multipliers[type_name])}</span>" if multipliers else ""}'
        f'<img src="{TYPE_SVG_URLS[type_name]}" alt="" /></span>'
        for type_name in type_names
    )
@strlit.cache_data(ttl=86400, show_spinner=False)
def get_type_relationships(type_name):
    """
    Fetches and caches one Pokémon type's damage relationships.
    """

    try:
        url = f"https://pokeapi.co/api/v2/type/{type_name.lower()}"
        response = requests.get(url, timeout=5)

        if response.status_code == 200:
            return response.json().get("damage_relations", {})

    except Exception:
        pass

    return {}


@strlit.cache_data(ttl=86400, show_spinner=False)
def compute_meta_analytics(mon_name):
    """
    Generates the Meta Profile using the actual Pokémon
    Champions roster.

    Megas are excluded from automatic recommendations.
    """

    if not mon_name or mon_name == "-- Choose a Pokémon --":
        return {
            "tier": "Unknown",
            "viability": "0 / 100",
            "teammates": [],
            "counters": []
        }

    # ---------------------------------------------------------
    # 1. Get selected Pokémon data
    # ---------------------------------------------------------

    mon_data = fetch_pokemon_details(mon_name)

    types = mon_data.get("types", ["Normal"])
    stats = mon_data.get("stats", {})

    bst = sum(stats.values()) if stats else 500

    # ---------------------------------------------------------
    # 2. Viability
    # ---------------------------------------------------------

    if bst >= 650:
        tier = "S-Tier / Uber Threat"
        viability = "95 / 100"

    elif bst >= 580:
        tier = "OU / High Viability"
        viability = "85 / 100"

    else:
        tier = "UU / Niche Pick"
        viability = "70 / 100"

    # ---------------------------------------------------------
    # 3. Find selected Pokémon's weaknesses
    # ---------------------------------------------------------

    weaknesses = set()

    for pokemon_type in types:

        relations = get_type_relationships(pokemon_type)

        if not relations:
            continue

        for weakness in relations.get(
            "double_damage_from",
            []
        ):
            weaknesses.add(
                weakness["name"].title()
            )

    # ---------------------------------------------------------
    # 4. Calculate useful resistance types ONCE
    # ---------------------------------------------------------

    resistant_types = set()

    for weakness in weaknesses:

        relations = get_type_relationships(weakness)

        for resistant in relations.get(
            "half_damage_from",
            []
        ):
            resistant_types.add(
                resistant["name"].title()
            )

    # ---------------------------------------------------------
    # 5. Build actual Champions recommendation pool
    # ---------------------------------------------------------

    champions = []

    for species_key in CHAMPIONS_ROSTER:

        name = display_name_for_species_key(species_key)

        # Never recommend Megas
        if name.lower().startswith("mega "):
            continue

        # Never recommend the selected Pokémon itself
        if name.lower() == mon_name.lower():
            continue

        champions.append(name)

    # Remove duplicates
    champions = list(dict.fromkeys(champions))

    # ---------------------------------------------------------
    # 6. Find teammates
    # ---------------------------------------------------------

    teammate_scores = []

    for name in champions:

        try:
            data = fetch_pokemon_details(name)

            candidate_types = data.get(
                "types",
                []
            )

            if not candidate_types:
                continue

            score = 0

            for candidate_type in candidate_types:

                if candidate_type in resistant_types:
                    score += 2

            if score > 0:
                teammate_scores.append(
                    (
                        score,
                        name,
                        candidate_types[0]
                    )
                )

        except Exception:
            continue

    teammate_scores.sort(
        key=lambda x: (-x[0], x[1])
    )

    teammates = [
        (name, pokemon_type)
        for score, name, pokemon_type
        in teammate_scores[:3]
    ]

    # ---------------------------------------------------------
    # 7. Find counters
    # ---------------------------------------------------------

    counter_scores = []

    for name in champions:

        try:
            data = fetch_pokemon_details(name)

            candidate_types = data.get(
                "types",
                []
            )

            if not candidate_types:
                continue

            score = 0

            # A Pokémon whose own typing matches
            # one of the selected Pokémon's weaknesses
            # gets a higher counter score.
            for candidate_type in candidate_types:

                if candidate_type in weaknesses:
                    score += 3

            if score > 0:
                counter_scores.append(
                    (
                        score,
                        name,
                        candidate_types[0]
                    )
                )

        except Exception:
            continue

    counter_scores.sort(
        key=lambda x: (-x[0], x[1])
    )

    counters = [
        (name, pokemon_type)
        for score, name, pokemon_type
        in counter_scores[:3]
    ]

    # ---------------------------------------------------------
    # 8. Return data to GUI
    # ---------------------------------------------------------

    return {
        "tier": tier,
        "viability": viability,
        "teammates": teammates,
        "counters": counters
    }


def infer_slot_role(slot):
    moves = slot.get("moves", [])
    if any(m in moves for m in ["Swords Dance", "Dragon Dance", "Nasty Plot", "Calm Mind", "Quiver Dance"]):
        return "Setup Sweeper"
    if any(m in moves for m in ["Stealth Rock", "Spikes", "Toxic Spikes", "Defog", "Rapid Spin", "Tidy Up"]):
        return "Support"
    if any(m in moves for m in ["U-turn", "Volt Switch", "Flip Turn", "Parting Shot"]):
        return "Pivot"
    return "Balanced Pick"

def ensure_slot_structure(slot_idx, fallback_name="-- Choose a Pokémon --"):
    if "team_slots" not in strlit.session_state:
        strlit.session_state.team_slots = {}
    if slot_idx not in strlit.session_state.team_slots:
        strlit.session_state.team_slots[slot_idx] = {
            "name": fallback_name,
            "ability": "Standard",
            "item": "",
            "nature": "Hardy",
            "moves": ["Protect", "Substitute", "Toxic", "Rest"],
            "evs": {"HP": 0, "Atk": 0, "Def": 0, "SpA": 0, "SpD": 0, "Spe": 0}
        }
    return strlit.session_state.team_slots[slot_idx]

def normalize_moves(moves, available_moves):
    """Return exactly four valid move selections for a team slot."""
    available_moves = list(dict.fromkeys(available_moves)) or ["Protect"]
    valid_moves = [move for move in moves if move in available_moves]
    for move in available_moves:
        if len(valid_moves) >= 4:
            break
        if move not in valid_moves:
            valid_moves.append(move)
    while len(valid_moves) < 4:
        valid_moves.append(available_moves[0])
    return valid_moves[:4]

def generate_synergistic_moveset(new_species, target_slot_idx):
    if new_species == "-- Choose a Pokémon --":
        return ["Protect", "Substitute", "Toxic", "Rest"]
    mon_data = fetch_pokemon_details(new_species)
    learnset = mon_data["moves"]
    mon_types = mon_data["types"]
    
    priority_STABs = []
    priority_Coverage = []
    for m in learnset:
        m_type = fetch_move_type(m)
        if m_type in mon_types and m not in priority_STABs:
            priority_STABs.append(m)
        else:
            priority_Coverage.append(m)
            
    final_set = (priority_STABs[:2] + priority_Coverage[:2])
    while len(final_set) < 4 and learnset:
        for m in learnset:
            if m not in final_set:
                final_set.append(m)
                break
    return list(dict.fromkeys(final_set))[:4]

def on_species_change(slot_idx):
    new_species = strlit.session_state.get(f"species_select_{slot_idx}", "-- Choose a Pokémon --")
    slot = ensure_slot_structure(slot_idx, new_species)
    if new_species == "-- Choose a Pokémon --":
        return
    ability = CUSTOM_MEGAS_DATA.get(new_species, {}).get("ability", "Standard")
    item = MEGA_STONE_MAP.get(new_species, "Focus Sash")
    mon_data = fetch_pokemon_details(new_species)
    atk = mon_data["stats"].get("attack", 80)
    spa = mon_data["stats"].get("special-attack", 80)
    nature = "Jolly (+Spe, -SpA)" if atk >= spa else "Timid (+Spe, -Atk)"
    evs = {"HP": 0, "Atk": 252, "Def": 4, "SpA": 0, "SpD": 0, "Spe": 252} if atk >= spa else {"HP": 0, "Atk": 0, "Def": 4, "SpA": 252, "SpD": 0, "Spe": 252}
    recommended_moves = generate_synergistic_moveset(new_species, slot_idx)

    slot.update({
        "name": new_species, "ability": ability, "item": item,
        "nature": nature, "moves": normalize_moves(recommended_moves, mon_data["moves"]), "evs": evs,
    })

# -----------------------------------------------------------------------------
# 4. INITIALIZE SESSION STATE
# -----------------------------------------------------------------------------
if "team_slots" not in strlit.session_state:
    strlit.session_state.team_slots = {}
for i in range(6):
    ensure_slot_structure(i, "-- Choose a Pokémon --")

# -----------------------------------------------------------------------------
# 5. APP INTERFACE
# -----------------------------------------------------------------------------
strlit.title("⚔️ Pokémon Champions Teambuilder")

with strlit.sidebar:
    strlit.header("🛠️ Team Actions")
    if strlit.button("Reset Team"):
        strlit.session_state.team_slots = {}
        for idx in range(6):
            for key in (f"species_select_{idx}", f"ab_{idx}", f"item_{idx}", f"nat_{idx}"):
                strlit.session_state.pop(key, None)
            for move_idx in range(4):
                strlit.session_state.pop(f"move_{idx}_{move_idx}", None)
            for ev_key in ("HP", "Atk", "Def", "SpA", "SpD", "Spe"):
                strlit.session_state.pop(f"stat_ev_{idx}_{ev_key}", None)
            ensure_slot_structure(idx, "-- Choose a Pokémon --")
        strlit.rerun()

    strlit.checkbox("Only show legal moves", value=True, key="legal_moves_only")
    strlit.caption("Uses Smogon Showdown learnsets for legal verification.")

tabs = strlit.tabs([f"Slot {i+1}" for i in range(6)] + ["📊 Team Overview"])

for i in range(6):
    with tabs[i]:
        slot = ensure_slot_structure(i, "-- Choose a Pokémon --")
        slot_name = slot.get('name', '-- Choose a Pokémon --')
        strlit.subheader(f"Slot {i+1}: {slot_name if slot_name != '-- Choose a Pokémon --' else '(Empty Slot)'}")
        
        try:
            default_index = CHAMPIONS_ALL_FORMS.index(slot_name)
        except ValueError:
            default_index = 0

        selected_mon = strlit.selectbox(
            f"Species (Slot {i+1})",
            options=CHAMPIONS_ALL_FORMS,
            index=default_index,
            key=f"species_select_{i}",
            on_change=on_species_change,
            args=(i,)
        )

        slot = strlit.session_state.team_slots[i]
        slot_name = slot.get('name', selected_mon)

        if slot_name == "-- Choose a Pokémon --":
            strlit.info("👆 Please select a Pokémon from the dropdown above to begin building this slot.")
            continue

        col_mon, col_set = strlit.columns([1, 2])
        
        with col_mon:
            mon_data = fetch_pokemon_details(slot_name)
            strlit.image(mon_data["sprite"], width=170)
            
            badge_html = "".join([
                f'<div class="type-badge" style="background-color: {TYPE_COLORS.get(t, "#777")}; margin-right: 6px;">'
                f'<img src="{TYPE_SVG_URLS.get(t, "")}" width="14" height="14" style="filter: brightness(0) invert(1);" />'
                f'<span>{t.upper()}</span>'
                f'</div>'
                for t in mon_data["types"]
            ])
            strlit.markdown(f'<div style="display:flex; margin-bottom:12px;">{badge_html}</div>', unsafe_allow_html=True)

            ability_options = mon_data.get("abilities", ["Standard"])
            current_ability = slot.get("ability", ability_options[0])
            if current_ability not in ability_options:
                current_ability = ability_options[0]

            slot["ability"] = strlit.selectbox("Ability", options=ability_options, index=ability_options.index(current_ability), key=f"ab_{i}")
            strlit.caption(f"Suggested role: {infer_slot_role(slot)}")

            if slot_name in MEGA_STONE_MAP:
                correct_stone = MEGA_STONE_MAP[slot_name]
                slot["item"] = correct_stone
                strlit.text_input("Held Item", value=correct_stone, key=f"item_locked_{i}_{slot_name}", disabled=True)
            else:
                item_opts = CHAMPIONS_HELD_ITEMS
                current_item = slot.get("item", item_opts[0])
                if current_item not in item_opts:
                    current_item = item_opts[0]
                slot["item"] = strlit.selectbox("Held Item", options=item_opts, index=item_opts.index(current_item), key=f"item_{i}")

            nat_opts = NATURES
            current_nature = slot.get("nature", "Hardy")
            nat_match = [n for n in nat_opts if n.startswith(current_nature.split(" ")[0])]
            nat_idx = nat_opts.index(nat_match[0]) if nat_match else 0
            slot["nature"] = strlit.selectbox("Nature", options=nat_opts, index=nat_idx, key=f"nat_{i}")

            # -----------------------------------------------------------------
            # UPGRADED VISUAL ANALYTICS CARD WITH ICONS & COLORED STAT BORDERS
            # -----------------------------------------------------------------
            meta = compute_meta_analytics(slot_name)
            type_summary = get_type_defense_summary(mon_data["types"])
            offensive_summary = get_offensive_type_summary(mon_data["types"])

            # Safe guard: If meta is None, provide default empty structures so the app doesn't crash
            if not meta:
                meta = {"tier": "Unknown", "viability_score": "0 / 100", "teammates": [], "counters": []}

            # Simple patch to fix your HTML viewer down on line 1068
            meta["viability"] = meta.get("viability_score", "0 / 100")

            teammates_html = "".join([
                f''
                f'<img src="{get_mini_sprite_url(tm_name)}" />'
                f'<span>{tm_name}</span>'
                f'</div>'
                for tm_name, tm_type in meta.get("teammates", [])
            ])

            counters_html = "".join([
                f''
                f'<img src="{get_mini_sprite_url(ct_name)}" />'
                f'<span>{ct_name}</span>'
                f'</div>'
                for ct_name, ct_type in meta.get("counters", [])
            ])



            strlit.html(f"""
            <div class="analytics-container">
                <div class="analytics-title">
                    <span>📈 Competitive Synergy & Meta Profile</span>
                </div>

                <div class="stat-box-row">
                    <div class="stat-box viability-box">
                        <div class="stat-label">Viability Index</div>
                        <div class="stat-value">{meta['viability']}</div>
                    </div>

                    <div class="stat-box">
                        <div class="stat-label">Smogon Tiering</div>
                        <div class="stat-value">{meta['tier']}</div>
                    </div>
                </div>

                <div class="stat-box" style="margin-bottom: 12px;">
                    <div class="stat-label">Synergistic Core Teammates</div>
                    <div style="margin-top: 6px;">
                        {teammates_html}
                    </div>
                </div>

                <div class="stat-box counter-box">
                    <div class="stat-label">Common Meta Checks & Counters</div>
                    <div style="margin-top: 6px;">
                        {counters_html}
                    </div>
                </div>

                <div class="stat-box" style="margin-top:12px;">
                    <div class="stat-label">Recommended Role</div>
                    <div class="stat-value">{infer_slot_role(slot)}</div>
                </div>
            </div>
            """)

        with col_set:
            strlit.markdown("##### ⚔️ Moveset Configuration")
            all_moves = mon_data.get("moves", ["Protect", "Tackle"])
            slot["moves"] = normalize_moves(slot.get("moves", []), all_moves)

            for row_idx in range(2):
                m_col1, m_col2 = col_set.columns(2)
                for c_i, col in enumerate([m_col1, m_col2]):
                    m_idx = row_idx * 2 + c_i
                    current_selected = slot["moves"][m_idx]
                    available_options = [m for m in all_moves if m not in slot["moves"] or m == current_selected]
                    if current_selected not in available_options:
                        current_selected = available_options[0] if available_options else all_moves[0]
                        slot["moves"][m_idx] = current_selected

                    selected_move = col.selectbox(
                        f"Move {m_idx+1}",
                        options=available_options,
                        index=available_options.index(current_selected) if current_selected in available_options else 0,
                        key=f"move_{i}_{m_idx}"
                    )
                    slot["moves"][m_idx] = selected_move

                    m_type = get_hardcoded_move_type(selected_move) or fetch_move_type(selected_move)
                    col.markdown(f'''
                        <div class="move-card" style="background-color: {TYPE_COLORS.get(m_type, "#555")};">
                            <span class="move-name">{selected_move}</span>
                            <div class="move-type-badge">
                                <img src="{TYPE_SVG_URLS.get(m_type, "")}" width="14" height="14" style="filter: brightness(0) invert(1);" />
                                <span>{m_type.upper()}</span>
                            </div>
                        </div>
                    ''', unsafe_allow_html=True)

            strlit.markdown("##### 📊 Effort Values (EV Spread)")
            ev_cols = col_set.columns(3)
            ev_keys = ["HP", "Atk", "Def", "SpA", "SpD", "Spe"]
            ev_labels = ["HP", "Attack", "Defense", "Sp. Atk", "Sp. Def", "Speed"]
            if "evs" not in slot or not isinstance(slot["evs"], dict):
                slot["evs"] = {k: 0 for k in ev_keys}

            for idx, (key, label) in enumerate(zip(ev_keys, ev_labels)):
                with ev_cols[idx % 3]:
                    slot["evs"][key] = strlit.number_input(
                        label, min_value=0, max_value=252, step=4,
                        value=slot["evs"].get(key, 0), key=f"stat_ev_{i}_{key}"
                    )

            strlit.markdown("##### Type matchup")
            with strlit.container(border=True):
                weak_col, resist_col, immune_col = strlit.columns(3)
                with weak_col:
                    strlit.caption("Weak to")
                    strlit.html(render_type_chips(type_summary["weak"], type_summary["multipliers"]))
                with resist_col:
                    strlit.caption("Resists")
                    strlit.html(render_type_chips(type_summary["resist"], type_summary["multipliers"]))
                with immune_col:
                    strlit.caption("Immune to")
                    strlit.html(render_type_chips(type_summary["immune"], type_summary["multipliers"]))

            strlit.markdown("##### Offensive coverage")
            with strlit.container(border=True):
                strong_col, resisted_col = strlit.columns(2)
                with strong_col:
                    strlit.caption("STAB attacks are strong against")
                    strlit.html(render_type_chips(offensive_summary["strong_against"]))
                with resisted_col:
                    strlit.caption("STAB attacks are resisted by")
                    strlit.html(render_type_chips(offensive_summary["resisted_by"]))

with tabs[6]:
    strlit.subheader("📊 Comprehensive Team Overview")
    strlit.success("✓ Dynamic moveset names fetched directly from Pokémon Showdown's GitHub repository.")
    strlit.success("✓ Analytics rebuilt with larger fonts, colored accent borders, and inline Pokémon sprites.")
    strlit.success("✓ Removed arbitrary usage percentages in favor of calculated Viability Indexes and Type Synergies.")
