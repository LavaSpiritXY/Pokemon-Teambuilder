import json
from pathlib import Path

from champions import history_data
from champions.tournament_data import calculate_tournament_metrics, get_tournament_partners


def _write_history(path: Path) -> None:
    payload = {
        "schema_version": 1,
        "events_processed": 929,
        "regulations": {"M-A": 499, "M-B": 430},
        "pokemon": {
            "garchomp": {
                "appearances": 19608,
                "wins": 53055,
                "losses": 52419,
                "top_cut_count": 2624,
                "top_cut_rate": 0.1338229294,
                "win_rate": 0.5023339046,
                "recent_usage_weight": 8646.6461,
                "recent_win_rate": 0.4975472815,
                "recent_top_cut_rate": 0.137,
                "display_name": "Garchomp",
                "regulations": {"M-A": 10417, "M-B": 9191},
            }
        },
        "partners": {
            "garchomp": [
                {
                    "pokemon": "kingambit",
                    "teams_together": 6253,
                    "shared_wins": 18224,
                    "shared_losses": 15956,
                    "shared_win_rate": 0.533,
                },
                {
                    "pokemon": "sneasler",
                    "teams_together": 5314,
                    "shared_wins": 15361,
                    "shared_losses": 13945,
                    "shared_win_rate": 0.524,
                },
            ]
        },
    }
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_history_loader_and_legacy_translation(tmp_path):
    history_path = tmp_path / "champions_meta_history.json"
    _write_history(history_path)

    history_data.load_champions_history.cache_clear()
    loaded = history_data.load_champions_history(str(history_path))
    assert loaded["events_processed"] == 929
    assert history_data.get_history_pokemon_record("Garchomp", regulation="M-B")["appearances"] == 19608
    assert history_data.get_history_pokemon_record("Garchomp", regulation="M-Z") is None

    # Point the compatibility layer at the temporary fixture rather than the
    # repository's real history file.
    history_data.load_champions_history.cache_clear()
    original_path = history_data.DEFAULT_HISTORY_PATH
    history_data.DEFAULT_HISTORY_PATH = history_path
    try:
        legacy = history_data.build_legacy_meta_db()
    finally:
        history_data.DEFAULT_HISTORY_PATH = original_path
        history_data.load_champions_history.cache_clear()

    assert legacy["garchomp"]["appearances"] == 19608
    assert legacy["garchomp"]["wins"] == 53055
    assert legacy["garchomp"]["partners"]["kingambit"] == 6253
    assert legacy["garchomp"]["partners"]["sneasler"] == 5314


def test_history_helpers_do_not_break_when_file_is_missing(tmp_path):
    missing = tmp_path / "missing.json"
    history_data.load_champions_history.cache_clear()
    assert history_data.load_champions_history(str(missing)) == {}
    assert history_data.get_history_pokemon_record("Garchomp") is None
    assert history_data.get_history_partners("Garchomp") == []


def test_existing_tournament_api_returns_normalized_metrics():
    metrics = calculate_tournament_metrics("Garchomp")
    partners = get_tournament_partners("Garchomp")

    assert isinstance(metrics, dict)
    assert 0.0 <= metrics["tournament_score"] <= 1.0
    assert isinstance(partners, list)
