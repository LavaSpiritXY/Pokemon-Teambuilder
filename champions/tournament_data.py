from champions.constants import CURRENT_REGULATION
from champions.history_data import (
    build_legacy_meta_db,
    get_history_metrics,
    get_history_partners,
)
from champions.move_data import get_champions_species_key
from champions.roster_data import display_name_for_species_key


# Legacy compatibility database. New consumers should use the clean history
# API below instead of reading this structure directly.
CHAMPIONS_META_DB = build_legacy_meta_db()


def _extract_match_record(player):
    """Return explicit wins/losses supplied by a tournament record."""
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
    """Import one Champions tournament into the legacy compatibility DB."""
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
    """Return normalized Champions history metrics for one Pokémon."""
    history_metrics = get_history_metrics(
        pokemon_name,
        current_regulation=CURRENT_REGULATION,
    )

    if not history_metrics:
        return {
            "usage": 0.0,
            "top_cut_rate": 0.0,
            "win_rate": None,
            "tournament_score": 0.0,
            "partner_score": 0.0,
            "win_rate_available": False,
            "current_regulation": CURRENT_REGULATION,
            "current_regulation_appearances": None,
            "overall": None,
            "recent": None,
            "current": None,
        }

    overall = history_metrics["overall"]
    recent = history_metrics["recent"]
    current = history_metrics["current"]

    appearances = max(1, overall.get("appearances", 0))
    top_cut_rate = max(
        0.0,
        min(1.0, float(overall.get("top_cut_rate", 0.0) or 0.0)),
    )
    win_rate = overall.get("win_rate")
    win_rate_available = win_rate is not None
    if win_rate_available:
        win_rate = max(0.0, min(1.0, float(win_rate)))

    partner_values = [
        int(partner.get("teams_together", 0) or 0)
        for partner in get_history_partners(pokemon_name, top_n=10)
    ]
    partner_values = [value for value in partner_values if value > 0]
    partner_score = (
        min(1.0, sum(partner_values) / max(1, appearances * 5))
        if partner_values else 0.0
    )

    # Recent usage is exposed as a normalized signal for existing callers.
    recent_usage_score = min(
        1.0,
        max(0.0, float(recent.get("usage_weight", 0.0) or 0.0)) / 200.0,
    )

    components = [
        (recent_usage_score, 0.20),
        (top_cut_rate, 0.35),
        (partner_score, 0.10),
    ]
    if win_rate_available:
        components.append((win_rate, 0.35))

    total_weight = sum(weight for _, weight in components)
    tournament_score = (
        sum(score * weight for score, weight in components) / total_weight
        if total_weight else 0.0
    )

    return {
        "usage": recent_usage_score,
        "top_cut_rate": top_cut_rate,
        "win_rate": win_rate,
        "tournament_score": tournament_score,
        "partner_score": partner_score,
        "win_rate_available": win_rate_available,
        "current_regulation": current.get("regulation") or CURRENT_REGULATION,
        "current_regulation_appearances": current.get("appearances"),
        "current_regulation_win_rate": current.get("win_rate"),
        "current_regulation_top_cut_rate": current.get("top_cut_rate"),
        "current_regulation_win_rate_available": current.get("win_rate_available", False),
        "current_regulation_top_cut_rate_available": current.get("top_cut_rate_available", False),
        "overall": overall,
        "recent": recent,
        "current": current,
    }


def get_tournament_partners(pokemon_name, top_n=10):
    """Return strongest historical tournament partners for a Pokémon."""
    results = []

    for partner in get_history_partners(pokemon_name, top_n=top_n):
        partner_key = str(partner.get("pokemon", "")).strip().lower()
        if not partner_key:
            continue

        display_name = display_name_for_species_key(partner_key)
        if not display_name:
            continue

        if display_name.lower().startswith("mega "):
            continue

        results.append(
            (partner_key, int(partner.get("teams_together", 0) or 0))
        )
        if len(results) >= top_n:
            break

    return results
