"""Phase 8/9 helpers for historical Champions discovery and exact cuts.

Discovery deliberately uses the lightweight tournament listing endpoint only.
Individual /details requests are reserved for a specific event that we are
actually going to ingest. This prevents historical discovery from triggering
hundreds of rate-limited detail requests.
"""

from __future__ import annotations

import re
from typing import Any, Dict, Iterable, List, Optional, Tuple

from champions_data import CHAMPIONS_REGULATIONS, list_limitless_tournaments


def _listing_regulation(row: Dict[str, Any]) -> str:
    """Get the regulation from a listing row without fetching event details."""
    for key in ("format", "regulation", "regulation_name"):
        value = row.get(key)
        if value:
            value = str(value).strip()
            if value in CHAMPIONS_REGULATIONS:
                return value

    # Some listing payloads expose the regulation only in the tournament name.
    name = str(row.get("name") or "")
    match = re.search(r"\bReg\s*(M-[AB])\b", name, flags=re.IGNORECASE)
    if match:
        return match.group(1).upper()

    return ""


def discover_champions_tournaments(
    *,
    regulations: Iterable[str] = CHAMPIONS_REGULATIONS,
    page_limit: int = 100,
    max_pages: int = 100,
) -> List[Dict[str, Any]]:
    """Discover and de-duplicate Champions tournaments without detail calls.

    This function intentionally does not call get_limitless_tournament_details.
    The resulting rows are lightweight manifests; details are fetched later
    only for events selected for historical ingestion.
    """
    if page_limit < 1 or page_limit > 100:
        raise ValueError("page_limit must be between 1 and 100")
    if max_pages < 1:
        raise ValueError("max_pages must be >= 1")

    requested = set(regulations)
    invalid = requested - CHAMPIONS_REGULATIONS
    if invalid:
        raise ValueError(f"Unsupported Champions regulation(s): {sorted(invalid)}")

    found: Dict[str, Dict[str, Any]] = {}

    for page in range(1, max_pages + 1):
        rows = list_limitless_tournaments(page=page, limit=page_limit)
        if not rows:
            break

        for row in rows:
            event_id = str(row.get("id", "")).strip()
            if not event_id:
                continue
            regulation = _listing_regulation(row)
            if regulation not in requested:
                continue
            found[event_id] = {**row, "format": regulation}

        # A short page can still be a valid page boundary. Requesting the next
        # page is cheap because this endpoint is only the listing endpoint.

    return list(found.values())


def _as_int(value: Any) -> Optional[int]:
    try:
        if value is None or value == "":
            return None
        return int(value)
    except (TypeError, ValueError):
        return None


def _phase_cut_size(phase: Dict[str, Any]) -> Optional[int]:
    """Extract a plausible elimination-field size from one phase object."""
    if not isinstance(phase, dict):
        return None

    for key in (
        "topCut", "top_cut", "cut", "cutSize", "cut_size",
        "eliminationSize", "elimination_size",
    ):
        value = _as_int(phase.get(key))
        if value and value >= 2:
            return value

    name = str(phase.get("name") or phase.get("title") or "")
    match = re.search(r"top\s*(\d+)", name, flags=re.IGNORECASE)
    if match:
        return int(match.group(1))
    return None


def extract_exact_top_cut_size(details: Dict[str, Any]) -> Optional[int]:
    """Return the elimination cut size when the details payload states it."""
    phases = details.get("phases")
    if not isinstance(phases, list):
        return None

    candidates = []
    for phase in phases:
        size = _phase_cut_size(phase)
        if size:
            candidates.append(size)
    return min(candidates) if candidates else None


def exact_top_cut_flags(
    details: Dict[str, Any],
    placements: Iterable[Optional[int]],
) -> Tuple[Optional[int], List[bool]]:
    """Calculate top-cut flags without inventing a cutoff."""
    cut_size = extract_exact_top_cut_size(details)
    if cut_size is None:
        return None, [False for _ in placements]

    return cut_size, [
        placement is not None and 1 <= placement <= cut_size
        for placement in placements
    ]


def summarize_discovery(events: Iterable[Dict[str, Any]]) -> Dict[str, int]:
    """Return a small audit summary for discovered events."""
    summary = {regulation: 0 for regulation in sorted(CHAMPIONS_REGULATIONS)}
    completed = 0

    for event in events:
        regulation = str(event.get("format", ""))
        if regulation in summary:
            summary[regulation] += 1
        if event.get("ended"):
            completed += 1

    summary["total"] = sum(summary.values())
    summary["completed"] = completed
    return summary


__all__ = [
    "discover_champions_tournaments",
    "extract_exact_top_cut_size",
    "exact_top_cut_flags",
    "summarize_discovery",
]
