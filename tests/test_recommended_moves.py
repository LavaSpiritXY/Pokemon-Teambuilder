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
