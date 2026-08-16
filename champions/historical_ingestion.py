"""Safe, resumable historical Pokémon Champions tournament ingestion.

Supported tournaments are downloaded and cached as individual JSON files.

Tournaments that are known to be outside the supported Champions formats are
recorded in the manifest as skipped, so they are not retried on later runs.

Transient HTTP failures are retried with exponential backoff.
"""

from __future__ import annotations

import argparse
import json
import time
from dataclasses import asdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Set

import requests

from champions.limitless_data import load_limitless_event_data


DEFAULT_OUTPUT_DIR = Path("champions_cache")
DEFAULT_MANIFEST = DEFAULT_OUTPUT_DIR / "manifest.json"

DEFAULT_BATCH_SIZE = 10
DEFAULT_DELAY_SECONDS = 1.5
DEFAULT_MAX_CONSECUTIVE_FAILURES = 5

MAX_RETRIES = 5


def _request_with_backoff(loader, *, label: str) -> Any:
    """Run a request with bounded exponential backoff for transient errors."""
    delay = DEFAULT_DELAY_SECONDS

    for attempt in range(MAX_RETRIES + 1):
        try:
            return loader()

        except requests.HTTPError as exc:
            status = exc.response.status_code if exc.response is not None else None

            if status not in {429, 500, 502, 503, 504}:
                raise

            if attempt >= MAX_RETRIES:
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
                f"{label}: HTTP {status}; "
                f"retrying in {sleep_for:.1f}s"
            )

            time.sleep(sleep_for)
            delay = min(delay * 2.0, 20.0)


def _event_path(output_dir: Path, event_id: str) -> Path:
    """Return the cache path for an event ID."""
    safe_id = "".join(
        ch for ch in str(event_id)
        if ch.isalnum() or ch in "-_"
    )

    return output_dir / f"{safe_id}.json"


