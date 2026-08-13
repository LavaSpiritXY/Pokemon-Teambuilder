from champions.constants import CURRENT_REGULATION
from champions.move_data import get_champions_species_key
from champions.roster_data import display_name_for_species_key


CHAMPIONS_META_DB = {}


def _extract_match_record(player):
    """Return explicit wins/losses supplied by a tournament record.

    The importer never infers wins from placement.  A placing is not a game
    record, so fabricated win/loss values would distort viability scoring.
    Supported shapes are ``wins``/``losses`` directly on the player or inside
    a ``record`` mapping.
    """
    record = player.get("record")
    if not isinstance(record, dict):
        record = {}

    wins = player.get("wins", record.get("wins", 0))
    losses = player.get("losses", record.get("losses", 0))

    try:
        wins = max(0, int(wins or 0))
    except (TypeError, ValueError):
        wins = 0

    try:
        losses = max(0, int(losses or 0))
    except (TypeError, ValueError):
        losses = 0

    return wins, losses


def import_champions_tournament(event):
    """
    Import one Champions tournament into CHAMPIONS_META_DB.

    The event must contain:
        {
            "regulation": "...",
            "players": [
                {
                    "team": [...],
                    "placing": 1,
                    "wins": 5,
                    "losses": 1
                }
            ]
        }

    ``wins`` and ``losses`` are optional.  When they are absent, the importer
    keeps the match record unknown rather than pretending it was 0-0.
    """

    regulation = event.get("regulation", "")

    if (
        regulation
        and CURRENT_REGULATION
        and regulation != CURRENT_REGULATION
    ):
        return

    for player in event.get("players", []):
        team = player.get("team", [])
        placing = player.get("placing")
        wins, losses = _extract_match_record(player)

        canonical_team = [
            get_champions_species_key(pokemon)
            for pokemon in team
            if pokemon
        ]
        canonical_team = list(dict.fromkeys(canonical_team))

        for pokemon in canonical_team:
            if pokemon not in CHAMPIONS_META_DB:
                CHAMPIONS_META_DB[pokemon] = {
                    "appearances": 0,
                    "wins": 0,
                    "losses": 0,
                    "match_records": 0,
                    "top_cuts": 0,
                    "usage": 0.0,
                    "win_rate": None,
                    "top_cut_rate": 0.0,
                    "partners": {},
                    "roles": {},
                    "moves": {},
                    "abilities": {},
                    "items": {},
                }

            record = CHAMPIONS_META_DB[pokemon]
            record["appearances"] += 1

            if wins + losses > 0:
                record["wins"] += wins
                record["losses"] += losses
                record["match_records"] += 1

            if placing is not None and placing <= 8:
                record["top_cuts"] += 1

            for partner in canonical_team:
                if partner == pokemon:
                    continue

                record["partners"][partner] = (
                    record["partners"].get(partner, 0) + 1
                )


def calculate_tournament_metrics(pokemon_name):
    """Convert raw Champions tournament data into normalized metrics."""
    key = get_champions_species_key(pokemon_name)
    record = CHAMPIONS_META_DB.get(key)

    if not record:
        return {
            "usage": 0.0,
            "top_cut_rate": 0.0,
            "win_rate": None,
            "tournament_score": 0.0,
            "partner_score": 0.0,
            "win_rate_available": False,
        }

    appearances = max(1, record.get("appearances", 0))
    wins = max(0, record.get("wins", 0))
    losses = max(0, record.get("losses", 0))
    top_cuts = max(0, record.get("top_cuts", 0))

    total_games = wins + losses
    win_rate_available = total_games > 0
    win_rate = wins / total_games if win_rate_available else None

    top_cut_rate = top_cuts / appearances

    partner_values = list(record.get("partners", {}).values())
    if partner_values:
        partner_score = min(
            1.0,
            sum(partner_values) / max(1, appearances * 5),
        )
    else:
        partner_score = 0.0

    usage_score = min(1.0, appearances / 200.0)

    # Do not penalize an imported record merely because the source did not
    # contain match results.  Redistribute the unused win-rate weight across
    # the other tournament signals.
    components = [
        (usage_score, 0.30),
        (top_cut_rate, 0.35),
        (partner_score, 0.10),
    ]

    if win_rate_available:
        components.append((win_rate, 0.25))

    total_weight = sum(weight for _, weight in components)
    tournament_score = (
        sum(score * weight for score, weight in components) / total_weight
    )

    return {
        "usage": usage_score,
        "top_cut_rate": top_cut_rate,
        "win_rate": win_rate,
        "tournament_score": tournament_score,
        "partner_score": partner_score,
        "win_rate_available": win_rate_available,
    }


def get_tournament_partners(pokemon_name, top_n=10):
    """Return the strongest tournament partners for a Pokémon."""
    key = get_champions_species_key(pokemon_name)
    record = CHAMPIONS_META_DB.get(key)

    if not record:
        return []

    partners = record.get("partners", {})
    ranked = sorted(
        partners.items(),
        key=lambda item: item[1],
        reverse=True,
    )

    results = []

    for partner_key, frequency in ranked:
        display_name = display_name_for_species_key(partner_key)

        if not display_name:
            continue

        if display_name.lower().startswith("mega "):
            continue

        results.append((partner_key, frequency))

        if len(results) >= top_n:
            break

    return results
