"""Phase 13: safe interface to the aggregated Pokémon Champions dataset.

Phase 18.1 extends the lookup layer with conservative form/alias fallbacks.
Exact tournament keys always win; when an exact form is absent, a Mega or
regional/form display name may fall back to its base species so the UI does
not silently lose tournament evidence.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

DEFAULT_META_PATH = Path("champions_meta_history.json")


def _normalise_name(name: str) -> str:
    value = " ".join(str(name or "").strip().lower().split())
    value = value.replace("’", "'")
    value = re.sub(r"[^a-z0-9 ]+", " ", value)
    return " ".join(value.split())


def _candidate_keys(name: str) -> List[str]:
    """Generate exact-first lookup aliases for display/form names."""
    key = _normalise_name(name)
    if not key:
        return []
    candidates = [key]

    def add(value: str) -> None:
        value = _normalise_name(value)
        if value and value not in candidates:
            candidates.append(value)

    # Mega display forms. Preserve the exact form first, then progressively
    # fall back to the species. Both "Mega Charizard X" and "Charizard Mega X"
    # therefore resolve to the tournament species "charizard" when needed.
    if key.startswith("mega "):
        remainder = key[5:].strip()
        add(remainder)
        match = re.match(r"^(.+?)\s+([xy])$", remainder)
        if match:
            add(match.group(1))
    if key.endswith(" mega"):
        add(key[:-5].strip())
    for suffix in (" mega x", " mega y"):
        if key.endswith(suffix):
            add(key[:-len(suffix)].strip())

    # Regional display prefixes.
    for prefix in ("alolan ", "galarian ", "hisuian ", "paldean "):
        if key.startswith(prefix):
            add(key[len(prefix):])

    # Form suffixes. Keep the exact form first; these are fallbacks only.
    for suffix in (" combat breed", " blaze breed", " aqua breed"):
        if key.endswith(suffix):
            add(key[:-len(suffix)].strip())

    if key == "eternal flower floette":
        add("floette")

    return list(dict.fromkeys(candidates))


class ChampionsMetaStore:
    """Read-only access to the aggregated Champions meta dataset."""

    def __init__(self, path: Path = DEFAULT_META_PATH) -> None:
        self.path = Path(path)
        self._data: Optional[Dict[str, Any]] = None

    def load(self) -> Dict[str, Any]:
        if self._data is not None:
            return self._data
        if not self.path.exists():
            self._data = {"schema_version": 0, "events_processed": 0, "pokemon": {}, "partners": {}, "available": False}
            return self._data
        try:
            with self.path.open("r", encoding="utf-8") as handle:
                data = json.load(handle)
        except (OSError, json.JSONDecodeError) as exc:
            raise RuntimeError(f"Could not load Champions meta data from {self.path}: {exc}") from exc
        if not isinstance(data, dict):
            raise RuntimeError("Champions meta dataset must contain a JSON object.")
        pokemon, partners = data.get("pokemon"), data.get("partners")
        if not isinstance(pokemon, dict) or not isinstance(partners, dict):
            raise RuntimeError("Champions meta dataset has an unexpected schema: 'pokemon' and 'partners' must be objects.")
        data["available"] = True
        self._data = data
        return data

    def _lookup(self, table: str, pokemon_name: str) -> Optional[Any]:
        source = self.load().get(table, {})
        if not isinstance(source, dict):
            return None
        for candidate in _candidate_keys(pokemon_name):
            row = source.get(candidate)
            if row is not None:
                return row
        normalised_source = {_normalise_name(k): v for k, v in source.items() if isinstance(k, str)}
        for candidate in _candidate_keys(pokemon_name):
            if candidate in normalised_source:
                return normalised_source[candidate]
        return None

    def get(self, pokemon_name: str) -> Optional[Dict[str, Any]]:
        row = self._lookup("pokemon", pokemon_name)
        return row if isinstance(row, dict) else None

    def get_partners(self, pokemon_name: str, limit: int = 10) -> List[Dict[str, Any]]:
        rows = self._lookup("partners", pokemon_name)
        if not isinstance(rows, list):
            return []
        return [row for row in rows if isinstance(row, dict)][:max(0, limit)]

    def summary(self) -> Dict[str, Any]:
        data = self.load()
        return {
            "available": bool(data.get("available", False)),
            "schema_version": data.get("schema_version"),
            "events_processed": int(data.get("events_processed", 0) or 0),
            "pokemon_records": len(data.get("pokemon", {})),
            "partner_records": sum(len(rows) for rows in data.get("partners", {}).values() if isinstance(rows, list)),
            "reference_date": data.get("reference_date"),
            "recency_half_life_days": data.get("recency_half_life_days"),
        }


_DEFAULT_STORE = ChampionsMetaStore()

def get_champions_meta(pokemon_name: str) -> Optional[Dict[str, Any]]:
    return _DEFAULT_STORE.get(pokemon_name)

def get_champions_partners(pokemon_name: str, limit: int = 10) -> List[Dict[str, Any]]:
    return _DEFAULT_STORE.get_partners(pokemon_name, limit=limit)

def get_champions_meta_summary() -> Dict[str, Any]:
    return _DEFAULT_STORE.summary()
