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

from champions.registry import get_mega_forms, get_standard_items



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



# Items that are meaningfully associated with one species/form.  These are
# surfaced separately in the UI, but remain legal only when appropriate.
POKEMON_SPECIFIC_ITEMS = {
    "Pikachu": ("Light Ball",),
}


def _base_species_for_mega(species: str) -> str:
    value = str(species or "").strip()
    if value.startswith("Mega "):
        value = value[5:]
        # Mega Raichu X/Y and Mega Charizard X/Y share their base species.
        if value.endswith((" X", " Y", " Z")):
            value = value.rsplit(" ", 1)[0]
    return value


def get_contextual_item_groups(species: str):
    """Return (mega_items, species_items, standard_items) for one species."""
    species = str(species or "").strip()
    base = _base_species_for_mega(species)

    mega_items = []
    for mega_name, stone in get_mega_stone_map().items():
        if _base_species_for_mega(mega_name).casefold() == base.casefold():
            mega_items.append(stone)

    species_items = list(POKEMON_SPECIFIC_ITEMS.get(base, ()))
    mega_items = sorted(set(mega_items), key=str.casefold)
    species_items = sorted(set(species_items), key=str.casefold)
    special = set(mega_items) | set(species_items)
    standard_items = [
        item for item in CHAMPIONS_STANDARD_HELD_ITEMS
        if item not in special
    ]
    return mega_items, species_items, standard_items


_ITEM_ALIASES = {
    "kings rock": "King's Rock",
    "never melt ice": "Never-Melt Ice",
    "icy rock": "Icy Rock",
}


def normalize_item_name(item_name: str) -> str:
    """Normalise harmless whitespace/casing differences without inventing data."""
    value = " ".join(str(item_name or "").strip().split())
    if not value:
        return ""
    return _ITEM_ALIASES.get(value.casefold(), value)


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
