"""Tournament-backed move recommendations for Champions analytics.

This layer sits above the existing move-history and local move-metadata systems.
It does not change counter scoring. It ranks moves that the selected Pokémon can
actually learn using observed tournament frequency, matchup pressure, STAB,
move quality, and evidence confidence.
"""
from __future__ import annotations

import math
from typing import Any, Dict, Iterable, Mapping, Sequence

import streamlit as strlit

from champions.move_metadata import get_move_metadata_many
from champions.tournament_move_history import get_tournament_move_recommendations
from champions.type_chart import get_type_relationships


_STATUS_UTILITY = {
    "protect": 1.0,
    "fake out": 1.0,
    "follow me": 1.0,
    "rage powder": 1.0,
    "taunt": 0.95,
    "encore": 0.95,
    "will-o-wisp": 0.9,
    "thunder wave": 0.9,
    "parting shot": 0.95,
    "u-turn": 0.9,
    "volt switch": 0.9,
    "flip turn": 0.9,
    "tailwind": 0.95,
    "trick room": 0.95,
    "helping hand": 0.9,
    "coaching": 0.9,
    "wide guard": 0.9,
    "quick guard": 0.85,
}


def _effectiveness(attacking_type: str, defending_types: Sequence[str]) -> float:
    relations = get_type_relationships(attacking_type) or {}
    double = {str(item.get("name", "")).title() for item in relations.get("double_damage_to", []) if isinstance(item, dict)}
    half = {str(item.get("name", "")).title() for item in relations.get("half_damage_to", []) if isinstance(item, dict)}
    immune = {str(item.get("name", "")).title() for item in relations.get("no_damage_to", []) if isinstance(item, dict)}
    multiplier = 1.0
    for defending_type in defending_types:
        name = str(defending_type).title()
        if name in immune:
            multiplier *= 0.0
        elif name in double:
            multiplier *= 2.0
        elif name in half:
            multiplier *= 0.5
    return multiplier


def _effectiveness_score(effectiveness: float) -> float:
    return {
        0.0: 0.0,
        0.25: 8.0,
        0.5: 20.0,
        1.0: 48.0,
        2.0: 82.0,
        4.0: 100.0,
    }.get(effectiveness, min(100.0, max(0.0, effectiveness * 42.0)))


def _move_quality(metadata: Mapping[str, Any]) -> float:
    name = str(metadata.get("name", "")).casefold()
    category = str(metadata.get("damage_class") or "status").lower()
    power = float(metadata.get("power", 0) or 0)

    if category == "status":
        return _STATUS_UTILITY.get(name, 0.25) * 100.0

    # 120 BP represents excellent direct damage without making enormous-power
    # outliers dominate the recommendation system.
    return min(100.0, power / 1.2)


def _pressure_score(metadata: Mapping[str, Any], target_types: Sequence[str], own_types: Sequence[str]) -> float:
    move_type = str(metadata.get("type") or "Normal").title()
    category = str(metadata.get("damage_class") or "status").lower()
    if category == "status":
        return 25.0 * _STATUS_UTILITY.get(str(metadata.get("name", "")).casefold(), 0.25)

    effectiveness = _effectiveness(move_type, target_types)
    stab = 1.0 if move_type in {str(item).title() for item in own_types} else 0.0
    power = float(metadata.get("power", 0) or 0)
    power_score = min(100.0, power / 1.2) if power > 0 else 0.0
    effectiveness_score = _effectiveness_score(effectiveness)
    return power_score * 0.35 + effectiveness_score * 0.50 + stab * 15.0


def _role_label(metadata: Mapping[str, Any], target_types: Sequence[str], own_types: Sequence[str]) -> str:
    name = str(metadata.get("name") or "")
    category = str(metadata.get("damage_class") or "status").lower()
    if category == "status":
        utility = _STATUS_UTILITY.get(name.casefold(), 0.0)
        return "High-value utility" if utility >= 0.8 else "Utility / support"
    effectiveness = _effectiveness(str(metadata.get("type") or "Normal"), target_types)
    move_type = str(metadata.get("type") or "Normal").title()
    if effectiveness >= 2.0:
        return "Super-effective pressure"
    if move_type in {str(item).title() for item in own_types}:
        return "Reliable STAB pressure"
    return "Coverage pressure"


