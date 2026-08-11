"""Phase 9/11/11.1: safe historical Champions ingestion.

Phase 11.1 adds a resumable full-backfill mode. The downloader still uses
bounded request pacing and exponential backoff, but can now continue through
all remaining event IDs without requiring repeated manual commands.
"""

from __future__ import annotations

import argparse
import json
import time
from dataclasses import asdict
from pathlib import Path
from typing import Any, Dict, Iterable, List

import requests

from champions_data import load_limitless_event_data

DEFAULT_OUTPUT_DIR = Path("champions_cache")
DEFAULT_MANIFEST = DEFAULT_OUTPUT_DIR / "manifest.json"
DEFAULT_BATCH_SIZE = 10
DEFAULT_DELAY_SECONDS = 1.5
DEFAULT_MAX_CONSECUTIVE_FAILURES = 5
MAX_RETRIES = 5


def _request_with_backoff(loader, *, label: str) -> Any:
    delay = DEFAULT_DELAY_SECONDS
    for attempt in range(MAX_RETRIES + 1):
        try:
            return loader()
        except requests.HTTPError as exc:
            status = exc.response.status_code if exc.response is not None else None
            if status not in {429, 500, 502, 503, 504} or attempt >= MAX_RETRIES:
                raise
            retry_after = None
            if exc.response is not None:
                raw = exc.response.headers.get("Retry-After")
                try:
                    retry_after = float(raw) if raw is not None else None
                except (TypeError, ValueError):
                    retry_after = None
            # Backoff grows 1.5 -> 3 -> 6 -> 12 -> 20 seconds, unless the
            # server explicitly asks us to wait longer.
            sleep_for = max(delay, retry_after or 0.0)
            print(f"{label}: HTTP {status}; retrying in {sleep_for:.1f}s")
            time.sleep(sleep_for)
            delay = min(delay * 2.0, 20.0)


def _event_path(output_dir: Path, event_id: str) -> Path:
    safe_id = "".join(ch for ch in str(event_id) if ch.isalnum() or ch in "-_")
    return output_dir / f"{safe_id}.json"


def _serialize_event(payload: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "event": asdict(payload["event"]),
        "results": [asdict(result) for result in payload["results"]],
        "teams": [asdict(team) for team in payload["teams"]],
    }


def load_event_ids(path: Path) -> List[str]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        raise ValueError("Event ID file must contain a JSON list.")
    ids: List[str] = []
    seen = set()
    for item in raw:
        event_id = item.get("id") if isinstance(item, dict) else item
        if event_id is None:
            continue
        value = str(event_id).strip()
        if value and value not in seen:
            seen.add(value)
            ids.append(value)
    return ids


def _write_manifest(output_dir: Path, event_ids: List[str]) -> Dict[str, Any]:
    cached_ids = []
    for event_id in event_ids:
        if _event_path(output_dir, event_id).exists():
            cached_ids.append(event_id)

    manifest = {
        "total_discovered": len(event_ids),
        "cached": len(cached_ids),
        "remaining": len(event_ids) - len(cached_ids),
        "cached_event_ids": cached_ids,
    }
    path = output_dir / "manifest.json"
    temporary = path.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(path)
    return manifest


def _process_one(
    event_id: str,
    *,
    output_dir: Path,
) -> bool:
    print(f"Loading {event_id}")
    try:
        payload = _request_with_backoff(
            lambda event_id=event_id: load_limitless_event_data(event_id),
            label=event_id,
        )
        path = _event_path(output_dir, event_id)
        temporary = path.with_suffix(".json.tmp")
        temporary.write_text(
            json.dumps(_serialize_event(payload), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        temporary.replace(path)
        print(f"    saved {path}")
        return True
    except Exception as exc:
        print(f"    ERROR: {exc}")
        return False


def process_event_ids(
    event_ids: Iterable[str],
    *,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    batch_size: int = DEFAULT_BATCH_SIZE,
    delay_seconds: float = DEFAULT_DELAY_SECONDS,
    full: bool = False,
    max_consecutive_failures: int = DEFAULT_MAX_CONSECUTIVE_FAILURES,
) -> Dict[str, int]:
    if batch_size < 1:
        raise ValueError("batch_size must be at least 1")
    if delay_seconds < 0:
        raise ValueError("delay must be non-negative")
    if max_consecutive_failures < 1:
        raise ValueError("max_consecutive_failures must be at least 1")

    output_dir.mkdir(parents=True, exist_ok=True)
    all_ids = list(dict.fromkeys(str(event_id).strip() for event_id in event_ids if str(event_id).strip()))

    remaining_ids = [
        event_id for event_id in all_ids
        if not _event_path(output_dir, event_id).exists()
    ]
    already_cached = len(all_ids) - len(remaining_ids)

    # Normal mode preserves the Phase 11 behaviour: process at most one batch.
    # Full mode keeps going until every discovered ID has been attempted.
    if full:
        selected = remaining_ids
    else:
        selected = remaining_ids[:batch_size]

    processed = 0
    failed = 0
    consecutive_failures = 0

    print(f"Discovered: {len(all_ids)}")
    print(f"Already cached: {already_cached}")
    print(f"Remaining: {len(remaining_ids)}")
    if full:
        print(f"Full backfill enabled: processing all {len(selected)} remaining events")
    else:
        print(f"Batch mode: processing up to {len(selected)} events")

    for index, event_id in enumerate(selected, start=1):
        print(f"[{index}/{len(selected)}]", end=" ")
        success = _process_one(event_id, output_dir=output_dir)
        if success:
            processed += 1
            consecutive_failures = 0
        else:
            failed += 1
            consecutive_failures += 1

        manifest = _write_manifest(output_dir, all_ids)
        print(f"    progress: {manifest['cached']}/{manifest['total_discovered']} cached; remaining {manifest['remaining']}")

        if consecutive_failures >= max_consecutive_failures:
            print(
                f"Stopping safely after {consecutive_failures} consecutive failures. "
                "Re-run the same command later to resume."
            )
            break

        if index < len(selected):
            time.sleep(delay_seconds)

    manifest = _write_manifest(output_dir, all_ids)
    return {
        "requested": len(selected),
        "processed": processed,
        "failed": failed,
        "already_cached": already_cached,
        "total_discovered": manifest["total_discovered"],
        "total_cached": manifest["cached"],
        "remaining": manifest["remaining"],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Process Champions tournament history safely.")
    parser.add_argument("--event-ids", type=Path, required=True)
    parser.add_argument("--batch-size", type=int, default=DEFAULT_BATCH_SIZE)
    parser.add_argument("--delay", type=float, default=DEFAULT_DELAY_SECONDS)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument(
        "--full",
        action="store_true",
        help="Continue through every uncached event ID instead of processing one batch.",
    )
    parser.add_argument(
        "--max-consecutive-failures",
        type=int,
        default=DEFAULT_MAX_CONSECUTIVE_FAILURES,
        help="Stop safely after this many consecutive failed events.",
    )
    args = parser.parse_args()

    event_ids = load_event_ids(args.event_ids)
    summary = process_event_ids(
        event_ids,
        output_dir=args.output,
        batch_size=args.batch_size,
        delay_seconds=args.delay,
        full=args.full,
        max_consecutive_failures=args.max_consecutive_failures,
    )

    print("--- Phase 11.1 backfill summary ---")
    for key, value in summary.items():
        print(f"{key}: {value}")


if __name__ == "__main__":
    main()
