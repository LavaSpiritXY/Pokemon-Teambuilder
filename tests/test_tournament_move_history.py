import json

from champions.tournament_move_history import (
    enrich_history_with_tournament_moves,
    get_tournament_move_sample_size,
    get_tournament_move_usage,
)


def test_mega_form_move_history_is_preserved_and_idempotent(tmp_path):
    history_path = tmp_path / "champions_meta_history.json"
    cache_dir = tmp_path / "champions_cache"
    cache_dir.mkdir()

    # The canonical Champions species-key layer removes the "Mega-" prefix
    # for lookup compatibility, so Mega Charizard Y is stored under
    # "charizard-y" while retaining its display_name as the exact form.
    history = {
        "schema_version": 1,
        "active_regulation": "M-B",
        "pokemon": {
            "charizard-y": {
                "display_name": "Mega Charizard Y",
                "appearances": 4,
            },
            "charizard": {
                "display_name": "Charizard",
                "appearances": 20,
            },
        },
        "partners": {},
    }
    history_path.write_text(json.dumps(history), encoding="utf-8")

    snapshot = {
        "event": {
            "id": "test-mega-event",
            "date": "2026-08-01",
            "regulation": "M-B",
        },
        "results": [
            {
                "player_name": "Player One",
                "placement": 1,
                "wins": 5,
                "losses": 0,
                "draws": 0,
            }
        ],
        "teams": [
            {
                "player_name": "Player One",
                "pokemon": ["Mega Charizard Y", "Garchomp"],
                "raw_decklist": {
                    "pokemon": [
                        {
                            "name": "Mega Charizard Y",
                            "moves": ["Heat Wave", "Solar Beam", "Protect", "Tailwind"],
                        },
                        {
                            "name": "Garchomp",
                            "moves": ["Earthquake"],
                        },
                    ]
                },
            }
        ],
    }
    (cache_dir / "test-mega-event.json").write_text(
        json.dumps(snapshot),
        encoding="utf-8",
    )

    assert enrich_history_with_tournament_moves(
        history_path=history_path,
        cache_dir=cache_dir,
    ) is True

    usage = get_tournament_move_usage(
        "Mega Charizard Y",
        history_path=history_path,
    )
    assert usage
    assert usage["Heat Wave"] == 1.0
    assert usage["Solar Beam"] == 1.0
    assert usage["Protect"] == 1.0
    assert usage["Tailwind"] == 1.0
    assert get_tournament_move_sample_size(
        "Mega Charizard Y",
        history_path=history_path,
    ) == 1

    # Exact form data must not leak into the base species record.
    assert get_tournament_move_usage(
        "Charizard",
        history_path=history_path,
    ) == {}

    # Re-running against the same cached event must be idempotent.
    assert enrich_history_with_tournament_moves(
        history_path=history_path,
        cache_dir=cache_dir,
    ) is False
