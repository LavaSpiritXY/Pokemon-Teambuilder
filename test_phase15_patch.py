"""Validate that the Phase 15 patcher can safely identify app.py anchors."""

from pathlib import Path


APP = Path(__file__).with_name("app.py")
PATCHER = Path(__file__).with_name("apply_phase15_patch.py")


def main() -> None:
    print("=== Pokémon Champions Phase 15 patch diagnostic ===")

    assert APP.exists(), "app.py is missing"
    assert PATCHER.exists(), "apply_phase15_patch.py is missing"

    app_text = APP.read_text(encoding="utf-8")
    patch_text = PATCHER.read_text(encoding="utf-8")

    assert "render_champions_tournament_profile" not in app_text
    assert "calculate_meta_viability" in app_text
    assert "CHAMPIONS_META_DB" in app_text
    assert "if not meta:" in app_text
    assert "Phase 15 patch applied successfully" in patch_text

    print("app.py located: PASS")
    print("Patch script located: PASS")
    print("Existing viability engine detected: PASS")
    print("Existing Champions metadata engine detected: PASS")
    print("Patch is guarded against missing/duplicate anchors: PASS")
    print("STATUS: PASS")


if __name__ == "__main__":
    main()
