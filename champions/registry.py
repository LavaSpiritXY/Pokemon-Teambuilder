"""Canonical generated data registry for Pokemon Champions.

The generated JSON is produced by tools/sync_champions_registry.py from
Pokemon Showdown canonical data. Application modules can import this file
without making network requests.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Optional


REGISTRY_PATH = Path(__file__).resolve().parents[1] / "champions_registry.json"
REGISTRY_SCHEMA_VERSION = 1


@lru_cache(maxsize=2)
def load_registry(path: Path = REGISTRY_PATH) -> Dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(
            f"Champions registry not found at {path}. "
            "Run tools/sync_champions_registry.py first."
        )

    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("Champions registry must contain a JSON object.")

    validate_registry(payload)
    return payload


def validate_registry(payload: Dict[str, Any]) -> None:
    if not isinstance(payload, dict):
        raise ValueError("Registry payload must be a dictionary.")

    if payload.get("schema_version") != REGISTRY_SCHEMA_VERSION:
        raise ValueError(
            f"Unsupported Champions registry schema: "
            f"{payload.get('schema_version')!r}"
        )

    species = payload.get("species")
    if not isinstance(species, dict) or not species:
        raise ValueError("Registry must contain a non-empty 'species' mapping.")

    megas = payload.get("megas")
    if not isinstance(megas, dict):
        raise ValueError("Registry must contain a 'megas' mapping.")

    base_roster = payload.get("base_roster")
    if not isinstance(base_roster, list):
        raise ValueError("Registry must contain a 'base_roster' list.")

    learnsets = payload.get("learnsets", {})
    if not isinstance(learnsets, dict):
        raise ValueError("Registry 'learnsets' data must be a mapping.")

    items = payload.get("items", {})
    if not isinstance(items, dict):
        raise ValueError("Registry 'items' data must be a mapping.")

    for species_key, moves in learnsets.items():
        if not isinstance(species_key, str) or not species_key:
            raise ValueError("Every learnset key must be a non-empty string.")
        if not isinstance(moves, list) or not moves:
            raise ValueError(f"Registry learnset {species_key!r} has no moves.")
        if any(not isinstance(move, str) or not move for move in moves):
            raise ValueError(f"Registry learnset {species_key!r} contains an invalid move.")

    for item_key, entry in items.items():
        if not isinstance(item_key, str) or not item_key:
            raise ValueError("Every registry item key must be a non-empty string.")
        if not isinstance(entry, dict):
            raise ValueError(f"Registry item {item_key!r} must be an object.")
        if not isinstance(entry.get("display_name"), str) or not entry["display_name"]:
            raise ValueError(f"Registry item {item_key!r} has no display name.")
        if not isinstance(entry.get("legal"), bool):
            raise ValueError(f"Registry item {item_key!r} has invalid legality.")
        if not isinstance(entry.get("is_mega_stone"), bool):
            raise ValueError(f"Registry item {item_key!r} has invalid Mega Stone flag.")
        if not isinstance(entry.get("mega_stone_map"), dict):
            raise ValueError(f"Registry item {item_key!r} has invalid Mega Stone mapping.")

    for field in ("standard_items", "mega_stones"):
        values = payload.get(field, [])
        if not isinstance(values, list):
            raise ValueError(f"Registry '{field}' data must be a list.")

    for species_key, entry in species.items():
        if not isinstance(species_key, str) or not species_key:
            raise ValueError("Every registry species key must be a non-empty string.")
        if not isinstance(entry, dict):
            raise ValueError(f"Registry entry {species_key!r} must be an object.")

        required = (
            "display_name",
            "base_species_key",
            "types",
            "base_stats",
            "abilities",
        )
        missing = [field for field in required if field not in entry]
        if missing:
            raise ValueError(
                f"Registry species {species_key!r} is missing: {', '.join(missing)}"
            )

        if not isinstance(entry["types"], list) or not entry["types"]:
            raise ValueError(f"Registry species {species_key!r} has no types.")

        if not isinstance(entry["abilities"], list) or not entry["abilities"]:
            raise ValueError(f"Registry species {species_key!r} has no abilities.")

        for optional in ("source_name", "api_slug", "canonical_key"):
            value = entry.get(optional)
            if value is not None and (not isinstance(value, str) or not value.strip()):
                raise ValueError(
                    f"Registry species {species_key!r} has invalid {optional}."
                )

        stats = entry["base_stats"]
        if not isinstance(stats, dict):
            raise ValueError(f"Registry species {species_key!r} has invalid base stats.")

        missing_stats = [
            stat for stat in ("hp", "atk", "def", "spa", "spd", "spe")
            if stat not in stats
        ]
        if missing_stats:
            raise ValueError(
                f"Registry species {species_key!r} is missing stats: "
                f"{', '.join(missing_stats)}"
            )

    for mega_key, mega in megas.items():
        if mega_key not in species:
            raise ValueError(f"Mega {mega_key!r} is missing from species registry.")
        if not isinstance(mega, dict):
            raise ValueError(f"Mega registry entry {mega_key!r} must be an object.")
        if not mega.get("base_species_key"):
            raise ValueError(f"Mega {mega_key!r} has no base species.")
        if not mega.get("required_item"):
            raise ValueError(f"Mega {mega_key!r} has no required item/stone.")

    current_regulation = payload.get("current_regulation")
    if current_regulation is not None:
        value = str(current_regulation).strip().upper()
        if not value.startswith("M-"):
            raise ValueError(
                f"Invalid current regulation in registry: {current_regulation!r}"
            )


def get_species(species_key: str, registry: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    data = registry or load_registry()
    key = str(species_key or "").strip().casefold()
    return data["species"].get(key, {})


def get_learnset(
    species_key: str,
    registry: Optional[Dict[str, Any]] = None,
) -> list[str]:
    data = registry or load_registry()
    key = str(species_key or "").strip().casefold()
    return list(data.get("learnsets", {}).get(key, []))


def get_standard_items(registry: Optional[Dict[str, Any]] = None) -> list[str]:
    data = registry or load_registry()
    return list(data.get("standard_items", []))


def get_mega_stones(registry: Optional[Dict[str, Any]] = None) -> list[str]:
    data = registry or load_registry()
    return list(data.get("mega_stones", []))


def get_current_regulation(registry: Optional[Dict[str, Any]] = None) -> Optional[str]:
    """Return the current regulation recorded in the generated registry."""
    data = registry or load_registry()
    value = str(data.get("current_regulation") or "").strip().upper()
    return value or None


def get_species_by_canonical_key(
    canonical_key: str,
    registry: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Return a species/form record by the app's stable canonical key."""
    data = registry or load_registry()
    target = str(canonical_key or "").strip().casefold()
    if not target:
        return {}

    for entry in data["species"].values():
        if str(entry.get("canonical_key", "")).strip().casefold() == target:
            return dict(entry)

    return {}


