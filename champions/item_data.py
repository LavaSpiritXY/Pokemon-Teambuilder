"""Pokémon Champions item availability and normalisation.

The app previously built its held-item selector from ``BASE_HELD_ITEMS``, a
legacy generic-Pokémon list. That list contains items which are not legal in
Champions. This module provides the Champions-specific source of truth used
by the UI and team-state code.

The non-Mega pool is based on the current Champions M-B legal-item catalogue;
Mega Stones are derived from the project's own Champions Mega roster so the
item list stays aligned with the Pokémon/forms the app actually supports.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Dict, List

from champions.constants import CUSTOM_MEGAS_DATA


CHAMPIONS_STANDARD_HELD_ITEMS = (
    "Aspear Berry", "Babiri Berry", "Big Root", "Black Belt", "Black Glasses",
    "Bright Powder", "Charcoal", "Charti Berry", "Cheri Berry", "Chesto Berry",
    "Chilan Berry", "Choice Scarf", "Chople Berry", "Coba Berry", "Colbur Berry",
    "Damp Rock", "Dragon Fang", "Expert Belt", "Fairy Feather", "Focus Band",
    "Focus Sash", "Hard Stone", "Haban Berry", "Heat Rock", "Icy Rock", "Iron Ball",
    "King's Rock", "Kasib Berry", "Kebia Berry", "Leftovers", "Leppa Berry", "Life Orb",
    "Light Ball", "Light Clay", "Lum Berry", "Magnet", "Mental Herb", "Metal Coat",
    "Metronome", "Miracle Seed", "Muscle Band", "Mystic Water", "Never-Melt Ice",
    "Occa Berry", "Oran Berry", "Passho Berry", "Payapa Berry", "Pecha Berry",
    "Persim Berry", "Poison Barb", "Quick Claw", "Rawst Berry", "Rindo Berry",
    "Roseli Berry", "Scope Lens", "Sharp Beak", "Shed Shell", "Shell Bell",
    "Shuca Berry", "Silk Scarf", "Silver Powder", "Sitrus Berry", "Smooth Rock",
    "Soft Sand", "Spell Tag", "Tanga Berry", "Twisted Spoon", "Wacan Berry",
    "White Herb", "Wide Lens", "Wise Glasses", "Yache Berry", "Zoom Lens",
)


# Mega Stone names are not safely derivable by simply removing "Mega" and
# appending "ite". Keep explicit mappings for the canonical stones and the
# project's Champions-specific Mega forms. This prevents malformed selector
# entries such as ``CharizardYite`` or ``Blastoisite``.
_MEGA_STONE_OVERRIDES = {
    "Mega Venusaur": "Venusaurite",
    "Mega Abomasnow": "Abomasite",
    "Mega Charizard X": "Charizardite X",
    "Mega Charizard Y": "Charizardite Y",
    "Mega Blastoise": "Blastoisinite",
    "Mega Beedrill": "Beedrillite",
    "Mega Pidgeot": "Pidgeotite",
    "Mega Raichu X": "Raichunite X",
    "Mega Raichu Y": "Raichunite Y",
    "Mega Clefable": "Clefablite",
    "Mega Alakazam": "Alakazite",
    "Mega Victreebel": "Victreebelite",
    "Mega Slowbro": "Slowbronite",
    "Mega Gengar": "Gengarite",
    "Mega Kangaskhan": "Kangaskhanite",
    "Mega Starmie": "Starminite",
    "Mega Pinsir": "Pinsirite",
    "Mega Gyarados": "Gyaradosite",
    "Mega Aerodactyl": "Aerodactylite",
    "Mega Dragonite": "Dragoninite",
    "Mega Tyranitar": "Tyranitarite",
    "Mega Sceptile": "Sceptilite",
    "Mega Blaziken": "Blazikenite",
    "Mega Swampert": "Swampertite",
    "Mega Gardevoir": "Gardevoirite",
    "Mega Sableye": "Sablenite",
    "Mega Mawile": "Mawilite",
    "Mega Aggron": "Aggronite",
    "Mega Medicham": "Medichamite",
    "Mega Manectric": "Manectite",
    "Mega Sharpedo": "Sharpedonite",
    "Mega Camerupt": "Cameruptite",
    "Mega Altaria": "Altarianite",
    "Mega Banette": "Banettite",
    "Mega Absol": "Absolite",
    "Mega Glalie": "Glalitite",
    "Mega Metagross": "Metagrossite",
    "Mega Staraptor": "Staraptorite",
    "Mega Lopunny": "Lopunnite",
    "Mega Garchomp": "Garchompite",
    "Mega Lucario": "Lucarionite",
    "Mega Gallade": "Galladite",
    "Mega Emboar": "Emboarite",
    "Mega Excadrill": "Excadrite",
    "Mega Audino": "Audinoite",
    "Mega Scrafty": "Scraftinite",
    "Mega Chandelure": "Chandelurite",
    "Mega Golurk": "Golurkite",
    "Mega Greninja": "Greninjite",
    "Mega Floette": "Floettite",
    "Mega Meowstic Male": "Meowsticite",
    "Mega Meowstic Female": "Meowsticite",
    "Mega Malamar": "Malamarite",
    "Mega Barbaracle": "Barbaracite",
    "Mega Dragalge": "Dragalgite",
    "Mega Hawlucha": "Hawluchanite",
    "Mega Glimmora": "Glimmoranite",
}


def _mega_stone_for_species(species: str) -> str:
    override = _MEGA_STONE_OVERRIDES.get(species)
    if override:
        return override
    base = species.removeprefix("Mega ").replace(" ", "")
    return f"{base}ite"


@lru_cache(maxsize=1)
def get_mega_stone_map() -> Dict[str, str]:
    """Return Mega Pokémon -> legal Champions Mega Stone mapping."""
    return {
        species: _mega_stone_for_species(species)
        for species in CUSTOM_MEGAS_DATA
        if str(species).startswith("Mega ")
    }


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
        value = value.rsplit(" ", 1)[0] if value.endswith((" X", " Y")) else value
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
