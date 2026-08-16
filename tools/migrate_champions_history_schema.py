"""Migrate legacy Champions history aggregates to the current schema.

The incremental updater expects per-regulation placement fields. Older
history snapshots can lack those fields, so normalize them before every
incremental sync. The migration is idempotent and only writes the file when
something actually changes.
"""

from __future__ import annotations

import json
from pathlib import Path

HISTORY_PATH = Path("champions_meta_history.json")

REGULATION_DEFAULTS = {
    "appearances": 0,
    "wins": 0,
    "losses": 0,
    "draws": 0,
    "top_cut_count": 0,
    "placement_sum": 0.0,
    "placement_count": 0,
    "best_placement": None,
}


def migrate(path: Path = HISTORY_PATH) -> bool:
    if not path.exists():
        raise FileNotFoundError(f"History file not found: {path}")

    with path.open("r", encoding="utf-8") as handle:
        report = json.load(handle)

    if not isinstance(report, dict):
        raise ValueError("Champions history must contain a JSON object")

    changed = False
    pokemon = report.get("pokemon") or {}
    if not isinstance(pokemon, dict):
        raise ValueError("Champions history 'pokemon' field must be an object")

    for stats in pokemon.values():
        if not isinstance(stats, dict):
            continue
        regulation_metrics = stats.setdefault("regulation_metrics", {})
        if not isinstance(regulation_metrics, dict):
            stats["regulation_metrics"] = {}
            regulation_metrics = stats["regulation_metrics"]
            changed = True

        for regulation_stats in regulation_metrics.values():
            if not isinstance(regulation_stats, dict):
                continue
            for field, default in REGULATION_DEFAULTS.items():
                if field not in regulation_stats:
                    regulation_stats[field] = default
                    changed = True

    if changed:
        with path.open("w", encoding="utf-8") as handle:
            json.dump(report, handle, indent=2, ensure_ascii=False)
            handle.write("\n")
        print(f"Migrated legacy Champions history schema in {path}")
    else:
        print("Champions history schema already up to date.")

    return changed


if __name__ == "__main__":
    migrate()
