"""Phase 8 rate-limit-safe tournament discovery.

This helper deliberately bypasses the old regulation-filter path in
champions_data.py, because that path makes a /details request for every row.
Discovery should only hit the cheap tournament-list endpoint.  Detailed data
is fetched later for one event at a time.
"""

from __future__ import annotations

import re
import time
from typing import Any, Dict, Iterable, List, Optional, Tuple

import requests

from champions_data import (
    CHAMPIONS_REGULATIONS,
    LIMITLESS_API_BASE_URL,
    get_limitless_tournament_details,
)

MAX_429_RETRIES = 4
MAX_429_SLEEP_SECONDS = 30
USER_AGENT = (
    "Pokemon-Teambuilder/ChampionsData "
    "(+https://github.com/LavaSpiritXY/Pokemon-Teambuilder)"
)


def _get_json(url: str) -> Any:
    headers = {"User-Agent": USER_AGENT, "Accept": "application/json"}
    last_response: Optional[requests.Response] = None

    for attempt in range(MAX_429_RETRIES + 1):
        response = requests.get(url, headers=headers, timeout=20)
        if response.status_code != 429:
            response.raise_for_status()
            return response.json()

        last_response = response
        if attempt >= MAX_429_RETRIES:
            break

        retry_after = response.headers.get("Retry-After")
        try:
            delay = float(retry_after) if retry_after else 2 ** attempt
        except ValueError:
            delay = 2 ** attempt
        time.sleep(max(1.0, min(delay, MAX_429_SLEEP_SECONDS)))

    raise requests.HTTPError(
        f"429 Too Many Requests after {MAX_429_RETRIES + 1} attempts: {url}",
        response=last_response,
    )


def list_vgc_page(page: int, limit: int = 100) -> List[Dict[str, Any]]:
    url = (
        f"{LIMITLESS_API_BASE_URL}/tournaments"
        f"?game=VGC&page={page}&limit={limit}"
    )
    payload = _get_json(url)
    if not isinstance(payload, list):
        raise ValueError("Limitless tournament listing returned a non-list payload.")
    return [row for row in payload if isinstance(row, dict)]


def _listed_regulation(row: Dict[str, Any]) -> str:
    for key in ("format", "regulation", "ruleset"):
        value = str(row.get(key) or "").strip()
        if value in CHAMPIONS_REGULATIONS:
            return value

    # Some listing names include the regulation even when the structured
    # format field is omitted, e.g. "(Reg M-B)". This is only a discovery
    # fallback; the event details are still validated before import.
    name = str(row.get("name") or "")
    match = re.search(r"\bReg\s+(M-[AB])\b", name, re.IGNORECASE)
    return match.group(1).upper() if match else ""


def discover_champions_tournaments(
    *,
    regulations: Iterable[str] = CHAMPIONS_REGULATIONS,
    page_limit: int = 100,
    max_pages: int = 100,
) -> List[Dict[str, Any]]:
    wanted = set(regulations)
    if not wanted.issubset(CHAMPIONS_REGULATIONS):
        raise ValueError(f"Unsupported Champions regulations: {sorted(wanted - CHAMPIONS_REGULATIONS)}")

    found: Dict[str, Dict[str, Any]] = {}

    for page in range(1, max_pages + 1):
        rows = list_vgc_page(page, page_limit)
        if not rows:
            break

        for row in rows:
            event_id = str(row.get("id") or "").strip()
            regulation = _listed_regulation(row)
            if event_id and regulation in wanted:
                found[event_id] = {**row, "format": regulation}

        if len(rows) < page_limit:
            # One short page is normally the end of the listing. We stop here
            # rather than generating unnecessary requests against the source.
            break

    return list(found.values())


def extract_exact_top_cut_size(details: Dict[str, Any]) -> Optional[int]:
    phases = details.get("phases")
    if not isinstance(phases, list):
        return None

    candidates: List[int] = []
    for phase in phases:
        if not isinstance(phase, dict):
            continue
        for key in (
            "topCut", "top_cut", "cut", "cutSize", "cut_size",
            "eliminationSize", "elimination_size",
        ):
            try:
                value = int(phase.get(key))
            except (TypeError, ValueError):
                value = 0
            if value >= 2:
                candidates.append(value)

        label = str(phase.get("name") or phase.get("title") or "")
        match = re.search(r"top\s*(\d+)", label, re.IGNORECASE)
        if match:
            candidates.append(int(match.group(1)))

    return min(candidates) if candidates else None


def get_verified_cut(event_id: str) -> Tuple[Dict[str, Any], Optional[int]]:
    details = get_limitless_tournament_details(event_id)
    return details, extract_exact_top_cut_size(details)


def summarize_discovery(events: Iterable[Dict[str, Any]]) -> Dict[str, int]:
    summary = {regulation: 0 for regulation in sorted(CHAMPIONS_REGULATIONS)}
    completed = 0
    for event in events:
        regulation = str(event.get("format") or "").strip()
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
    "get_verified_cut",
    "summarize_discovery",
]
