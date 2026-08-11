"""Phase 9 helper: export discovered Champions tournament IDs.

This uses the safe Phase 8 discovery layer and writes a small JSON manifest
that champions_historical.py can consume in batches. It does not download
individual event details.
"""

from __future__ import annotations

import json
from pathlib import Path

from champions_phase8 import discover_champions_tournaments

OUTPUT = Path("champions_event_ids.json")


def main() -> None:
    print("=== Exporting Champions tournament IDs ===")
    tournaments = discover_champions_tournaments()

    unique = {}
    for tournament in tournaments:
        event_id = str(tournament.get("id", "")).strip()
        if event_id:
            unique[event_id] = tournament

    rows = sorted(
        unique.values(),
        key=lambda row: str(row.get("start_date") or row.get("date") or ""),
        reverse=True,
    )

    OUTPUT.write_text(
        json.dumps(rows, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(f"Exported {len(rows)} unique tournament IDs")
    print(f"Saved to: {OUTPUT.resolve()}")
    print()
    print("Next step: run the Phase 9 historical processor with:")
    print("python champions_historical.py --event-ids champions_event_ids.json --batch-size 10")


if __name__ == "__main__":
    main()
