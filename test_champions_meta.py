"""Phase 13 validation for the isolated Champions meta interface."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from champions_meta import ChampionsMetaStore


def main() -> int:
    print("=== Pokémon Champions Phase 13 meta interface diagnostic ===")

    path = Path("champions_meta_history.json")
    if not path.exists():
        print("DATASET: not present in working tree")
        print("The interface is installed correctly, but the generated JSON is not")
        print("committed to GitHub. This is safe; run the aggregation locally first.")
        return 0

    store = ChampionsMetaStore(path)
    summary = store.summary()
    print("--- Dataset summary ---")
    for key, value in summary.items():
        print(f"{key}: {value}")

    if not summary["available"]:
        print("ERROR: dataset was not loaded")
        return 1

    required = ["kingambit", "garchomp", "farigiraf"]
    print("--- Sample lookups ---")
    for name in required:
        row = store.get(name)
        if row is None:
            print(f"{name}: NOT FOUND")
            continue
        print(
            f"{name}: appearances={row.get('appearances', 0)}, "
            f"win_rate={row.get('win_rate', 0.0):.3f}, "
            f"top_cut_rate={row.get('top_cut_rate', 0.0):.3f}, "
            f"recent_win_rate={row.get('recent_win_rate', 0.0):.3f}"
        )
        partners = store.get_partners(name, limit=3)
        print("  partners:", [p.get("pokemon") for p in partners])

    missing = store.get("this-is-not-a-pokemon")
    if missing is not None:
        print("ERROR: missing Pokémon lookup should return None")
        return 1

    print("--- Schema check ---")
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw.get("pokemon"), dict) or not isinstance(raw.get("partners"), dict):
        print("ERROR: unexpected aggregated dataset schema")
        return 1

    print("STATUS: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