def _serialize_event(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Convert the normalized event payload into JSON-safe dictionaries."""
    return {
        "event": asdict(payload["event"]),
        "results": [
            asdict(result)
            for result in payload["results"]
        ],
        "teams": [
            asdict(team)
            for team in payload["teams"]
        ],
    }


def load_event_ids(path: Path) -> List[str]:
    """Load unique tournament IDs from a JSON list."""
    raw = json.loads(path.read_text(encoding="utf-8"))

    if not isinstance(raw, list):
        raise ValueError("Event ID file must contain a JSON list.")

    ids: List[str] = []
    seen: Set[str] = set()

    for item in raw:
        event_id = item.get("id") if isinstance(item, dict) else item

        if event_id is None:
            continue

        value = str(event_id).strip()

        if value and value not in seen:
            seen.add(value)
            ids.append(value)

    return ids


def _load_manifest(output_dir: Path) -> Dict[str, Any]:
    """Load the existing progress manifest, if present."""
    path = output_dir / "manifest.json"

    if not path.exists():
        return {
            "total_discovered": 0,
            "cached": 0,
            "skipped": 0,
            "remaining": 0,
            "cached_event_ids": [],
            "skipped_event_ids": [],
        }

    try:
        manifest = json.loads(
            path.read_text(encoding="utf-8")
        )
    except (OSError, json.JSONDecodeError):
        return {
            "total_discovered": 0,
            "cached": 0,
            "skipped": 0,
            "remaining": 0,
            "cached_event_ids": [],
            "skipped_event_ids": [],
        }

    if not isinstance(manifest, dict):
        return {
            "total_discovered": 0,
            "cached": 0,
            "skipped": 0,
            "remaining": 0,
            "cached_event_ids": [],
            "skipped_event_ids": [],
        }

    skipped = manifest.get("skipped_event_ids", [])

    if not isinstance(skipped, list):
        skipped = []

    manifest["skipped_event_ids"] = [
        str(event_id)
        for event_id in skipped
        if str(event_id).strip()
    ]

    return manifest


def _write_manifest(
    output_dir: Path,
    event_ids: List[str],
    skipped_event_ids: Iterable[str] = (),
) -> Dict[str, Any]:
    """Write an atomic progress manifest."""
    skipped_set = {
        str(event_id).strip()
        for event_id in skipped_event_ids
        if str(event_id).strip()
    }

    cached_ids = [
        event_id
        for event_id in event_ids
        if _event_path(output_dir, event_id).exists()
    ]

    cached_set = set(cached_ids)

    skipped_set -= cached_set

    remaining_ids = [
        event_id
        for event_id in event_ids
        if event_id not in cached_set
        and event_id not in skipped_set
    ]

    manifest = {
        "total_discovered": len(event_ids),
        "cached": len(cached_ids),
        "skipped": len(skipped_set),
        "remaining": len(remaining_ids),
        "cached_event_ids": cached_ids,
        "skipped_event_ids": sorted(skipped_set),
    }

    path = output_dir / "manifest.json"
    temporary = path.with_suffix(".json.tmp")

    temporary.write_text(
        json.dumps(
            manifest,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    temporary.replace(path)

    return manifest


def _is_unsupported_format_error(exc: Exception) -> bool:
    """Return True when the importer rejected an unsupported tournament format."""
    message = str(exc)

    return (
        "uses unsupported format" in message
        or "Unsupported Champions regulation" in message
    )


def _process_one(
    event_id: str,
    *,
    output_dir: Path,
) -> str:
    """Process one event.

    Returns:
        "cached"    - successfully downloaded and cached.
        "skipped"   - known unsupported tournament format.
        "failed"    - unexpected failure.
    """
    print(f"Loading {event_id}")

    try:
        payload = _request_with_backoff(
            lambda event_id=event_id: load_limitless_event_data(event_id),
            label=event_id,
        )

        path = _event_path(output_dir, event_id)
        temporary = path.with_suffix(".json.tmp")

        temporary.write_text(
            json.dumps(
                _serialize_event(payload),
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

        temporary.replace(path)

        print(f"    saved {path}")

        return "cached"

    except Exception as exc:
        if _is_unsupported_format_error(exc):
            print(
                f"    SKIPPED: {exc}"
            )
            return "skipped"

        print(
            f"    ERROR: {exc}"
        )

        return "failed"


def process_event_ids(
    event_ids: Iterable[str],
    *,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    batch_size: int = DEFAULT_BATCH_SIZE,
    delay_seconds: float = DEFAULT_DELAY_SECONDS,
    full: bool = False,
    max_consecutive_failures: int = DEFAULT_MAX_CONSECUTIVE_FAILURES,
) -> Dict[str, int]:
    """Process tournament IDs safely and resumably."""
    if batch_size < 1:
        raise ValueError(
            "batch_size must be at least 1"
        )

    if delay_seconds < 0:
        raise ValueError(
            "delay must be non-negative"
        )

    if max_consecutive_failures < 1:
        raise ValueError(
            "max_consecutive_failures must be at least 1"
        )

    output_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    all_ids = list(
        dict.fromkeys(
            str(event_id).strip()
            for event_id in event_ids
            if str(event_id).strip()
        )
    )

    existing_manifest = _load_manifest(output_dir)

    skipped_ids: Set[str] = {
        str(event_id).strip()
        for event_id in existing_manifest.get(
            "skipped_event_ids",
            [],
        )
        if str(event_id).strip()
    }

    # Anything that already exists as a cache file is considered completed.
    cached_ids = {
        event_id
        for event_id in all_ids
        if _event_path(output_dir, event_id).exists()
    }

    # Never allow an event to be both cached and skipped.
    skipped_ids -= cached_ids

    remaining_ids = [
        event_id
        for event_id in all_ids
        if event_id not in cached_ids
        and event_id not in skipped_ids
    ]

    already_cached = len(cached_ids)
    already_skipped = len(skipped_ids)

    if full:
        selected = remaining_ids
    else:
        selected = remaining_ids[:batch_size]

    processed = 0
    skipped = 0
    failed = 0
    consecutive_failures = 0

    print(f"Discovered: {len(all_ids)}")
    print(f"Already cached: {already_cached}")
    print(f"Already skipped: {already_skipped}")
    print(f"Remaining: {len(remaining_ids)}")

    if full:
        print(
            "Full backfill enabled: "
            f"processing all {len(selected)} remaining events"
        )
    else:
        print(
            "Batch mode: "
            f"processing up to {len(selected)} events"
        )

    for index, event_id in enumerate(
        selected,
        start=1,
    ):
        print(
            f"[{index}/{len(selected)}] ",
            end="",
        )

        result = _process_one(
            event_id,
            output_dir=output_dir,
        )

        if result == "cached":
            processed += 1
            consecutive_failures = 0

        elif result == "skipped":
            skipped_ids.add(event_id)
            skipped += 1

            # A known unsupported event is not a failure.
            consecutive_failures = 0

        else:
            failed += 1
            consecutive_failures += 1

        manifest = _write_manifest(
            output_dir,
            all_ids,
            skipped_ids,
        )

        print(
            f"    progress: "
            f"{manifest['cached']}/{manifest['total_discovered']} cached; "
            f"skipped {manifest['skipped']}; "
            f"remaining {manifest['remaining']}"
        )

        if consecutive_failures >= max_consecutive_failures:
            print(
                f"Stopping safely after "
                f"{consecutive_failures} consecutive failures. "
                "Re-run the same command later to resume."
            )
            break

        if index < len(selected):
            time.sleep(delay_seconds)

    manifest = _write_manifest(
        output_dir,
        all_ids,
        skipped_ids,
    )

    return {
        "requested": len(selected),
        "processed": processed,
        "skipped": skipped,
        "failed": failed,
        "already_cached": already_cached,
        "already_skipped": already_skipped,
        "total_discovered": manifest["total_discovered"],
        "total_cached": manifest["cached"],
        "total_skipped": manifest["skipped"],
        "remaining": manifest["remaining"],
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Process Champions tournament history safely."
        )
    )

    parser.add_argument(
        "--event-ids",
        type=Path,
        required=True,
    )

    parser.add_argument(
        "--batch-size",
        type=int,
        default=DEFAULT_BATCH_SIZE,
    )

    parser.add_argument(
        "--delay",
        type=float,
        default=DEFAULT_DELAY_SECONDS,
    )

    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
    )

    parser.add_argument(
        "--full",
        action="store_true",
        help=(
            "Process all remaining events instead of "
            "only one batch."
        ),
    )

    parser.add_argument(
        "--max-consecutive-failures",
        type=int,
        default=DEFAULT_MAX_CONSECUTIVE_FAILURES,
    )

    args = parser.parse_args()

    event_ids = load_event_ids(
        args.event_ids
    )

    summary = process_event_ids(
        event_ids,
        output_dir=args.output,
        batch_size=args.batch_size,
        delay_seconds=args.delay,
        full=args.full,
        max_consecutive_failures=(
            args.max_consecutive_failures
        ),
    )

    print(
        "--- Historical backfill summary ---"
    )

    for key, value in summary.items():
        print(
            f"{key}: {value}"
        )


if __name__ == "__main__":
    main()