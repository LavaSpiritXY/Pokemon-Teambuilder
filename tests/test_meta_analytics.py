import champions.meta_analytics as meta_analytics


def test_meta_analytics_passes_active_regulation_metrics_into_viability(monkeypatch):
    tournament_metrics = {
        "usage": 0.42,
        "tournament_score": 0.91,
        "win_rate": 0.88,
        "current_regulation": "M-C",
        "current_regulation_win_rate": 0.88,
        "current_regulation_top_cut_rate": 0.31,
    }
    captured = {}

    monkeypatch.setattr(
        meta_analytics,
        "fetch_pokemon_details",
        lambda name: {
            "types": ["Electric"],
            "stats": {
                "attack": 80,
                "special-attack": 120,
                "speed": 100,
            },
            "abilities": ["Static"],
            "moves": [],
        },
    )
    monkeypatch.setattr(
        meta_analytics,
        "calculate_tournament_metrics",
        lambda name: tournament_metrics,
    )
    monkeypatch.setattr(
        meta_analytics,
        "get_tournament_partners",
        lambda name, top_n=10: [],
    )
    monkeypatch.setattr(
        meta_analytics,
        "_candidate_names",
        lambda name: [],
    )
    monkeypatch.setattr(
        meta_analytics,
        "infer_slot_role",
        lambda data, fetcher: "Special Attacker",
    )

    def fake_viability(pokemon_data, tournament_metrics=None, **kwargs):
        captured["metrics"] = tournament_metrics
        return {
            "viability_index": 91,
            "tier_display": "S-Tier / Elite Meta Threat",
            "recommended_role": "Special Attacker",
            "archetypes_detected": [],
        }

    monkeypatch.setattr(meta_analytics, "calculate_meta_viability", fake_viability)

    meta_analytics.compute_meta_analytics.clear()
    profile = meta_analytics.compute_meta_analytics("Pikachu")

    assert captured["metrics"] is tournament_metrics
    assert captured["metrics"]["current_regulation"] == "M-C"
    assert captured["metrics"]["current_regulation_win_rate"] == 0.88
    assert captured["metrics"]["current_regulation_top_cut_rate"] == 0.31
    assert profile["viability"] == "91 / 100"
