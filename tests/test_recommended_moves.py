from champions.recommended_moves import get_recommended_moves


def test_recommended_moves_respect_legal_learnset():
    data = {
        "types": ["Fighting", "Poison"],
        "moves": ["Close Combat", "Fake Out", "Protect"],
    }
    rows = get_recommended_moves("Sneasler", data, top_n=3)
    names = {row["move"] for row in rows}
    assert names <= set(data["moves"])


def test_recommended_moves_are_structured():
    data = {
        "types": ["Ground", "Dragon"],
        "moves": ["Earthquake", "Stomping Tantrum", "Dragon Claw"],
    }
    rows = get_recommended_moves("Garchomp", data, target_types=["Dark", "Steel"], top_n=3)
    assert rows
    required = {"move", "score", "frequency", "count", "sample_size", "confidence", "type", "reason"}
    assert required <= set(rows[0])


def test_recommended_move_scores_are_not_flat():
    data = {
        "types": ["Fighting", "Poison"],
        "moves": ["Close Combat", "Fake Out", "Protect", "Dire Claw", "Coaching", "Poison Jab"],
    }
    rows = get_recommended_moves("Sneasler", data, target_types=["Water", "Fire"], top_n=6)
    scores = [row["score"] for row in rows]
    assert len(scores) >= 3
    assert len(set(scores)) >= 3


def test_recommended_move_output_has_no_internal_selection_fields():
    data = {
        "types": ["Ground", "Dragon"],
        "moves": ["Earthquake", "Stomping Tantrum", "Dragon Claw"],
    }
    rows = get_recommended_moves("Garchomp", data, target_types=["Dark", "Steel"], top_n=3)
    assert all("_selection_score" not in row for row in rows)
