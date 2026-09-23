"""Pokémon Champions item availability and normalisation.

The app previously built its held-item selector from ``BASE_HELD_ITEMS``, a
legacy generic-Pokémon list. That list contains items which are not legal in
Champions. This module provides the Champions-specific source of truth used
by the UI and team-state code.

The non-Mega pool is generated from the current Champions item catalogue.
Mega Stones are derived from the generated Champions registry so the item list
stays aligned with the Pokémon/forms the app actually supports.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Dict, List
import re

from champions.registry import (
    get_mega_forms,
    get_species,
    get_species_by_display_name,
    get_standard_items,
    load_registry,
)



@lru_cache(maxsize=1)
def get_mega_stone_map() -> Dict[str, str]:
    """Return Mega display name -> legal Champions Mega Stone from registry."""
    return {
        entry["display_name"]: entry["required_item"]
        for entry in get_mega_forms().values()
        if entry.get("display_name") and entry.get("required_item")
    }

CHAMPIONS_STANDARD_HELD_ITEMS = tuple(
    sorted(set(get_standard_items()), key=str.casefold)
)


@lru_cache(maxsize=2)
def get_champions_held_items(include_mega_stones: bool = True) -> List[str]:
    """Return sorted held-item selector options legal in Champions."""
    items = set(CHAMPIONS_STANDARD_HELD_ITEMS)
    if include_mega_stones:
        items.update(get_mega_stone_map().values())
    return sorted(items, key=str.casefold)



@lru_cache(maxsize=1)
def get_pokemon_specific_items() -> Dict[str, tuple[str, ...]]:
    """Build species/form-specific item choices from generated itemUser metadata."""
    registry = load_registry()
    result: Dict[str, set[str]] = {}

    for entry in registry.get("items", {}).values():
        if not entry.get("legal") or entry.get("is_mega_stone"):
            continue

        item_name = str(entry.get("display_name") or "").strip()
        if not item_name:
            continue

        for user in entry.get("item_users", []) or []:
            user_key = str(user).strip().casefold()
            if not user_key:
                continue

            # Resolve exact generated forms first.
            matched = (
                get_species_by_display_name(user_key)
                or get_species(user_key)
            )

            if matched:
                targets = [matched]
            else:
                # Showdown itemUser can mention a form that is outside the
                # Champions roster. Keep the item available to the matching
                # base species without maintaining another form table.
                base_name = user_key.split("-", 1)[0]
                matched = get_species(base_name)
                targets = [matched] if matched else []

            for species in targets:
                display = str(
                    species.get("display_name")
                    or species.get("source_name")
                    or ""
                ).strip()
                if display:
                    result.setdefault(display, set()).add(item_name)

    return {
        key: tuple(sorted(values, key=str.casefold))
        for key, values in result.items()
    }


POKEMON_SPECIFIC_ITEMS = get_pokemon_specific_items()



def _base_species_for_mega(species: str) -> str:
    """Return the base species name for a base or Mega display name."""
    value = str(species or "").strip()
    if value.casefold().startswith("mega "):
        value = value[5:].strip()
        parts = value.rsplit(" ", 1)
        if len(parts) == 2 and parts[1].casefold() in {"x", "y", "z"}:
            value = parts[0]
    return value


def get_contextual_item_groups(species: str):
    """Return (mega_items, species_items, standard_items) for one species."""
    species = str(species or "").strip()
    base = _base_species_for_mega(species)

    mega_items = []
    for mega_name, stone in get_mega_stone_map().items():
        mega_base = _base_species_for_mega(mega_name)
        if mega_base.casefold() == base.casefold():
            mega_items.append(stone)

    specific_lookup = {
        str(name).casefold(): tuple(items)
        for name, items in POKEMON_SPECIFIC_ITEMS.items()
    }

    species_items = list(specific_lookup.get(base.casefold(), ()))

    mega_items = sorted(set(mega_items), key=str.casefold)
    species_items = sorted(set(species_items), key=str.casefold)
    special = set(mega_items) | set(species_items)
    standard_items = [
        item
        for item in CHAMPIONS_STANDARD_HELD_ITEMS
        if item not in special
    ]
    return mega_items, species_items, standard_items



@lru_cache(maxsize=1)
def _item_display_lookup() -> Dict[str, str]:
    """Map tolerant item-name keys to the generated canonical display name."""
    lookup: Dict[str, str] = {}
    for entry in load_registry().get("items", {}).values():
        name = str(entry.get("display_name") or "").strip()
        if entry.get("legal") and name:
            key = re.sub(r"[^a-z0-9]+", "", name.casefold())
            lookup.setdefault(key, name)
    return lookup


def normalize_item_name(item_name: str) -> str:
    """Normalise user-entered item names against generated item metadata."""
    value = " ".join(str(item_name or "").strip().split())
    if not value:
        return ""

    key = re.sub(r"[^a-z0-9]+", "", value.casefold())
    return _item_display_lookup().get(key, value)



@lru_cache(maxsize=2)
def _champions_item_keys(include_mega_stones: bool) -> frozenset[str]:
    return frozenset(
        item.casefold()
        for item in get_champions_held_items(include_mega_stones=include_mega_stones)
    )


def is_champions_item(item_name: str, *, include_mega_stones: bool = True) -> bool:
    """Return whether an item is legal in the current Champions item pool."""
    normalized = normalize_item_name(item_name)
    return bool(normalized) and normalized.casefold() in _champions_item_keys(include_mega_stones)


CHAMPIONS_HELD_ITEMS = get_champions_held_items()
MEGA_STONE_MAP = get_mega_stone_map()


__all__ = [
    "CHAMPIONS_STANDARD_HELD_ITEMS",
    "CHAMPIONS_HELD_ITEMS",
    "MEGA_STONE_MAP",
    "get_champions_held_items",
    "get_mega_stone_map",
    "normalize_item_name",
    "is_champions_item",
    "POKEMON_SPECIFIC_ITEMS",
    "get_contextual_item_groups",
]
