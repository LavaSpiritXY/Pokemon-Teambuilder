from champions import team_recommendations as rec


def _mon(name, types, moves=None, attack=100, special_attack=100, abilities=None):
    return {
        "name": name,
        "types": types,
        "moves": moves or [],
        "stats": {"hp": 80, "attack": attack, "defense": 80, "special-attack": special_attack, "special-defense": 80, "speed": 90},
        "abilities": abilities or [],
        "item": "",
    }


def test_recommendation_is_improvement_driven(monkeypatch):
    team = [_mon("Charizard", ["Fire", "Flying"], ["Flamethrower", "Protect"])]

    monkeypatch.setattr(rec, "_candidate_shortlist", lambda active_names, limit=36: ["Rotom Wash", "Garchomp"])
    monkeypatch.setattr(rec, "load_champions_history", lambda: {"active_regulation": "M-B", "pokemon": {}})
    monkeypatch.setattr(rec, "get_tournament_partners", lambda *args, **kwargs: [])
    monkeypatch.setattr(rec, "fetch_pokemon_details_batch", lambda names, max_workers=12: {
        "Rotom Wash": _mon("Rotom Wash", ["Electric", "Water"], ["Thunderbolt", "Protect"], special_attack=110),
        "Garchomp": _mon("Garchomp", ["Dragon", "Ground"], ["Earthquake", "Protect"], attack=120),
    })

    results = rec.recommend_team_additions(team, top_n=2, candidate_limit=2)

    assert results
    assert results[0]["name"] in {"Rotom Wash", "Garchomp"}
    assert "team_delta" in results[0]
    assert "reasons" in results[0]


def test_full_team_has_no_addition_recommendations():
    team = [_mon(f"Mon{i}", ["Normal"]) for i in range(6)]
    assert rec.recommend_team_additions(team) == []
