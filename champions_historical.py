"""Phase 9/11: safe historical Champions ingestion.

Phase 11 adds a local progress manifest so historical backfills are resumable
and auditable without manually counting cache files.
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
MAX_RETRIES = 4


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


def process_event_ids(
    event_ids: Iterable[str],
    *,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    batch_size: int = DEFAULT_BATCH_SIZE,
    delay_seconds: float = DEFAULT_DELAY_SECONDS,
) -> Dict[str, int]:
    if batch_size < 1:
        raise ValueError("batch_size must be at least 1")

    output_dir.mkdir(parents=True, exist_ok=True)
    all_ids = list(dict.fromkeys(str(event_id).strip() for event_id in event_ids if str(event_id).strip()))

    selected = []
    skipped = 0
    for event_id in all_ids:
        if _event_path(output_dir, event_id).exists():
            skipped += 1
            continue
        selected.append(event_id)
        if len(selected) >= batch_size:
            break

    processed = 0
    failed = 0
    for index, event_id in enumerate(selected):
        print(f"[{index + 1}/{len(selected)}] Loading {event_id}")
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
            processed += 1
            print(f"    saved {path}")
        except Exception as exc:
            failed += 1
            print(f"    ERROR: {exc}")

        # Update the manifest after every event so an interrupted run still has
        # an accurate progress record.
        manifest = _write_manifest(output_dir, all_ids)
        print(f"    progress: {manifest['cached']}/{manifest['total_discovered']} cached")

        if index + 1 < len(selected):
            time.sleep(max(0.0, delay_seconds))

    manifest = _write_manifest(output_dir, all_ids)
    return {
        "requested": len(selected),
        "processed": processed,
        "failed": failed,
        "already_cached": skipped,
        "total_discovered": manifest["total_discovered"],
        "total_cached": manifest["cached"],
        "remaining": manifest["remaining"],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Process a small Champions event batch.")
    parser.add_argument("--event-ids", type=Path, required=True)
    parser.add_argument("--batch-size", type=int, default=DEFAULT_BATCH_SIZE)
    parser.add_argument("--delay", type=float, default=DEFAULT_DELAY_SECONDS)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args()

    event_ids = load_event_ids(args.event_ids)
    summary = process_event_ids(
        event_ids,
        output_dir=args.output,
        batch_size=args.batch_size,
        delay_seconds=args.delay,
    )

    print("--- Phase 11 batch summary ---")
    for key, value in summary.items():
        print(f"{key}: {value}")


if __name__ == "__main__":
    main()
