from datetime import date
from pathlib import Path

from champions.regulation import (
    get_active_regulation_from_history,
    select_active_champions_regulation,
)
from tools.sync_champions_history import (
    detect_champions_regulation,
    load_existing_event_ids,
    write_event_ids,
)


def test_detects_current_and_future_regulations():
    assert detect_champions_regulation({"format": "M-A"}) == "M-A"
    assert detect_champions_regulation({"format": "M-B"}) == "M-B"
    assert detect_champions_regulation({"format": "M-C"}) == "M-C"
    assert detect_champions_regulation({"name": "Regional Championship - Regulation M-D"}) == "M-D"


def test_ignores_non_champions_formats():
    assert detect_champions_regulation({"format": "Regulation G"}) is None
    assert detect_champions_regulation({"format": "Standard"}) is None
    assert detect_champions_regulation({"name": "Random VGC Tournament"}) is None


def test_event_id_file_round_trip(tmp_path: Path):
    path = tmp_path / "event_ids.json"
    write_event_ids(path, ["abc", "abc", "def", ""])

    assert load_existing_event_ids(path) == ["abc", "def"]


def test_active_regulation_uses_latest_completed_event():
    tournaments = [
        {"format": "M-A", "date": "2026-05-10", "completed": True},
        {"format": "M-B", "date": "2026-08-01", "completed": True},
    ]

    assert select_active_champions_regulation(
        tournaments,
        as_of=date(2026, 8, 15),
    ) == "M-B"


def test_future_regulation_does_not_become_active_early():
    tournaments = [
        {"format": "M-B", "date": "2026-08-01", "completed": True},
        {"format": "M-C", "date": "2026-09-01", "completed": False},
    ]

    assert select_active_champions_regulation(
        tournaments,
        as_of=date(2026, 8, 15),
    ) == "M-B"


def test_active_regulation_can_switch_when_new_regulation_is_active():
    tournaments = [
        {"format": "M-B", "date": "2026-08-01", "completed": True},
        {"format": "M-C", "date": "2026-09-01", "completed": True},
    ]

    assert select_active_champions_regulation(
        tournaments,
        as_of=date(2026, 9, 15),
    ) == "M-C"


def test_history_active_regulation_metadata_is_preferred_over_fallback():
    history = {"active_regulation": "M-C", "regulations": {"M-B": 430, "M-C": 1}}

    assert get_active_regulation_from_history(history, fallback="M-B") == "M-C"
    assert get_active_regulation_from_history({}, fallback="M-B") == "M-B"
