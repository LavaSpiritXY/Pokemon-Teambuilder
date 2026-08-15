from pathlib import Path

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
