"""Pokémon Champions item availability and normalisation.

The app previously built its held-item selector from ``BASE_HELD_ITEMS``, a
legacy generic-Pokémon list.  That list contains items which are not legal in
Champions.  This module provides the Champions-specific source of truth used
by the UI and team-state code.

The non-Mega pool is based on the current Champions M-B legal-item catalogue;
Mega Stones are derived from the project's own Champions Mega roster so the
item list stays aligned with the Pokémon/forms the app actually supports.
"""

from __future__ import annotations

from typing import Dict, List

from champions.constants import CUSTOM_MEGAS_DATA


# Current non-Mega Champions held items.  Keep this separate from the legacy
# BASE_HELD_ITEMS list: that constant is intentionally not used for UI legality.
CHAMPIONS_STANDARD_HELD_ITEMS = (
    "Aspear Berry",
    "Babiri Berry",
    "Big Root",
    "Black Belt",
    "Black Glasses",
    "Bright Powder",
    "Charcoal",
    "Charti Berry",
    "Cheri Berry",
    "Chesto Berry",
    "Chilan Berry",
    "Choice Scarf",
    "Chople Berry",
    "Coba Berry",
    "Colbur Berry",
    "Damp Rock",
    "Dragon Fang",
    "Expert Belt",
    "Fairy Feather",
    "Focus Band",
    "Focus Sash",
    "Hard Stone",
    "Haban Berry",
    "Heat Rock",
    "Icy Rock",
    "Iron Ball",
    "King's Rock",
    "Kasib Berry",
    "Kebia Berry",
    "Leftovers",
    "Leppa Berry",
    "Life Orb",
    "Light Ball",
    "Light Clay",
    "Lum Berry",
    "Magnet",
    "Mental Herb",
    "Metal Coat",
    "Metronome",
    "Miracle Seed",
    "Muscle Band",
    "Mystic Water",
    "Never-Melt Ice",
    "Occa Berry",
    "Oran Berry",
    "Passho Berry",
    "Payapa Berry",
    "Pecha Berry",
    "Persim Berry",
    "Poison Barb",
    "Quick Claw",
    "Rawst Berry",
    "Rindo Berry",
    "Roseli Berry",
    "Scope Lens",
    "Sharp Beak",
    "Shed Shell",
    "Shell Bell",
    "Shuca Berry",
    "Silk Scarf",
    "Silver Powder",
    "Sitrus Berry",
    "Smooth Rock",
    "Soft Sand",
    "Spell Tag",
    "Tanga Berry",
    "Twisted Spoon",
    "Wacan Berry",
    "White Herb",
    "Wide Lens",
    "Wise Glasses",
    "Yache Berry",
    "Zoom Lens",
)


# A few Mega names in CUSTOM_MEGAS_DATA do not follow the simple
# "Species + ite" spelling used by the older helper.
_MEGA_STONE_OVERRIDES = {
    "Mega Raichu X": "Raichunite X",
    "Mega Raichu Y": "Raichunite Y",
    "Mega Floette": "Floettite",
    "Mega Meowstic Male": "Meowsticite",
    "Mega Meowstic Female": "Meowsticite",
    "Mega Excadrill": "Excadrite",
    "Mega Dragonite": "Dragoninite",
    "Mega Greninja": "Greninjite",
    "Mega Glimmora": "Glimmoranite",
    "Mega Starmie": "Starminite",
}


def _mega_stone_for_species(species: str) -> str:
    override = _MEGA_STONE_OVERRIDES.get(species)
    if override:
        return override

    base = species.removeprefix("Mega ").replace(" ", "")
    return f"{base}ite"


def get_mega_stone_map() -> Dict[str, str]:
    """Return Mega Pokémon -> legal Champions Mega Stone mapping."""
    return {
        species: _mega_stone_for_species(species)
        for species in CUSTOM_MEGAS_DATA
        if str(species).startswith("Mega ")
    }


def get_champions_held_items(include_mega_stones: bool = True) -> List[str]:
    """Return the sorted held-item selector options legal in Champions."""
    items = set(CHAMPIONS_STANDARD_HELD_ITEMS)
    if include_mega_stones:
        items.update(get_mega_stone_map().values())
    return sorted(items, key=str.casefold)


def normalize_item_name(item_name: str) -> str:
    """Normalise harmless whitespace/casing differences without inventing data."""
    value = " ".join(str(item_name or "").strip().split())
    if not value:
        return ""

    aliases = {
        "kings rock": "King's Rock",
        "never melt ice": "Never-Melt Ice",
        "icy rock": "Icy Rock",
    }
    return aliases.get(value.casefold(), value)


def is_champions_item(item_name: str, *, include_mega_stones: bool = True) -> bool:
    """Return whether an item is legal in the current Champions item pool."""
    normalized = normalize_item_name(item_name)
    if not normalized:
        return False
    return normalized.casefold() in {
        item.casefold()
        for item in get_champions_held_items(include_mega_stones=include_mega_stones)
    }


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
]
