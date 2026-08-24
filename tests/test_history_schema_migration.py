from pathlib import Path

from tools.migrate_champions_history_schema import REGULATION_DEFAULTS, migrate


def test_migrate_adds_required_regulation_fields(tmp_path: Path):
    history = tmp_path / "champions_meta_history.json"
    history.write_text(
        '{"pokemon": {"pikachu": {"regulation_metrics": {"M-A": {"appearances": 2}}}}}',
        encoding="utf-8",
    )

    assert migrate(history) is True

    import json

    report = json.loads(history.read_text(encoding="utf-8"))
    stats = report["pokemon"]["pikachu"]["regulation_metrics"]["M-A"]
    for field, default in REGULATION_DEFAULTS.items():
        assert field in stats
        assert stats[field] == default if field != "appearances" else stats[field] == 2


def test_migrate_is_idempotent(tmp_path: Path):
    history = tmp_path / "champions_meta_history.json"
    history.write_text(
        '{"pokemon": {"pikachu": {"regulation_metrics": {"M-A": {"appearances": 2, "wins": 1, "losses": 1, "draws": 0, "top_cut_count": 0, "placement_sum": 8.0, "placement_count": 1, "best_placement": 8}}}}}',
        encoding="utf-8",
    )

    assert migrate(history) is False
