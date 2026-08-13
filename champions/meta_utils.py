from champions.constants import ARCHETYPE_DEFINITIONS
from champions.move_data import fetch_move_type, get_hardcoded_move_type


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
