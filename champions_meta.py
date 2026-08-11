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
    """Generate conservative lookup aliases without collapsing real forms."""
    key = _normalise_name(name)
    if not key:
        return []
    candidates = [key]

    # Common app display conventions.
    if key.startswith("mega "):
        candidates.append(key[5:])
    if key.endswith(" mega"):
        candidates.append(key[:-5].strip())

    # Regional/form prefixes: only use the base species as a fallback.
    for prefix in ("alolan ", "galarian ", "hisuian ", "paldean "):
        if key.startswith(prefix):
            candidates.append(key[len(prefix):])

    # Common suffix conventions used by the app/Pokémon data sources.
    for suffix in (" mega x", " mega y", " combat breed", " blaze breed", " aqua breed"):
        if key.endswith(suffix):
            candidates.append(key[:-len(suffix)].strip())
    if key == "eternal flower floette":
        candidates.extend(["eternal flower floette", "floette"])

    # Avoid duplicate aliases while preserving exact-first order.
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
        # First pass exact/normalised aliases against the stored keys.
        for candidate in _candidate_keys(pokemon_name):
            row = source.get(candidate)
            if row is not None:
                return row
        # Final pass handles legacy keys containing punctuation/casing.
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
