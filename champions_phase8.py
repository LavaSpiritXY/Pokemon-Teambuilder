"""Phase 8 helpers for historical Champions event discovery and exact cuts.

This module is deliberately isolated from app.py.  It adds two things we
need before building the historical database:

1. Paginated discovery of Champions tournaments across all available pages.
2. A phase-aware top-cut detector that inspects the tournament details payload
   instead of assuming every event is Top 8.

The functions are defensive because tournament phase payloads can vary.
"""

from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional, Set, Tuple

from champions_data import (
    CHAMPIONS_REGULATIONS,
    get_limitless_tournament_details,
    list_limitless_tournaments,
)


def discover_champions_tournaments(
    *,
    regulations: Iterable[str] = CHAMPIONS_REGULATIONS,
    page_limit: int = 100,
    max_pages: int = 100,
) -> List[Dict[str, Any]]:
    """Discover and de-duplicate Champions tournaments across API pages.

    We stop pagination for a regulation when a page returns no rows.  If a
    service returns fewer than page_limit rows, we still request the next page
    once so an exact page boundary cannot hide the end condition.
    """

    if page_limit < 1 or page_limit > 100:
        raise ValueError("page_limit must be between 1 and 100")
    if max_pages < 1:
        raise ValueError("max_pages must be >= 1")

    found: Dict[str, Dict[str, Any]] = {}

    for regulation in regulations:
        if regulation not in CHAMPIONS_REGULATIONS:
            raise ValueError(f"Unsupported Champions regulation: {regulation!r}")

        for page in range(1, max_pages + 1):
            rows = list_limitless_tournaments(
                page=page,
                limit=page_limit,
                regulation=regulation,
            )

            if not rows:
                break

            for row in rows:
                event_id = str(row.get("id", "")).strip()
                if not event_id:
                    continue
                found[event_id] = row

            # Continue one more page even when the page is short; the API may
            # apply filters after pagination.
            if len(rows) == 0:
                break

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

    # Prefer explicit elimination/cut fields.
    for key in (
        "topCut",
        "top_cut",
        "cut",
        "cutSize",
        "cut_size",
        "eliminationSize",
        "elimination_size",
    ):
        value = _as_int(phase.get(key))
        if value and value >= 2:
            return value

    # Some payloads describe the phase by name, e.g. "Top 8".
    name = str(phase.get("name") or phase.get("title") or "")
    import re

    match = re.search(r"top\s*(\d+)", name, flags=re.IGNORECASE)
    if match:
        return int(match.group(1))

    return None


def extract_exact_top_cut_size(details: Dict[str, Any]) -> Optional[int]:
    """Return the elimination cut size when the details payload states it."""

    phases = details.get("phases")
    if not isinstance(phases, list):
        return None

    candidates: List[int] = []
    for phase in phases:
        size = _phase_cut_size(phase)
        if size:
            candidates.append(size)

    if not candidates:
        return None

    # The smallest explicit top-cut size represents the final elimination
    # field (e.g. Top 16 -> Top 8 -> Top 4 -> Top 2).
    return min(candidates)


def exact_top_cut_flags(
    details: Dict[str, Any],
    placements: Iterable[Optional[int]],
) -> Tuple[Optional[int], List[bool]]:
    """Calculate top-cut flags without inventing a cutoff."""

    cut_size = extract_exact_top_cut_size(details)
    if cut_size is None:
        return None, [False for _ in placements]

    flags = [
        placement is not None and 1 <= placement <= cut_size
        for placement in placements
    ]
    return cut_size, flags


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
