from datetime import date
import json
from pathlib import Path

from champions.history_data import get_history_metrics, load_champions_history
from tools import sync_champions_history


def _write_history(path: Path) -> None:
    payload = {
        "pokemon": {
            "pikachu": {
                "display_name": "Pikachu",
                "appearances": 11,
                "wins": 5,
                "losses": 6,
                "top_cut_count": 2,
                "win_rate": 5 / 11,
                "top_cut_rate": 2 / 11,
                "recent_usage_weight": 1.0,
                "recent_win_rate": 5 / 11,
                "recent_top_cut_rate": 2 / 11,
                "regulations": {"M-B": 10, "M-C": 1},
                "regulation_metrics": {
                    "M-B": {"win_rate": 0.20, "top_cut_rate": 0.10},
                    "M-C": {"win_rate": 0.80, "top_cut_rate": 0.50},
                },
            }
        },
        "partners": {},
        "active_regulation": "M-B",
        "detected_regulations": ["M-B", "M-C"],
    }
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def test_full_sync_transition_switches_history_to_new_active_regulation(tmp_path, monkeypatch):
    history_path = tmp_path / "history.json"
    event_ids_path = tmp_path / "event_ids.json"
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()
    _write_history(history_path)
    event_ids_path.write_text("[]", encoding="utf-8")

    monkeypatch.setattr(
        sync_champions_history,
        "discover_champions_event_ids",
        lambda **kwargs: {
            "event_ids": [],
            "regulations": ["M-B", "M-C"],
            "active_regulation": "M-C",
            "scanned_tournaments": 2,
        },
    )

    result = sync_champions_history.sync_history(
        event_ids_path=event_ids_path,
        cache_dir=cache_dir,
        history_path=history_path,
    )

    assert result["discovery"]["active_regulation"] == "M-C"
    assert result["history_changed"] is True

    history = load_champions_history(str(history_path))
    assert history["active_regulation"] == "M-C"

    metrics = get_history_metrics(
        "Pikachu",
        current_regulation=history["active_regulation"],
    )
    assert metrics["current"]["regulation"] == "M-C"
    assert metrics["current"]["win_rate"] == 0.80
    assert metrics["current"]["top_cut_rate"] == 0.50
