"""Tournament move-frequency extraction and history enrichment.

The Champions history aggregate stores team-level usage today. This module
adds an optional move-usage layer from the raw tournament decklists when the
source exposes moves. It is deliberately schema-tolerant because Limitless
payloads have used several decklist shapes over time.
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Iterable, Mapping, Optional

from champions.move_data import get_champions_species_key, display_name_for_move

DEFAULT_HISTORY_PATH = Path("champions_meta_history.json")
DEFAULT_CACHE_DIR = Path("champions_cache")


def _normalise_move(value: Any) -> str:
    if isinstance(value, dict):
        value = value.get("name") or value.get("move") or value.get("id")
    return str(value or "").strip()


def _pokemon_name(value: Any) -> str:
    if isinstance(value, str):
        return value.strip()
    if not isinstance(value, Mapping):
        return ""
    return str(value.get("pokemon") or value.get("pokémon") or value.get("name") or "").strip()


def _moves_from_pokemon_record(record: Mapping[str, Any]) -> list[str]:
    raw = record.get("moves") or record.get("move") or record.get("attacks")
    if not isinstance(raw, (list, tuple)):
        return []
    moves = []
    for item in raw:
        move = _normalise_move(item)
        if move:
            moves.append(display_name_for_move(move) or move)
    return list(dict.fromkeys(moves))


def _walk_decklist(value: Any) -> Iterable[tuple[str, list[str]]]:
    """Yield (pokemon, moves) pairs from several plausible decklist shapes."""
    if isinstance(value, list):
        for item in value:
            yield from _walk_decklist(item)
        return

    if not isinstance(value, Mapping):
        return

    name = _pokemon_name(value)
    moves = _moves_from_pokemon_record(value)
    if name and moves:
        yield name, moves

    for key in ("pokemon", "pokémon", "team", "members", "cards", "deck", "decklist", "contents"):
        child = value.get(key)
        if isinstance(child, (Mapping, list)):
            yield from _walk_decklist(child)


def extract_tournament_moves(snapshot: Mapping[str, Any]) -> Dict[str, Dict[str, int]]:
    """Return raw move counts keyed by canonical Pokémon species key."""
    output: Dict[str, Dict[str, int]] = {}
    for team in snapshot.get("teams") or []:
        if not isinstance(team, Mapping):
            continue
        decklist = team.get("raw_decklist") or team.get("decklist")
        for pokemon_name, moves in _walk_decklist(decklist):
            species_key = get_champions_species_key(pokemon_name)
            if not species_key:
                continue
            counts = output.setdefault(species_key, {})
            for move in moves:
                move_key = str(move).strip()
                if move_key:
                    counts[move_key] = counts.get(move_key, 0) + 1
    return output


def _merge_counts(target: Dict[str, int], source: Mapping[str, Any]) -> None:
    for move, count in source.items():
        try:
            value = max(0, int(count or 0))
        except (TypeError, ValueError):
            continue
        if value:
            target[move] = target.get(move, 0) + value


def enrich_history_with_tournament_moves(
    *,
    history_path: Path = DEFAULT_HISTORY_PATH,
    cache_dir: Path = DEFAULT_CACHE_DIR,
) -> bool:
    """Merge move observations from downloaded event snapshots into history."""
    if not history_path.exists() or not cache_dir.exists():
        return False

    try:
        history = json.loads(history_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    if not isinstance(history, dict):
        return False

    pokemon_records = history.setdefault("pokemon", {})
    changed = False

    for path in sorted(cache_dir.glob("*.json")):
        if path.name == "manifest.json":
            continue
        try:
            snapshot = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if not isinstance(snapshot, dict):
            continue

        move_counts = extract_tournament_moves(snapshot)
        for species_key, counts in move_counts.items():
            record = pokemon_records.get(species_key)
            if not isinstance(record, dict):
                continue
            aggregate = record.setdefault("move_counts", {})
            before = dict(aggregate)
            _merge_counts(aggregate, counts)
            if aggregate != before:
                changed = True

    for record in pokemon_records.values():
        if not isinstance(record, dict):
            continue
        counts = record.get("move_counts") or {}
        if not isinstance(counts, Mapping) or not counts:
            continue
        total = sum(max(0, int(v or 0)) for v in counts.values())
        if not total:
            continue
        usage = [
            {
                "move": move,
                "count": int(count),
                "frequency": int(count) / total,
            }
            for move, count in counts.items()
            if int(count or 0) > 0
        ]
        usage.sort(key=lambda row: (-row["frequency"], row["move"].lower()))
        if record.get("move_usage") != usage:
            record["move_usage"] = usage
            changed = True

    if not changed:
        return False

    temporary = history_path.with_suffix(history_path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(history, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    temporary.replace(history_path)
    _load_history_cached.cache_clear()
    return True


@lru_cache(maxsize=4)
def _load_history_cached(path_str: str, modified_ns: int, file_size: int) -> Dict[str, Any]:
    """Load move history once per file revision instead of once per Pokémon."""
    path = Path(path_str)
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _history_revision(path: Path) -> tuple[int, int]:
    try:
        stat = path.stat()
        return stat.st_mtime_ns, stat.st_size
    except OSError:
        return 0, 0


def get_tournament_move_usage(
    pokemon_name: Any,
    *,
    top_n: Optional[int] = None,
    history_path: Path = DEFAULT_HISTORY_PATH,
) -> Dict[str, float]:
    """Return observed move frequencies as {display_name: 0..1}.

    The generated history file is large enough that reading/parsing it once for
    every candidate creates a major avoidable cost during counter analysis.
    Cache it by modification time and size so the sync job can still invalidate
    the cache naturally when the file changes.
    """
    key = get_champions_species_key(pokemon_name)
    if not key or not history_path.exists():
        return {}

    modified_ns, file_size = _history_revision(history_path)
    history = _load_history_cached(str(history_path), modified_ns, file_size)
    record = (history.get("pokemon") or {}).get(key)
    if not isinstance(record, dict):
        return {}
    rows = record.get("move_usage") or []
    if not isinstance(rows, list):
        return {}
    output = {}
    for row in rows:
        if not isinstance(row, Mapping):
            continue
        move = str(row.get("move") or "").strip()
        if not move:
            continue
        try:
            frequency = float(row.get("frequency", 0.0) or 0.0)
        except (TypeError, ValueError):
            continue
        output[move] = max(0.0, min(1.0, frequency))
        if top_n and len(output) >= top_n:
            break
    return output
