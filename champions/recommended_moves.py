"""Tournament-backed move recommendations for Champions analytics.

This layer sits above the existing move-history and local move-metadata systems.
It does not change counter scoring. It ranks moves that the selected Pokémon can
actually learn using observed tournament frequency, matchup pressure, STAB,
move quality, and evidence confidence.
"""
from __future__ import annotations

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


def _pressure_score(metadata: Mapping[str, Any], target_types: Sequence[str], own_types: Sequence[str]) -> float:
    move_type = str(metadata.get("type") or "Normal").title()
    power = float(metadata.get("power", 0) or 0)
    category = str(metadata.get("damage_class") or "status").lower()
    if category == "status":
        return 25.0 * _STATUS_UTILITY.get(str(metadata.get("name", "")).casefold(), 0.25)

    effectiveness = _effectiveness(move_type, target_types)
    stab = 1.0 if move_type in {str(item).title() for item in own_types} else 0.0
    power_score = min(100.0, power / 1.2) if power > 0 else 0.0
    effectiveness_score = {0.0: 0.0, 0.25: 10.0, 0.5: 20.0, 1.0: 48.0, 2.0: 82.0, 4.0: 100.0}.get(effectiveness, min(100.0, effectiveness * 42.0))
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

    Tournament frequency is the strongest signal, but it cannot by itself make
    an obviously irrelevant move rank first. This keeps recommendations useful
    both for a selected Pokémon and when a target matchup is supplied.
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
        frequency = float(row.get("frequency", 0.0) or 0.0)
        count = int(row.get("count", 0) or 0)
        sample_size = int(row.get("sample_size", 0) or 0)
        confidence = float(row.get("confidence", 0.0) or 0.0)
        meta = metadata.get(move_name) or {}
        pressure = _pressure_score(meta, target_types, own_types) if target_types else 50.0
        utility = _STATUS_UTILITY.get(str(meta.get("name", move_name)).casefold(), 0.0)
        quality = min(100.0, float(meta.get("power", 0) or 0) / 1.2) if str(meta.get("damage_class", "status")).lower() != "status" else utility * 100.0
        priority = max(0.0, min(1.0, (float(meta.get("priority", 0) or 0) + 1.0) / 4.0))

        # Observed tournament frequency dominates. Matchup pressure and move
        # quality break ties and make the list useful for a specific target.
        score = (
            frequency * 55.0
            + pressure * 25.0
            + quality * 10.0
            + confidence * 5.0
            + priority * 5.0
        )
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
        })

    ranked.sort(key=lambda row: (-row["score"], -row["frequency"], -row["count"], row["move"].casefold()))
    return ranked[: max(1, int(top_n))]


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
