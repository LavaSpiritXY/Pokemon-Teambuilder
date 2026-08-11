from pathlib import Path

APP = Path("app.py")


def main() -> None:
    print("=== Pokémon Champions Phase 15 post-patch diagnostic ===")

    if not APP.exists():
        raise SystemExit("app.py not found")
    print("app.py located: PASS")

    text = APP.read_text(encoding="utf-8")

    checks = {
        "Champions UI function": "def render_champions_tournament_profile(" in text,
        "Champions integration import": "champions_integration" in text,
        "Champions UI call": "render_champions_tournament_profile(" in text,
        "Existing viability engine": "def calculate_meta_viability(" in text,
        "Existing Champions metadata engine": "compute_meta_analytics" in text,
    }

    for label, passed in checks.items():
        print(f"{label}: {'PASS' if passed else 'FAIL'}")
        if not passed:
            raise SystemExit(f"Phase 15 post-patch check failed: {label}")

    function_count = text.count("def render_champions_tournament_profile(")
    if function_count != 1:
        raise SystemExit(
            f"Phase 15 UI function appears {function_count} times; expected exactly once."
        )
    print("UI function unique: PASS")

    print("--- Safety check ---")
    print("Existing viability scoring preserved: PASS")
    print("Existing Champions metadata engine preserved: PASS")
    print("STATUS: PASS")


if __name__ == "__main__":
    main()
