"""Tournament move-usage extraction and normalization.

Limitless team snapshots currently preserve each player's raw decklist. This
module turns the move-bearing portions of those decklists into a conservative
Pokémon -> move frequency table. It deliberately refuses to guess when the
payload does not clearly identify a Pokémon/move relationship.
"""
from __future__ import annotations

import re
from collections import Counter, defaultdict
from typing import Any, Dict, Iterable, Mapping, MutableMapping, Optional

from champions.move_data import display_name_for_move

_MOVE_KEYS = ("moves", "move", "attacks", "moveset", "moveSet")
_POKEMON_KEYS = ("pokemon", "pokémon", "species", "name")


def _clean(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip())


def _looks_like_move(value: Any) -> bool:
    text = _clean(value)
    if not text or len(text) > 40:
        return False
    return bool(re.search(r"[A-Za-z]", text))


def _move_list(value: Any) -> list[str]:
    if isinstance(value, str):
        parts = re.split(r"[,|;/]\s*", value)
        return [_clean(part) for part in parts if _looks_like_move(part)]
    if isinstance(value, (list, tuple, set)):
        output = []
        for item in value:
            if isinstance(item, str) and _looks_like_move(item):
                output.append(_clean(item))
            elif isinstance(item, Mapping):
                for key in ("name", "move", "moveName"):
                    if isinstance(item.get(key), str) and _looks_like_move(item[key]):
                        output.append(_clean(item[key]))
                        break
        return output
    return []


def _walk(node: Any, current_pokemon: Optional[str] = None) -> Iterable[tuple[str, str]]:
    """Yield only explicit Pokémon/move relationships from nested JSON."""
    if isinstance(node, Mapping):
        pokemon = current_pokemon
        for key in _POKEMON_KEYS:
            value = node.get(key)
            if isinstance(value, str) and value.strip():
                # Do not treat a generic parent name as Pokémon unless this
                # object also contains move-like data.
                if any(k in node for k in _MOVE_KEYS):
                    pokemon = _clean(value)
                break

        for key in _MOVE_KEYS:
            if key in node and pokemon:
                for move in _move_list(node.get(key)):
                    yield pokemon, display_name_for_move(move)

        for key, value in node.items():
            if key in _MOVE_KEYS:
                continue
            yield from _walk(value, pokemon)

    elif isinstance(node, (list, tuple)):
        for item in node:
            yield from _walk(item, current_pokemon)


def extract_team_move_usage(decklist: Any) -> Dict[str, Dict[str, int]]:
    """Return ``{pokemon: {move: count}}`` from one raw tournament decklist."""
    output: MutableMapping[str, Counter] = defaultdict(Counter)
    for pokemon, move in _walk(decklist):
        pokemon = _clean(pokemon)
        move = _clean(move)
        if pokemon and move:
            output[pokemon][move] += 1
    return {pokemon: dict(counter) for pokemon, counter in output.items()}


def merge_move_usage(
    destination: MutableMapping[str, Dict[str, Any]],
    event_move_usage: Mapping[str, Mapping[str, int]],
    *,
    weight: float = 1.0,
) -> None:
    """Merge one event's move counts into the history aggregate."""
    for pokemon, moves in event_move_usage.items():
        record = destination.setdefault(
            str(pokemon).strip().lower(),
            {"uses": 0, "weighted_uses": 0.0, "moves": {}},
        )
        record.setdefault("moves", {})
        for move, count in moves.items():
            safe_count = max(0, int(count or 0))
            row = record["moves"].setdefault(
                str(move),
                {"uses": 0, "weighted_uses": 0.0},
            )
            row["uses"] += safe_count
            row["weighted_uses"] += safe_count * float(weight)
            record["uses"] += safe_count
            record["weighted_uses"] += safe_count * float(weight)


def finalize_move_usage(move_usage: Mapping[str, Mapping[str, Any]], top_n: int = 20) -> Dict[str, Any]:
    """Produce percentage-ranked move usage suitable for app/API consumers."""
    result: Dict[str, Any] = {}
    for pokemon, record in move_usage.items():
        moves = record.get("moves") or {}
        total = sum(max(0.0, float(row.get("weighted_uses", 0.0) or 0.0)) for row in moves.values())
        rows = []
        for move, row in moves.items():
            weighted = max(0.0, float(row.get("weighted_uses", 0.0) or 0.0))
            rows.append({
                "move": move,
                "uses": int(row.get("uses", 0) or 0),
                "weighted_uses": weighted,
                "usage_rate": weighted / total if total else 0.0,
            })
        rows.sort(key=lambda item: (item["usage_rate"], item["uses"]), reverse=True)
        result[str(pokemon).strip().lower()] = {
            "total_move_uses": int(record.get("uses", 0) or 0),
            "moves": rows[:max(0, int(top_n))],
        }
    return result
