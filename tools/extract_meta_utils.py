from pathlib import Path

APP = Path("app.py")
MODULE = Path("champions/meta_utils.py")

IMPORT_BLOCK = '''from champions.meta_utils import (
    get_hardcoded_move_type,
    fetch_move_type,
    detect_archetypes,
)
'''

MODULE_CONTENT = '''from champions.constants import ARCHETYPE_DEFINITIONS


def get_hardcoded_move_type(move_name):
    move_map = {
        "Tailwind": "Flying", "Trick Room": "Psychic", "Rain Dance": "Water",
        "Sunny Day": "Fire", "Protect": "Normal", "Surf": "Water", "Eruption": "Fire"
    }
    return move_map.get(move_name, "Normal")


def fetch_move_type(move_name):
    return get_hardcoded_move_type(move_name)


def detect_archetypes(pkmn_data):
    """
    Scans a Pokémon's ability pool and relevant moveset to identify functional archetypes.
    Uses OR logic so anchors like Pelipper (Drizzle) are detected correctly.
    """
    matched_archetypes = []
    abilities = [str(a).lower() for a in pkmn_data.get("abilities", [])]
    moves = [str(m).lower() for m in pkmn_data.get("moves", [])]

    for arch_name, criteria in ARCHETYPE_DEFINITIONS.items():
        req_abs = [str(a).lower() for a in criteria.get("abilities", [])]
        req_moves = [str(m).lower() for m in criteria.get("moves", [])]

        has_ability = any(ab in abilities for ab in req_abs) if req_abs else False
        has_move = any(mv in moves for mv in req_moves) if req_moves else False

        if has_ability or has_move:
            matched_archetypes.append({
                "name": arch_name,
                "role_label": criteria.get("role_label", "Balanced Pick"),
                "boost": criteria.get("boost", 20)
            })

    return matched_archetypes
'''


def main():
    text = APP.read_text(encoding="utf-8")

    if "from champions.meta_utils import (" not in text:
        anchor = "from champions.constants import ("
        end = text.index(")\n", text.index(anchor)) + 2
        text = text[:end] + "\n" + IMPORT_BLOCK + text[end:]

    start_token = "def get_hardcoded_move_type(move_name):"
    end_token = "# ==========================================\n# 2. META-INDEX AWARE VIABILITY & TIERING"

    if start_token in text:
        start = text.index(start_token)
        end = text.index(end_token, start)
        text = text[:start] + text[end:]
    elif "from champions.meta_utils import (" not in text:
        raise SystemExit("Meta utility block was not found; refusing to modify app.py.")

    MODULE.write_text(MODULE_CONTENT.rstrip() + "\n", encoding="utf-8")
    APP.write_text(text, encoding="utf-8")
    print("Extracted move/archetype utilities into champions/meta_utils.py")


if __name__ == "__main__":
    main()
