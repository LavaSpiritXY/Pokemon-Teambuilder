import json
from pathlib import Path

from champions.incremental_history import incremental_update


def _write_history(path: Path) -> None:
    path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "generated_at": "2026-08-10T00:00:00+00:00",
                "reference_date": "2026-08-10T00:00:00+00:00",
                "recency_half_life_days": 45.0,
                "events_processed": 10,
                "regulations": {"M-B": 10},
                "pokemon": {
                    "pikachu": {
                        "appearances": 10,
                        "wins": 20,
                        "losses": 10,
                        "draws": 0,
                        "weighted_appearances": 5.0,
                        "weighted_wins": 10.0,
                        "weighted_losses": 5.0,
                        "top_cut_count": 2,
                        "weighted_top_cut": 1.0,
                        "placement_sum": 100.0,
                        "placement_count": 10,
                        "best_placement": 1.0,
                        "regulations": {"M-B": 10},
                        "display_name": "Pikachu",
                    }
                },
                "partners": {
                    "pikachu": [
                        {
                            "pokemon": "charizard",
                            "teams_together": 4,
                            "shared_wins": 8,
                            "shared_losses": 2,
                            "weighted_teams_together": 2.0,
                            "weighted_wins": 4.0,
                            "weighted_losses": 1.0,
                            "shared_win_rate": 0.8,
                        }
                    ]
                },
            }
        ),
        encoding="utf-8",
    )


def _write_event(path: Path) -> None:
    path.write_text(
        json.dumps(
            {
                "event": {
                    "regulation": "M-B",
                    "start_date": "2026-08-11T00:00:00Z",
                },
                "results": [
                    {
                        "player_name": "Alice",
                        "wins": 3,
                        "losses": 1,
                        "draws": 0,
                        "placement": 2,
                        "top_cut": True,
                    }
                ],
                "teams": [
                    {
                        "player_name": "Alice",
                        "pokemon": ["Pikachu", "Charizard"],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )


def test_incremental_update_merges_new_events(tmp_path):
    history = tmp_path / "history.json"
    cache = tmp_path / "cache"
    cache.mkdir()
    _write_history(history)
    _write_event(cache / "new-event.json")

    report = incremental_update(history, cache)

    assert report["events_processed"] == 11
    assert report["pokemon"]["pikachu"]["appearances"] == 11
    assert report["pokemon"]["pikachu"]["wins"] == 23
    assert report["pokemon"]["charizard"]["appearances"] == 1
    assert report["partners"]["pikachu"][0]["pokemon"] == "charizard"
    assert report["partners"]["pikachu"][0]["teams_together"] == 5
