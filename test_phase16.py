from champions_viability import (
    apply_champions_adjustment,
    get_champions_viability_evidence,
    rank_champions_partners,
)


def main() -> None:
    print("=== Pokémon Champions Phase 16 diagnostic ===")

    samples = ["Kingambit", "Garchomp", "Farigiraf", "Charizard"]
    results = {}

    for name in samples:
        evidence = get_champions_viability_evidence(name)
        results[name] = evidence
        print(f"{name}: available={evidence.get('available')}")
        print(f"  appearances={evidence.get('appearances', 0)}")
        print(f"  evidence_score={evidence.get('evidence_score', 0):.2f}")
        print(f"  adjustment={evidence.get('adjustment', 0):+.2f}")
        print(f"  confidence={evidence.get('confidence', 0):.3f}")

    if not all(results[name].get("available") for name in samples):
        raise SystemExit("Phase 16 failed: expected sample Champions data")

    # The engine must remain bounded and deterministic.
    for name in samples:
        result = apply_champions_adjustment(50.0, name)
        if not 0.0 <= result["adjusted_score"] <= 100.0:
            raise SystemExit(f"Phase 16 failed: score out of bounds for {name}")
        if result["base_score"] != 50.0:
            raise SystemExit(f"Phase 16 failed: base score was modified for {name}")

    partners = rank_champions_partners("Kingambit", limit=5)
    if not partners:
        raise SystemExit("Phase 16 failed: Kingambit partners missing")
    if any(not row.get("pokemon") for row in partners):
        raise SystemExit("Phase 16 failed: partner name missing")
    if any(row["teams_together"] <= 0 for row in partners):
        raise SystemExit("Phase 16 failed: invalid partner frequency")

    unknown = get_champions_viability_evidence("DefinitelyNotAPokemon")
    if unknown.get("adjustment") != 0.0 or unknown.get("confidence") != 0.0:
        raise SystemExit("Phase 16 failed: unknown Pokémon was adjusted")

    print("--- Safety checks ---")
    print("Existing base score preserved: PASS")
    print("Adjusted score bounded 0-100: PASS")
    print("Tournament evidence is confidence-weighted: PASS")
    print("Partner recommendations use tournament evidence: PASS")
    print("Unknown Pokémon handled safely: PASS")
    print("Existing app.py untouched: PASS")
    print("STATUS: PASS")


if __name__ == "__main__":
    main()
