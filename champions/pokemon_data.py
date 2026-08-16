import requests
import streamlit as strlit

from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock

from champions.constants import CUSTOM_MEGAS_DATA
from champions.move_data import display_name_for_move, get_champions_species_key
from champions.roster_data import get_clean_api_name, get_base_api_name, display_name_for_species_key


_DETAILS_MEMORY_CACHE = {}
_DETAILS_CACHE_LOCK = Lock()
_PREFETCHED_TARGETS = set()


def get_champion_moves_for(mon_name):
    """
    Return the Champions learnset for the exact Pokémon/form.
    """
    from champions.roster_data import fetch_champions_learnsets

    learnsets = fetch_champions_learnsets()
    if not learnsets:
        return []

    species_key = get_champions_species_key(mon_name)

    if species_key in learnsets:
        return [
            display_name_for_move(move_id)
            for move_id in learnsets[species_key]
        ]

    if mon_name.startswith("Mega "):
        base_name = mon_name.replace("Mega ", "", 1).strip()
        base_key = get_champions_species_key(base_name)
        if base_key in learnsets:
            return [
                display_name_for_move(move_id)
                for move_id in learnsets[base_key]
            ]

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


def _prefetch_counter_candidates(target_name):
    """Warm only the high-value current-history candidates in parallel.

    The counter engine does not need the entire Champions Pokédex. Fetching
    every species on the first meta-analysis request caused hundreds of
    PokeAPI/history lookups and made a single target take minutes. Keep the
    broad candidate pool in meta_analytics, but cap the expensive detail
    prefetch to the same practical shortlist used by that pipeline.
    """
    target_key = str(target_name).strip().lower()
    with _DETAILS_CACHE_LOCK:
        if target_key in _PREFETCHED_TARGETS:
            return
        _PREFETCHED_TARGETS.add(target_key)

    try:
        from champions.history_data import load_champions_history
        from champions.species_keys import canonical_species_key
        from champions.tournament_data import get_tournament_partners

        history = load_champions_history() or {}
        records = history.get("pokemon") or {}
        if not isinstance(records, dict):
            return

        active_regulation = str(history.get("active_regulation") or "").strip().upper()
        target_key_canonical = canonical_species_key(target_name)
        ranked = []

        for species_key, record in records.items():
            display_name = display_name_for_species_key(species_key)
            if not display_name or display_name.lower().startswith("mega "):
                continue
            if canonical_species_key(display_name) == target_key_canonical:
                continue
            record = record if isinstance(record, dict) else {}
            regulations = record.get("regulation_metrics") or {}
            current = regulations.get(active_regulation, {}) if active_regulation else {}
            current = current if isinstance(current, dict) else {}
            appearances = float(current.get("appearances", 0) or record.get("appearances", 0) or 0)
            recent = float(record.get("recent_usage_weight", 0) or 0)
            top_cut = float(current.get("top_cut_rate", 0) or record.get("top_cut_rate", 0) or 0)
            usage = float(record.get("usage", 0) or 0)
            score = (
                min(50.0, appearances / 20.0)
                + min(25.0, recent * 25.0)
                + min(15.0, top_cut * 30.0)
                + min(10.0, usage * 10.0)
            )
            ranked.append((score, display_name))

        ranked.sort(key=lambda item: (-item[0], item[1].casefold()))
        names = [name for _, name in ranked[:60]]

        try:
            partner_names = []
            for partner_key, _count in get_tournament_partners(target_name, top_n=24):
                partner_name = display_name_for_species_key(partner_key)
                if (
                    partner_name
                    and not partner_name.lower().startswith("mega ")
                    and canonical_species_key(partner_name) != target_key_canonical
                ):
                    partner_names.append(partner_name)
            names = list(dict.fromkeys(partner_names + names))[:72]
        except Exception:
            pass

        if not names:
            return

        def load_one(name):
            data = _fetch_pokemon_details_uncached(name)
            with _DETAILS_CACHE_LOCK:
                _DETAILS_MEMORY_CACHE[name.casefold()] = data
            return data

        with ThreadPoolExecutor(max_workers=16) as executor:
            futures = [executor.submit(load_one, name) for name in names]
            for future in as_completed(futures):
                try:
                    future.result()
                except Exception:
                    pass
    except Exception:
        return


@strlit.cache_data(ttl=86400, show_spinner=False)
def fetch_pokemon_details(mon_name):
    key = str(mon_name).strip().casefold()
    with _DETAILS_CACHE_LOCK:
        cached = _DETAILS_MEMORY_CACHE.get(key)
    if cached is not None:
        return cached

    _prefetch_counter_candidates(mon_name)

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
