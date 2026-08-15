"""Discover and incrementally sync Pokémon Champions tournament history.

This is the orchestration layer for the historical pipeline:

1. Discover recent VGC tournaments from Limitless.
2. Detect Champions regulations dynamically (M-A, M-B, M-C, ...).
3. Merge newly discovered event IDs into champions_event_ids.json.
4. Reuse the resumable event cache so already-downloaded tournaments are skipped.
5. Rebuild champions_meta_history.json from the complete local cache.

The script is safe to run repeatedly. It does not need a manually maintained
list of new tournaments or a hard-coded list of future regulations.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Set

from champions.historical_ingestion import process_event_ids
from champions.limitless_data import (
    CHAMPIONS_REGULATIONS,
    get_limitless_tournament_details,
    list_limitless_tournaments,
    load_limitless_event_data,
)
from champions_aggregation_v2 import aggregate


DEFAULT_EVENT_IDS = Path("champions_event_ids.json")
DEFAULT_CACHE_DIR = Path("champions_cache")
DEFAULT_HISTORY = Path("champions_meta_history.json")
DEFAULT_DISCOVERY_PAGES = 10
DEFAULT_PAGE_SIZE = 100

# Champions regulations currently use the M-X naming family. Keeping this as
# a pattern rather than a fixed set means future regulations are discovered
# automatically.
_REGULATION_PATTERN = re.compile(
    r"\b(?:REG(?:ULATION)?[\s_-]*)?(M-[A-Z0-9]+)\b",
    flags=re.IGNORECASE,
)


def _normalise_regulation(value: Any) -> Optional[str]:
    text = str(value or "").strip().upper()
    if not text:
        return None

    match = _REGULATION_PATTERN.search(text)
    if not match:
        return None

    return match.group(1).upper()


def detect_champions_regulation(tournament: Dict[str, Any]) -> Optional[str]:
    """Detect a Champions regulation from a tournament summary/details row."""
    regulation = _normalise_regulation(tournament.get("format"))
    if regulation:
        return regulation

    regulation = _normalise_regulation(tournament.get("name"))
    if regulation:
        return regulation

    return None


def discover_champions_event_ids(
    *,
    max_pages: int = DEFAULT_DISCOVERY_PAGES,
    page_size: int = DEFAULT_PAGE_SIZE,
) -> Dict[str, Any]:
    """Discover Champions tournament IDs without a manually maintained list."""
    if max_pages < 1:
        raise ValueError("max_pages must be at least 1")
    if page_size < 1 or page_size > 100:
        raise ValueError("page_size must be between 1 and 100")

    event_ids: List[str] = []
    regulations: Set[str] = set()
    seen: Set[str] = set()
    scanned = 0

    for page in range(1, max_pages + 1):
        tournaments = list_limitless_tournaments(page=page, limit=page_size)
        if not tournaments:
            break

        scanned += len(tournaments)

        for tournament in tournaments:
            event_id = str(tournament.get("id") or "").strip()
            if not event_id:
                continue

            regulation = detect_champions_regulation(tournament)

            # Limitless occasionally exposes Champions tournaments as CUSTOM.
            # Only make a details request for those ambiguous rows; ordinary
            # VGC tournaments are discarded without an extra request.
            if regulation is None and str(tournament.get("format") or "").upper() == "CUSTOM":
                try:
                    details = get_limitless_tournament_details(event_id)
                except Exception as exc:
                    print(f"WARNING: could not inspect CUSTOM event {event_id}: {exc}")
                    continue
                regulation = detect_champions_regulation(details)
                if regulation is None:
                    regulation = detect_champions_regulation(
                        {**tournament, **details}
                    )

            if regulation is None:
                continue

            # Register newly discovered regulations for this process so
            # load_limitless_event_data accepts them without source-code edits.
            CHAMPIONS_REGULATIONS.add(regulation)
            regulations.add(regulation)

            if event_id not in seen:
                seen.add(event_id)
                event_ids.append(event_id)

        # Limitless returns pages in descending recency order. A short page
        # means there is no reason to keep paging further.
        if len(tournaments) < page_size:
            break

    return {
        "event_ids": event_ids,
        "regulations": sorted(regulations),
        "scanned_tournaments": scanned,
    }


def load_existing_event_ids(path: Path) -> List[str]:
    if not path.exists():
        return []

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []

    if not isinstance(payload, list):
        return []

    output: List[str] = []
    seen: Set[str] = set()
    for item in payload:
        value = str(item.get("id") if isinstance(item, dict) else item).strip()
        if value and value not in seen:
            seen.add(value)
            output.append(value)
    return output


def write_event_ids(path: Path, event_ids: Iterable[str]) -> None:
    values = list(dict.fromkeys(str(value).strip() for value in event_ids if str(value).strip()))
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(values, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    temporary.replace(path)


def sync_history(
    *,
    event_ids_path: Path = DEFAULT_EVENT_IDS,
    cache_dir: Path = DEFAULT_CACHE_DIR,
    history_path: Path = DEFAULT_HISTORY,
    discovery_pages: int = DEFAULT_DISCOVERY_PAGES,
    page_size: int = DEFAULT_PAGE_SIZE,
    batch_size: int = 25,
    delay_seconds: float = 1.5,
) -> Dict[str, Any]:
    """Run one complete incremental synchronization pass."""
    discovery = discover_champions_event_ids(
        max_pages=discovery_pages,
        page_size=page_size,
    )

    existing = load_existing_event_ids(event_ids_path)
    merged = list(dict.fromkeys(existing + discovery["event_ids"]))
    new_ids = [event_id for event_id in merged if event_id not in set(existing)]
    write_event_ids(event_ids_path, merged)

    print("=== Champions automatic discovery ===")
    print(f"Scanned tournaments: {discovery['scanned_tournaments']}")
    print(f"Detected regulations: {', '.join(discovery['regulations']) or 'none'}")
    print(f"Known event IDs before discovery: {len(existing)}")
    print(f"New event IDs discovered: {len(new_ids)}")
    print(f"Total known event IDs: {len(merged)}")

    # process_event_ids is intentionally resumable: existing cache files are
    # skipped, unsupported events are remembered, and transient failures stop
    # safely after the configured threshold.
    ingestion = process_event_ids(
        merged,
        output_dir=cache_dir,
        batch_size=batch_size,
        delay_seconds=delay_seconds,
        full=True,
    )

    report = aggregate(cache_dir)
    history_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print("=== Champions history sync complete ===")
    print(f"History events processed: {report['events_processed']}")
    print(f"Pokémon records: {len(report['pokemon'])}")
    print(f"Partner records: {sum(len(rows) for rows in report['partners'].values())}")
    print(f"Saved history: {history_path}")

    return {
        "discovery": discovery,
        "new_event_ids": len(new_ids),
        "known_event_ids": len(merged),
        "ingestion": ingestion,
        "events_processed": report["events_processed"],
        "pokemon_records": len(report["pokemon"]),
        "partner_records": sum(len(rows) for rows in report["partners"].values()),
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Automatically discover and sync Pokémon Champions tournament history."
    )
    parser.add_argument("--event-ids", type=Path, default=DEFAULT_EVENT_IDS)
    parser.add_argument("--cache", type=Path, default=DEFAULT_CACHE_DIR)
    parser.add_argument("--output", type=Path, default=DEFAULT_HISTORY)
    parser.add_argument("--discovery-pages", type=int, default=DEFAULT_DISCOVERY_PAGES)
    parser.add_argument("--page-size", type=int, default=DEFAULT_PAGE_SIZE)
    parser.add_argument("--batch-size", type=int, default=25)
    parser.add_argument("--delay", type=float, default=1.5)
    args = parser.parse_args()

    sync_history(
        event_ids_path=args.event_ids,
        cache_dir=args.cache,
        history_path=args.output,
        discovery_pages=args.discovery_pages,
        page_size=args.page_size,
        batch_size=args.batch_size,
        delay_seconds=args.delay,
    )


if __name__ == "__main__":
    main()
