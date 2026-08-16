import requests
import streamlit as strlit

from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock

from champions.constants import CUSTOM_MEGAS_DATA
from champions.move_data import display_name_for_move, get_champions_species_key
from champions.roster_data import get_clean_api_name, get_base_api_name, display_name_for_species_key


_DETAILS_MEMORY_CACHE = {}
_DETAILS_CACHE_LOCK = Lock()
_LEARNSETS_MEMORY_CACHE = None
_LEARNSETS_CACHE_LOCK = Lock()


def _get_cached_champions_learnsets():
    """Load the large Champions learnset file once per Python process."""
    global _LEARNSETS_MEMORY_CACHE
    with _LEARNSETS_CACHE_LOCK:
        if _LEARNSETS_MEMORY_CACHE is not None:
            return _LEARNSETS_MEMORY_CACHE

    from champions.roster_data import fetch_champions_learnsets
    learnsets = fetch_champions_learnsets() or {}

    with _LEARNSETS_CACHE_LOCK:
        if _LEARNSETS_MEMORY_CACHE is None:
            _LEARNSETS_MEMORY_CACHE = learnsets
        return _LEARNSETS_MEMORY_CACHE


def get_champion_moves_for(mon_name):
    """Return the Champions learnset for the exact Pokémon/form."""
    learnsets = _get_cached_champions_learnsets()
    if not learnsets:
        return []

    species_key = get_champions_species_key(mon_name)

    if species_key in learnsets:
        return [display_name_for_move(move_id) for move_id in learnsets[species_key]]

    if mon_name.startswith("Mega "):
        base_name = mon_name.replace("Mega ", "", 1).strip()
        base_key = get_champions_species_key(base_name)
        if base_key in learnsets:
            return [display_name_for_move(move_id) for move_id in learnsets[base_key]]

    return []


def _tournament_moves_for(mon_name):
    """Return optional observed tournament move frequencies for one species."""
    try:
        from champions.tournament_move_history import get_tournament_move_usage
        return get_tournament_move_usage(mon_name)
    except Exception:
        return {}


def _fetch_pokemon_details_uncached(mon_name):
    clean_api_name = get_clean_api_name(mon_name)
    sprite_url = f"https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/official-artwork/{clean_api_name}.png"
    box_sprite_url = f"https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/{clean_api_name}.png"

    custom_data = CUSTOM_MEGAS_DATA.get(mon_name, {})
    stats = {
        "hp": custom_data.get("hp", 80),
        "attack": custom_data.get("atk", 100),
        "defense": custom_data.get("def", 100),
        "special-attack": custom_data.get("spa", 100),
        "special-defense": custom_data.get("spd", 100),
        "speed": custom_data.get("spd_stat", 100),
    }
    custom_ability = custom_data.get("ability", "Standard")
    champion_moves = list(get_champion_moves_for(mon_name))

    types = ["Normal"]
    abilities = [custom_ability] if custom_ability else ["Standard"]
    moves = champion_moves if champion_moves else ["Tackle", "Protect", "Rest", "Substitute"]

    try:
        res = requests.get(f"https://pokeapi.co/api/v2/pokemon/{clean_api_name}", timeout=3)
        if res.status_code != 200 and mon_name.startswith("Mega "):
            res = requests.get(
                f"https://pokeapi.co/api/v2/pokemon/{get_base_api_name(mon_name)}",
                timeout=3,
            )
        if res.status_code == 200:
            data = res.json()
            sprite_url = data.get("sprites", {}).get("other", {}).get("official-artwork", {}).get("front_default") or sprite_url
            box_sprite_url = data.get("sprites", {}).get("front_default") or box_sprite_url
            types = [t["type"]["name"].title() for t in data.get("types", [])]
            if not custom_data:
                api_stats = {
                    entry["stat"]["name"]: entry["base_stat"]
                    for entry in data.get("stats", [])
                }
                if api_stats:
                    stats = api_stats
            api_abilities = [a["ability"]["name"].replace("-", " ").title() for a in data.get("abilities", [])]
            if custom_ability and custom_ability != "Standard":
                abilities = [custom_ability] + [ab for ab in api_abilities if ab != custom_ability]
            elif api_abilities:
                abilities = api_abilities
            if not champion_moves:
                fetched_moves = [m["move"]["name"].replace("-", " ").title() for m in data.get("moves", [])]
                if fetched_moves:
                    moves = fetched_moves
    except Exception:
        pass

    tournament_moves = _tournament_moves_for(mon_name)
    return {
        "sprite": sprite_url,
        "box_sprite": box_sprite_url,
        "types": types,
        "stats": stats,
        "abilities": abilities,
        "moves": sorted(list(set(moves))),
        "tournament_moves": tournament_moves,
    }


def fetch_pokemon_details_batch(mon_names, max_workers=12):
    """Fetch many Pokémon details concurrently without recursive prefetching.

    Counter analysis routinely needs dozens of candidates. The old design
    triggered a fresh 24-Pokémon prefetch every time *any* candidate was
    requested, creating an accidental O(N²) network workload. Batch loading
    makes the expensive network work explicitly bounded and parallel.
    """
    names = []
    seen = set()
    for name in mon_names or []:
        clean = str(name).strip()
        key = clean.casefold()
        if clean and key not in seen:
            seen.add(key)
            names.append(clean)

    results = {}
    missing = []
    with _DETAILS_CACHE_LOCK:
        for name in names:
            cached = _DETAILS_MEMORY_CACHE.get(name.casefold())
            if cached is not None:
                results[name] = cached
            else:
                missing.append(name)

    if missing:
        workers = max(1, min(int(max_workers or 1), len(missing), 12))

        def load_one(name):
            return name, _fetch_pokemon_details_uncached(name)

        with ThreadPoolExecutor(max_workers=workers) as executor:
            futures = [executor.submit(load_one, name) for name in missing]
            for future in as_completed(futures):
                try:
                    name, data = future.result()
                except Exception:
                    continue
                with _DETAILS_CACHE_LOCK:
                    _DETAILS_MEMORY_CACHE[name.casefold()] = data
                results[name] = data

    return results


@strlit.cache_data(ttl=86400, show_spinner=False)
def fetch_pokemon_details(mon_name):
    """Fetch one Pokémon's details, with no hidden candidate prefetch."""
    key = str(mon_name).strip().casefold()
    with _DETAILS_CACHE_LOCK:
        cached = _DETAILS_MEMORY_CACHE.get(key)
    if cached is not None:
        return cached

    data = _fetch_pokemon_details_uncached(mon_name)
    with _DETAILS_CACHE_LOCK:
        _DETAILS_MEMORY_CACHE[key] = data
    return data


def get_mini_sprite_url(mon_name):
    return fetch_pokemon_details(mon_name)["box_sprite"]
