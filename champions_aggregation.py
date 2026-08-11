"""
Pokémon Champions tournament aggregation layer.

PHASE 6
-------
This module sits on top of champions_data.py and turns normalized tournament
records into Pokémon-level competitive statistics.

It does NOT modify app.py or CHAMPIONS_META_DB yet.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import asdict
from typing import Any, Dict, Iterable, List, Optional

from champions_data import (
    ChampionsEvent,
    ChampionsResult,
    ChampionsTeam,
    champions_species_key,
)


# ============================================================================
# 1. BASIC HELPERS
# ============================================================================


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _normalise_placement(value: Any) -> Optional[int]:
    value = _safe_int(value, 0)
    return value if value > 0 else None


def _calculate_top_cut_size(event: ChampionsEvent, results: List[ChampionsResult]) -> int:
    """Determine a conservative cut size from normalized event information.

    Phase 6 deliberately prefers explicit event metadata when available.
    If the current source payload does not expose a cut size yet, we use the
    actual observed elimination placements rather than assuming Top 8.
    """

    # Future-proof hook: if a later parser attaches a cut_size attribute to
    # ChampionsEvent, use it without changing the aggregation code.
    explicit = getattr(event, "cut_size", None)
    if explicit:
        return max(1, _safe_int(explicit))

    placements = sorted(
        p.placement for p in results
        if p.placement is not None and p.placement > 0
    )

    if not placements:
        return 0

    # We cannot safely infer an exact cut from final placement alone when a
    # source does not expose tournament phases. Return zero rather than invent
    # a Top-8 rule. This means top_cut is only trusted when the source supplied
    # it or a later phase-aware parser sets cut_size.
    return 0


# ============================================================================
# 2. EVENT-LEVEL NORMALIZATION
# ============================================================================


def finalize_event_results(
    event: ChampionsEvent,
    results: Iterable[ChampionsResult],
) -> List[ChampionsResult]:
    """Return clean results and apply only evidence-backed top-cut data."""

    cleaned: List[ChampionsResult] = []
    for result in results:
        if not result.player_name:
            continue

        result.event_id = str(event.event_id)
        result.placement = _normalise_placement(result.placement)
        result.wins = max(0, _safe_int(result.wins))
        result.losses = max(0, _safe_int(result.losses))
        result.draws = max(0, _safe_int(result.draws))
        cleaned.append(result)

    # Do not manufacture a cut size. If the upstream result already says a
    # player reached the cut, preserve it; otherwise leave it False until the
    # event-phase parser supplies the exact elimination size.
    _calculate_top_cut_size(event, cleaned)
    return cleaned


# ============================================================================
# 3. POKÉMON-LEVEL AGGREGATION
# ============================================================================


def aggregate_pokemon_statistics(
    event: ChampionsEvent,
    results: Iterable[ChampionsResult],
    teams: Iterable[ChampionsTeam],
) -> Dict[str, Dict[str, Any]]:
    """Aggregate one tournament into Pokémon-level statistics.

    A Pokémon receives the player's tournament W/L record when that Pokémon
    appears on the player's submitted team. Partner counts are calculated
    from the same six-Pokémon team and are therefore team-based, not matchup-
    based.
    """

    clean_results = finalize_event_results(event, results)
    result_by_player: Dict[str, ChampionsResult] = {
        result.player_name.casefold(): result for result in clean_results
    }

    records: Dict[str, Dict[str, Any]] = {}

    for team in teams:
        player_key = team.player_name.casefold()
        result = result_by_player.get(player_key)
        if result is None:
            continue

        pokemon_keys: List[str] = []
        display_names: Dict[str, str] = {}

        for pokemon in team.pokemon:
            key = champions_species_key(pokemon)
            if not key or key in pokemon_keys:
                continue
            pokemon_keys.append(key)
            display_names[key] = pokemon

        for pokemon_key in pokemon_keys:
            record = records.setdefault(
                pokemon_key,
                {
                    "name": display_names[pokemon_key],
                    "events": set(),
                    "appearances": 0,
                    "wins": 0,
                    "losses": 0,
                    "draws": 0,
                    "top_cuts": 0,
                    "placements": [],
                    "partners": defaultdict(int),
                    "players": set(),
                },
            )

            record["events"].add(event.event_id)
            record["appearances"] += 1
            record["wins"] += result.wins
            record["losses"] += result.losses
            record["draws"] += result.draws
            record["players"].add(team.player_name)

            if result.top_cut:
                record["top_cuts"] += 1

            if result.placement is not None:
                record["placements"].append(result.placement)

            for partner_key in pokemon_keys:
                if partner_key != pokemon_key:
                    record["partners"][partner_key] += 1

    # Convert internal sets/defaultdicts into JSON-friendly plain structures.
    output: Dict[str, Dict[str, Any]] = {}
    for key, record in records.items():
        games = record["wins"] + record["losses"] + record["draws"]
        appearances = record["appearances"]
        placements = record["placements"]

        output[key] = {
            "name": record["name"],
            "events": sorted(record["events"]),
            "appearances": appearances,
            "wins": record["wins"],
            "losses": record["losses"],
            "draws": record["draws"],
            "top_cuts": record["top_cuts"],
            "placements": placements,
            "best_placement": min(placements) if placements else None,
            "average_placement": (
                sum(placements) / len(placements) if placements else None
            ),
            "usage_rate": 0.0,
            "win_rate": (
                record["wins"] / games if games else 0.0
            ),
            "top_cut_rate": (
                record["top_cuts"] / appearances if appearances else 0.0
            ),
            "players": sorted(record["players"]),
            "partners": dict(
                sorted(
                    record["partners"].items(),
                    key=lambda item: (-item[1], item[0]),
                )
            ),
        }

    return output


# ============================================================================
# 4. EVENT-TO-GLOBAL AGGREGATION
# ============================================================================


def merge_pokemon_statistics(
    destination: Dict[str, Dict[str, Any]],
    source: Dict[str, Dict[str, Any]],
) -> Dict[str, Dict[str, Any]]:
    """Merge one event's Pokémon statistics into a global database."""

    for key, incoming in source.items():
        target = destination.setdefault(
            key,
            {
                "name": incoming["name"],
                "events": [],
                "appearances": 0,
                "wins": 0,
                "losses": 0,
                "draws": 0,
                "top_cuts": 0,
                "placements": [],
                "best_placement": None,
                "average_placement": None,
                "usage_rate": 0.0,
                "win_rate": 0.0,
                "top_cut_rate": 0.0,
                "players": [],
                "partners": {},
            },
        )

        target["events"] = sorted(
            set(target["events"]) | set(incoming["events"])
        )
        target["appearances"] += incoming["appearances"]
        target["wins"] += incoming["wins"]
        target["losses"] += incoming["losses"]
        target["draws"] += incoming["draws"]
        target["top_cuts"] += incoming["top_cuts"]
        target["placements"].extend(incoming["placements"])
        target["players"] = sorted(
            set(target["players"]) | set(incoming["players"])
        )

        partner_counts = defaultdict(int, target["partners"])
        for partner, count in incoming["partners"].items():
            partner_counts[partner] += count
        target["partners"] = dict(
            sorted(partner_counts.items(), key=lambda item: (-item[1], item[0]))
        )

    for record in destination.values():
        games = record["wins"] + record["losses"] + record["draws"]
        placements = record["placements"]
        appearances = record["appearances"]

        record["best_placement"] = min(placements) if placements else None
        record["average_placement"] = (
            sum(placements) / len(placements) if placements else None
        )
        record["win_rate"] = record["wins"] / games if games else 0.0
        record["top_cut_rate"] = (
            record["top_cuts"] / appearances if appearances else 0.0
        )

    return destination


__all__ = [
    "finalize_event_results",
    "aggregate_pokemon_statistics",
    "merge_pokemon_statistics",
]
