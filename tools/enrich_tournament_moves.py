"""Rebuild tournament move usage in champions_meta_history.json from cached events."""
from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from champions.tournament_move_history import enrich_history_with_tournament_moves

HISTORY_PATH = REPO_ROOT / "champions_meta_history.json"
CACHE_DIR = REPO_ROOT / "champions_cache"


def main() -> None:
    changed = enrich_history_with_tournament_moves(
        history_path=HISTORY_PATH,
        cache_dir=CACHE_DIR,
    )
    print(
        "Tournament move enrichment: "
        + ("history updated." if changed else "no changes needed.")
    )


if __name__ == "__main__":
    main()
