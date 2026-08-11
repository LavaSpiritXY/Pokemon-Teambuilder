"""Phase 18.1 robust Champions species/form resolution."""
from __future__ import annotations
import re
from typing import List


def _normalise(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", str(value or "").strip().lower())


def champions_lookup_candidates(name: str) -> List[str]:
    raw = str(name or "").strip()
    if not raw:
        return []
    candidates: List[str] = []

    def add(value: str) -> None:
        value = _normalise(value)
        if value and value not in candidates:
            candidates.append(value)

    add(raw)
    lowered = re.sub(r"[-_]+", " ", raw).strip().lower()

    # Mega Charizard X/Y, Charizard-Mega-X/Y and similar UI variants.
    match = re.match(r"^mega\s+(.+?)\s+([xy])$", lowered)
    if match:
        base, suffix = match.groups()
        add(f"{base}-mega-{suffix}")
        add(base)
    match = re.match(r"^(.+?)[- ]mega[- ]([xy])$", lowered)
    if match:
        base, suffix = match.groups()
        add(f"{base}-mega-{suffix}")
        add(base)

    # Regional/form suffixes.
    for suffix in ("-mega-x", "-mega-y", "-mega", "-alola", "-galar", "-hisui", "-paldea", "-combat", "-blaze", "-aqua", "-dusk", "-dawn", "-midnight", "-eternalflower"):
        if lowered.endswith(suffix):
            add(lowered[:-len(suffix)])

    for prefix in ("alolan ", "galarian ", "hisuian ", "paldean ", "eternal flower "):
        if lowered.startswith(prefix):
            add(lowered[len(prefix):])

    return candidates


def resolve_tournament_record(name: str, records: dict):
    if not isinstance(records, dict):
        return None
    for candidate in champions_lookup_candidates(name):
        if candidate in records:
            return records[candidate]
    return None
