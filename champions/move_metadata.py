"""Fast local move metadata for the Champions analysis engines.

The counter engine may inspect hundreds of moves while scoring a single target.
This module deliberately downloads the Pokémon Showdown move tables once and
turns the useful fields into an in-memory dictionary. PokeAPI is only used as
a fallback for a genuinely unknown move.
"""
from __future__ import annotations

import re
from typing import Any, Dict, Mapping

import requests
import streamlit as strlit

from champions.move_data import get_move_api_slug, get_hardcoded_move_type


_MOVE_TABLE_URLS = (
    "https://raw.githubusercontent.com/smogon/pokemon-showdown/master/data/moves.ts",
    "https://raw.githubusercontent.com/smogon/pokemon-showdown/master/data/mods/champions/moves.ts",
)


def _parse_move_table(text: str) -> Dict[str, Dict[str, Any]]:
    """Parse top-level Showdown move objects without evaluating TypeScript."""
    result: Dict[str, Dict[str, Any]] = {}
    entry_re = re.compile(
        r"^\t(?:\"([^\"]+)\"|([A-Za-z0-9_]+))\s*:\s*\{(.*?)(?=^\t(?:\"[^\"]+\"|[A-Za-z0-9_]+)\s*:\s*\{|^};)",
        re.MULTILINE | re.DOTALL,
    )

    for match in entry_re.finditer(text):
        move_id = (match.group(1) or match.group(2) or "").strip().lower()
        block = match.group(3)
        if not move_id:
            continue

        name_match = re.search(r"^\t\tname:\s*[\"']([^\"']+)[\"']", block, re.MULTILINE)
        type_match = re.search(r"^\t\ttype:\s*[\"']([^\"']+)[\"']", block, re.MULTILINE)
        category_match = re.search(r"^\t\tcategory:\s*[\"']([^\"']+)[\"']", block, re.MULTILINE)
        power_match = re.search(r"^\t\tbasePower:\s*(\d+)", block, re.MULTILINE)
        priority_match = re.search(r"^\t\tpriority:\s*(-?\d+)", block, re.MULTILINE)
        accuracy_match = re.search(r"^\t\taccuracy:\s*(true|false|\d+)", block, re.MULTILINE)

        if not (name_match or type_match):
            continue

        accuracy: Any = None
        if accuracy_match:
            raw_accuracy = accuracy_match.group(1)
            accuracy = raw_accuracy if raw_accuracy in {"true", "false"} else int(raw_accuracy)

        result[move_id] = {
            "name": name_match.group(1) if name_match else move_id,
            "type": type_match.group(1).title() if type_match else "",
            "power": int(power_match.group(1)) if power_match else 0,
            "damage_class": category_match.group(1).lower() if category_match else "status",
            "priority": int(priority_match.group(1)) if priority_match else 0,
            "accuracy": accuracy,
        }

    return result


@strlit.cache_data(ttl=86400, show_spinner=False)
def fetch_master_move_metadata() -> Dict[str, Dict[str, Any]]:
    """Download and parse the move tables once per Streamlit cache lifetime."""
    metadata: Dict[str, Dict[str, Any]] = {}
    for url in _MOVE_TABLE_URLS:
        try:
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                # Champions/mod data wins when it contains an override.
                metadata.update(_parse_move_table(response.text))
        except Exception:
            continue
    return metadata


MASTER_MOVE_METADATA = fetch_master_move_metadata()


def _normalise_key(move_name: str) -> str:
    raw = str(move_name or "").strip().lower()
    raw = raw.split(" (")[0]
    raw = raw.replace("’", "").replace("'", "").replace(".", "")
    return re.sub(r"[^a-z0-9]+", "", raw)


def get_move_metadata(move_name: str) -> Dict[str, Any]:
    """Return move metadata from the local table, with a rare API fallback."""
    key = _normalise_key(move_name)
    if not key:
        return {}

    direct = MASTER_MOVE_METADATA.get(key)
    if direct:
        return dict(direct)

    # Showdown keys can retain hyphens while the normalised lookup removes them.
    slug = get_move_api_slug(move_name).replace("-", "")
    direct = MASTER_MOVE_METADATA.get(slug)
    if direct:
        return dict(direct)

    # Last-resort compatibility path. This should be hit only for moves absent
    # from both Showdown tables, never once per ordinary counter candidate.
    try:
        response = requests.get(
            f"https://pokeapi.co/api/v2/move/{get_move_api_slug(move_name)}",
            timeout=3,
        )
        if response.status_code == 200:
            data = response.json()
            return {
                "name": str(data.get("name") or move_name),
                "type": str(data.get("type", {}).get("name") or get_hardcoded_move_type(move_name) or "Normal").title(),
                "power": int(data.get("power") or 0),
                "damage_class": str(data.get("damage_class", {}).get("name") or "status").lower(),
                "priority": int(data.get("priority") or 0),
                "accuracy": data.get("accuracy"),
            }
    except Exception:
        pass

    return {
        "name": str(move_name),
        "type": get_hardcoded_move_type(move_name) or "Normal",
        "power": 0,
        "damage_class": "status",
        "priority": 0,
        "accuracy": None,
    }


def get_move_metadata_many(move_names) -> Dict[str, Dict[str, Any]]:
    """Resolve a collection entirely from the local table where possible."""
    return {str(name): get_move_metadata(str(name)) for name in dict.fromkeys(move_names or []) if str(name).strip()}