@strlit.cache_data(ttl=3600, show_spinner=False)
def rank_recommended_moves(
    pokemon_name: str,
    legal_moves: tuple[str, ...],
    own_types: tuple[str, ...],
    target_types: tuple[str, ...] = (),
    *,
    top_n: int = 6,
    history_revision_token: str = "",
) -> list[Dict[str, Any]]:
    """Rank legal moves using tournament evidence plus matchup quality.

    Frequency is the strongest signal, but it is deliberately compressed so a
    99% move does not automatically receive the same score as every other
    common move. Matchup pressure, move quality, evidence confidence and
    priority then provide meaningful separation.

    A second greedy selection pass adds move diversity without changing the
    displayed score: duplicate move types/categories receive a small selection
    penalty so the final list is useful as a practical recommendation set.
    """
    legal = {str(move).strip().casefold(): str(move).strip() for move in legal_moves if str(move).strip()}
    if not legal:
        return []

    observed = get_tournament_move_recommendations(
        pokemon_name,
        legal_moves=tuple(legal.values()),
        top_n=max(12, int(top_n) * 3),
        min_frequency=0.0,
    )
    observed_by_key = {str(row.get("move", "")).casefold(): row for row in observed}

    metadata = get_move_metadata_many(legal.values())
    ranked: list[Dict[str, Any]] = []

    for key, move_name in legal.items():
        row = observed_by_key.get(key, {})
        frequency = max(0.0, min(1.0, float(row.get("frequency", 0.0) or 0.0)))
        count = int(row.get("count", 0) or 0)
        sample_size = int(row.get("sample_size", 0) or 0)
        confidence = max(0.0, min(1.0, float(row.get("confidence", 0.0) or 0.0)))
        meta = metadata.get(move_name) or {}

        pressure = _pressure_score(meta, target_types, own_types) if target_types else 50.0
        quality = _move_quality(meta)
        priority_raw = float(meta.get("priority", 0) or 0)
        priority = max(0.0, min(1.0, (priority_raw + 1.0) / 4.0))

        # Frequency is converted to a percentage and square-root compressed.
        # This preserves the value of tournament staples while preventing a
        # handful of 90-100% moves from collapsing into identical 100 scores.
        usage_component = 45.0 * math.sqrt(frequency)
        score = (
            usage_component
            + pressure * 0.25
            + quality * 0.10
            + confidence * 10.0
            + priority * 5.0
        ) / 0.95
        if frequency <= 0.0:
            score *= 0.72

        effectiveness = _effectiveness(str(meta.get("type") or "Normal"), target_types) if target_types else 1.0
        ranked.append({
            "move": str(meta.get("name") or move_name),
            "score": round(max(0.0, min(100.0, score)), 1),
            "frequency": round(frequency * 100.0, 2),
            "count": count,
            "sample_size": sample_size,
            "confidence": round(confidence * 100.0, 1),
            "type": str(meta.get("type") or "Normal").title(),
            "power": int(meta.get("power", 0) or 0),
            "category": str(meta.get("damage_class") or "status").lower(),
            "priority": int(meta.get("priority", 0) or 0),
            "effectiveness": effectiveness,
            "reason": _role_label(meta, target_types, own_types),
            "_selection_score": score,
        })

    ranked.sort(key=lambda row: (-row["_selection_score"], -row["frequency"], -row["count"], row["move"].casefold()))

    selected: list[Dict[str, Any]] = []
    remaining = list(ranked)
    limit = max(1, int(top_n))
    while remaining and len(selected) < limit:
        best_index = 0
        best_selection_score = float("-inf")
        for index, row in enumerate(remaining):
            penalty = 0.0
            if any(row["type"] == chosen["type"] for chosen in selected):
                penalty += 4.0
            if any(row["category"] == chosen["category"] for chosen in selected):
                penalty += 2.0
            candidate_selection_score = row["_selection_score"] - penalty
            if candidate_selection_score > best_selection_score:
                best_selection_score = candidate_selection_score
                best_index = index

        chosen = remaining.pop(best_index)
        chosen.pop("_selection_score", None)
        selected.append(chosen)

    return selected


def get_recommended_moves(
    pokemon_name: str,
    pokemon_data: Mapping[str, Any],
    *,
    target_types: Iterable[str] = (),
    top_n: int = 6,
    history_revision_token: str = "",
) -> list[Dict[str, Any]]:
    """Public convenience wrapper for meta analytics/UI callers."""
    legal_moves = tuple(str(move) for move in pokemon_data.get("moves", []) if str(move).strip())
    own_types = tuple(str(item) for item in pokemon_data.get("types", []) if str(item).strip())
    return rank_recommended_moves(
        str(pokemon_name),
        legal_moves,
        own_types,
        tuple(str(item) for item in target_types if str(item).strip()),
        top_n=top_n,
        history_revision_token=str(history_revision_token),
    )
