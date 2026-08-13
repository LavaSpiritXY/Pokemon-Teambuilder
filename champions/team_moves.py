from typing import Callable, Dict, List


def normalize_moves(moves, available_moves):
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


def generate_synergistic_moveset(
    new_species: str,
    target_slot_idx: int,
    fetch_pokemon_details: Callable[[str], Dict],
    get_smogon_stats_for: Callable[[str], Dict],
    fetch_move_type: Callable[[str], str],
) -> List[str]:
    """Build a simple four-move recommendation using available meta signals."""
    if new_species == "-- Choose a Pokémon --":
        return ["Protect", "Substitute", "Toxic", "Rest"]

    mon_data = fetch_pokemon_details(new_species)
    learnset = mon_data["moves"]
    mon_types = mon_data["types"]

    smogon_stats = get_smogon_stats_for(new_species)
    smogon_moves = smogon_stats.get("common_moves", {})
    if smogon_moves:
        sorted_by_usage = sorted(
            [m for m in learnset if m in smogon_moves],
            key=lambda x: smogon_moves.get(x, 0.0),
            reverse=True,
        )
        if len(sorted_by_usage) >= 4:
            return sorted_by_usage[:4]

    priority_stabs = []
    priority_coverage = []
    for move in learnset:
        move_type = fetch_move_type(move)
        if move_type in mon_types and move not in priority_stabs:
            priority_stabs.append(move)
        else:
            priority_coverage.append(move)

    final_set = priority_stabs[:2] + priority_coverage[:2]
    while len(final_set) < 4 and learnset:
        for move in learnset:
            if move not in final_set:
                final_set.append(move)
                break

    return list(dict.fromkeys(final_set))[:4]
