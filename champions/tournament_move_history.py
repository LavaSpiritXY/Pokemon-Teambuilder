"""Tournament move-frequency extraction and history enrichment.

The Champions history aggregate stores team-level usage today. This module
adds a move-usage layer from the raw tournament decklists when the source
exposes moves. Move frequency is measured as the percentage of observed team
lists containing a move, not as a percentage of all move slots. The enrichment
is rebuilt from cached snapshots each run so repeated workflow executions are
idempotent.
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


def extract_tournament_move_observations(snapshot: Mapping[str, Any]) -> Dict[str, Dict[str, Any]]:
    """Return per-Pokémon move counts plus the number of observed teams.

    A move counts once per team list for a Pokémon. The sample size counts team
    lists in which that Pokémon had usable move information. This produces a
    genuine "percentage of sets using this move" rather than percentages that
    merely sum to 100 across move slots.
    """
    output: Dict[str, Dict[str, Any]] = {}
    for team in snapshot.get("teams") or []:
        if not isinstance(team, Mapping):
            continue
        decklist = team.get("raw_decklist") or team.get("decklist")
        seen_species: set[str] = set()
        seen_moves: set[tuple[str, str]] = set()
        for pokemon_name, moves in _walk_decklist(decklist):
            species_key = get_champions_species_key(pokemon_name)
            if not species_key:
                continue
            record = output.setdefault(species_key, {"counts": {}, "sample_size": 0})
            if species_key not in seen_species:
                record["sample_size"] = int(record.get("sample_size", 0)) + 1
                seen_species.add(species_key)
            counts = record["counts"]
            for move in moves:
                move_key = str(move).strip()
                if not move_key:
                    continue
                marker = (species_key, move_key.casefold())
                if marker in seen_moves:
                    continue
                seen_moves.add(marker)
                counts[move_key] = int(counts.get(move_key, 0)) + 1
    return output


def extract_tournament_moves(snapshot: Mapping[str, Any]) -> Dict[str, Dict[str, int]]:
    """Backward-compatible move-count-only view of a tournament snapshot."""
    observations = extract_tournament_move_observations(snapshot)
    return {
        species_key: dict(record.get("counts") or {})
        for species_key, record in observations.items()
    }


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
    """Rebuild move observations from all cached tournament snapshots.

    Rebuilding rather than incrementally adding to the existing aggregate is
    intentional: the same cached event must never be counted twice when the
    scheduled GitHub Actions workflow runs again.
    """
    if not history_path.exists() or not cache_dir.exists():
        return False

    try:
        history = json.loads(history_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    if not isinstance(history, dict):
        return False

    pokemon_records = history.setdefault("pokemon", {})
    rebuilt_counts: Dict[str, Dict[str, int]] = {}
    rebuilt_samples: Dict[str, int] = {}

    for path in sorted(cache_dir.glob("*.json")):
        if path.name == "manifest.json":
            continue
        try:
            snapshot = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if not isinstance(snapshot, dict):
            continue

        observations = extract_tournament_move_observations(snapshot)
        for species_key, observation in observations.items():
            counts = rebuilt_counts.setdefault(species_key, {})
            _merge_counts(counts, observation.get("counts") or {})
            rebuilt_samples[species_key] = rebuilt_samples.get(species_key, 0) + int(observation.get("sample_size", 0) or 0)

    changed = False
    touched = set(rebuilt_counts) | set(rebuilt_samples)
    for species_key in touched:
        record = pokemon_records.get(species_key)
        if not isinstance(record, dict):
            continue

        counts = rebuilt_counts.get(species_key, {})
        sample_size = max(0, int(rebuilt_samples.get(species_key, 0) or 0))
        usage = [
            {
                "move": move,
                "count": int(count),
                "sample_size": sample_size,
                "frequency": min(1.0, int(count) / sample_size) if sample_size else 0.0,
            }
            for move, count in counts.items()
            if int(count or 0) > 0
        ]
        usage.sort(key=lambda row: (-row["frequency"], -row["count"], row["move"].lower()))

        if record.get("move_counts") != counts:
            record["move_counts"] = counts
            changed = True
        if record.get("move_usage") != usage:
            record["move_usage"] = usage
            changed = True
        if record.get("move_sample_size") != sample_size:
            record["move_sample_size"] = sample_size
            changed = True

    # Remove stale move observations for Pokémon that no longer appear in the
    # available cache. This keeps the generated history faithful to its source.
    for species_key, record in pokemon_records.items():
        if not isinstance(record, dict) or species_key in touched:
            continue
        for field, empty in (("move_counts", {}), ("move_usage", []), ("move_sample_size", 0)):
            if record.get(field) != empty and field in record:
                record[field] = empty
                changed = True

    if not changed:
        return False

    temporary = history_path.with_suffix(history_path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(history, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    temporary.replace(history_path)
    return True


@lru_cache(maxsize=8)
def _load_history_cached(history_path_str: str, mtime_ns: int) -> Dict[str, Any]:
    """Load one history JSON once per file version."""
    try:
        data = json.loads(Path(history_path_str).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def _load_history(history_path: Path) -> Dict[str, Any]:
    try:
        mtime_ns = history_path.stat().st_mtime_ns
    except OSError:
        return {}
    return _load_history_cached(str(history_path.resolve()), mtime_ns)


def get_tournament_move_usage(
    pokemon_name: Any,
    *,
    top_n: Optional[int] = None,
    history_path: Path = DEFAULT_HISTORY_PATH,
) -> Dict[str, float]:
    """Return observed move frequencies as {display_name: 0..1}."""
    key = get_champions_species_key(pokemon_name)
    if not key or not history_path.exists():
        return {}

    history = _load_history(history_path)
    record = (history.get("pokemon") or {}).get(key)
    if not isinstance(record, dict):
        return {}
    rows = record.get("move_usage") or []
    if not isinstance(rows, list):
        return {}
    output: Dict[str, float] = {}
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


def get_tournament_move_sample_size(
    pokemon_name: Any,
    *,
    history_path: Path = DEFAULT_HISTORY_PATH,
) -> int:
    """Return the number of observed team lists supporting move evidence."""
    key = get_champions_species_key(pokemon_name)
    if not key or not history_path.exists():
        return 0
    history = _load_history(history_path)
    record = (history.get("pokemon") or {}).get(key)
    if not isinstance(record, dict):
        return 0
    try:
        return max(0, int(record.get("move_sample_size", 0) or 0))
    except (TypeError, ValueError):
        return 0