def get_species_key_by_display_name(
    display_name: str,
    registry: Optional[Dict[str, Any]] = None,
) -> str:
    """Return the stable canonical key for a UI display name."""
    data = registry or load_registry()
    target = str(display_name or "").strip().casefold()
    if not target:
        return ""

    for entry in data["species"].values():
        if str(entry.get("display_name", "")).strip().casefold() == target:
            return str(entry.get("canonical_key") or "")

    return ""


def get_species_by_display_name(
    display_name: str,
    registry: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Return a canonical species/form record by its UI display name."""
    data = registry or load_registry()
    target = str(display_name or "").strip().casefold()
    if not target:
        return {}

    for entry in data["species"].values():
        if str(entry.get("display_name", "")).strip().casefold() == target:
            return dict(entry)

    return {}

def get_mega_forms(registry: Optional[Dict[str, Any]] = None) -> Dict[str, Dict[str, Any]]:
    data = registry or load_registry()
    return dict(data["megas"])


def get_base_roster(registry: Optional[Dict[str, Any]] = None) -> list[str]:
    data = registry or load_registry()
    return list(data["base_roster"])


__all__ = [
    "REGISTRY_PATH",
    "REGISTRY_SCHEMA_VERSION",
    "load_registry",
    "validate_registry",
    "get_species",
    "get_current_regulation",
    "get_learnset",
    "get_standard_items",
    "get_mega_stones",
    "get_species_by_display_name",
    "get_species_key_by_display_name",
    "get_species_by_canonical_key",
    "get_mega_forms",
    "get_base_roster",
]
