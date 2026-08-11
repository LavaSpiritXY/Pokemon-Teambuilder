from pathlib import Path


def main() -> None:
    print("=== Pokémon Champions Phase 18.3 UI diagnostic ===")
    assert Path("app.py").exists()
    assert Path("champions_phase18_3_ui.py").exists()
    assert Path("apply_phase18_3_ui.py").exists()
    text = Path("app.py").read_text(encoding="utf-8")
    assert "render_champions_profile_v5" not in text, "UI patch should be applied locally before this test"
    print("Phase 18.3 UI assets: PASS")
    print("STATUS: READY_TO_APPLY")


if __name__ == "__main__":
    main()
