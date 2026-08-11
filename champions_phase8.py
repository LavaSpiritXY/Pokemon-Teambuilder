"""Phase 8/9 helpers for historical Champions discovery and exact cuts.

Discovery deliberately uses the lightweight tournament listing endpoint only.
Individual /details requests are reserved for a specific event that we are
actually going to ingest. This prevents historical discovery from triggering
hundreds of rate-limited detail requests.
"""

from __future__ import annotations

import re
import time
from typing import Any, Dict, Iterable, List, Optional, Tuple

import requests

from champions_data import CHAMPIONS_REGULATIONS, list_limitless_tournaments

DISCOVERY_DELAY_SECONDS = 2.0
DISCOVERY_MAX_RETRIES = 5


def _listing_regulation(row: Dict[str, Any]) -> str:
    """Get the regulation from a listing row without fetching event details."""
    for key in ("format", "regulation", "regulation_name"):
        value = row.get(key)
        if value:
            value = str(value).strip()
            if value in CHAMPIONS_REGULATIONS:
                return value

    name = str(row.get("name") or "")
    match = re.search(r"\bReg\s*(M-[AB])\b", name, flags=re.IGNORECASE)
    if match:
        return match.group(1).upper()

    return ""


def _load_listing_page(page: int, page_limit: int) -> List[Dict[str, Any]]:
    """Fetch one listing page with bounded 429/5xx backoff."""
    delay = DISCOVERY_DELAY_SECONDS

    for attempt in range(DISCOVERY_MAX_RETRIES + 1):
        try:
            rows = list_limitless_tournaments(page=page, limit=page_limit)
            if page > 1:
                time.sleep(DISCOVERY_DELAY_SECONDS)
            return rows
        except requests.HTTPError as exc:
            status = exc.response.status_code if exc.response is not None else None
            if status not in {429, 500, 502, 503, 504} or attempt >= DISCOVERY_MAX_RETRIES:
                raise

            retry_after = None
            if exc.response is not None:
                raw = exc.response.headers.get("Retry-After")
                try:
                    retry_after = float(raw) if raw is not None else None
                except (TypeError, ValueError):
                    retry_after = None

            sleep_for = max(delay, retry_after or 0.0)
            print(
                f"Listing page {page}: HTTP {status}; "
                f"waiting {sleep_for:.1f}s before retry {attempt + 1}/{DISCOVERY_MAX_RETRIES}"
            )
            time.sleep(sleep_for)
            delay = min(delay * 2.0, 30.0)

    raise RuntimeError("Unreachable listing retry state")


def discover_champions_tournaments(
    *,
    regulations: Iterable[str] = CHAMPIONS_REGULATIONS,
    page_limit: int = 100,
    max_pages: int = 100,
) -> List[Dict[str, Any]]:
    """Discover and de-duplicate Champions tournaments without detail calls."""
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
        print(f"Discovering tournament listing page {page}...")
        rows = _load_listing_page(page, page_limit)
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

    return list(found.values())


def _as_int(value: Any) -> Optional[int]:
    try:
        if value is None or value == "":
            return None
        return int(value)
    except (TypeError, ValueError):
        return None


def _phase_cut_size(phase: Dict[str, Any]) -> Optional[int]:
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
    return int(match.group(1)) if match else None


def extract_exact_top_cut_size(details: Dict[str, Any]) -> Optional[int]:
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
    cut_size = extract_exact_top_cut_size(details)
    if cut_size is None:
        return None, [False for _ in placements]
    return cut_size, [
        placement is not None and 1 <= placement <= cut_size
        for placement in placements
    ]


def summarize_discovery(events: Iterable[Dict[str, Any]]) -> Dict[str, int]:
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
