from champions_meta import ChampionsMetaStore, _candidate_keys


def test_mega_form_candidates_include_canonical_species_key():
    candidates = _candidate_keys("Mega Charizard Y")
    assert candidates[0] == "mega charizard y"
    assert "charizard-y" in candidates
    assert "charizard" in candidates


def test_mega_form_prefers_exact_canonical_record(tmp_path):
    history_path = tmp_path / "champions_meta_history.json"
    history_path.write_text(
        '{"pokemon": {'
        '"charizard-y": {"display_name": "Mega Charizard Y", "move_sample_size": 42},'
        '"charizard": {"display_name": "Charizard", "move_sample_size": 99}'
        '}, "partners": {}}',
        encoding="utf-8",
    )

    store = ChampionsMetaStore(history_path)
    record = store.get("Mega Charizard Y")

    assert record is not None
    assert record["display_name"] == "Mega Charizard Y"
    assert record["move_sample_size"] == 42
