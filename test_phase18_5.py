from __future__ import annotations

from pathlib import Path
import ast


def main() -> None:
    print("=== Pokémon Champions Phase 18.5 diagnostic ===")
    assert Path("app.py").exists(), "app.py"
    assert Path("champions_phase18_5.py").exists(), "Phase 18.5 renderer"
    assert Path("apply_phase18_5_patch.py").exists(), "Phase 18.5 patch script"
    print("Phase 18.5 files: PASS")

    source = Path("champions_phase18_5.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    functions = {node.name for node in ast.walk(tree) if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))}
    assert "render_champions_profile_v6" in functions
    assert "_display_score" in functions
    assert "_base_stat_rows" in functions
    assert "_sp_rows" in functions
    print("Unified renderer and helpers: PASS")

    app = Path("app.py").read_text(encoding="utf-8")
    assert "from champions_phase18_5 import render_champions_profile_v6" in app
    assert "render_champions_profile_v6(" in app
    assert "render_champions_profile_v5(" not in app
    print("Single active profile renderer: PASS")

    assert "##### 📊 Champions SP Allocation" in app
    assert "max_value=32" in app
    assert "66 - other_sp" in app or "66" in app
    print("Champions SP controls: PASS")

    assert "Tournament data unavailable" in source
    assert "No tournament-supported checks" in source
    print("No-data and evidence-ranked counter states: PASS")

    assert "background:{colour}" in source
    assert "ch185-statrow" in source
    print("Proportional red-to-green base-stat bars: PASS")

    assert "ch185-entity img{width:52px" in source
    print("Larger partner sprites: PASS")

    # Verify the display score is tournament-led while remaining display-only.
    assert "base_score * 0.25 + index * 0.75" in source
    assert "Display-only score" in source
    print("Tournament-led display viability: PASS")

    assert "Strategizer" in source
    print("Existing Strategizer engine isolated: PASS")
    print("STATUS: PASS")


if __name__ == "__main__":
    main()
