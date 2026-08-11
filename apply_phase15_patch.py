"""Apply Phase 15 Champions Meta Profile UI changes to app.py."""

from pathlib import Path

APP = Path(__file__).with_name("app.py")

IMPORT_ANCHOR = "import pandas as pd\n"
IMPORT_INSERT = '''
try:
    from champions_integration import get_champions_profile
except ImportError:
    get_champions_profile = None
'''

FUNCTION_ANCHOR = "# -----------------------------------------------------------------------------\n# 4. INITIALIZE SESSION STATE\n# -----------------------------------------------------------------------------\n"
FUNCTION_INSERT = '''# -----------------------------------------------------------------------------
# Phase 15: Champions tournament profile display
# -----------------------------------------------------------------------------
def render_champions_tournament_profile(pokemon_name):
    """Render tournament statistics without changing existing app scoring."""
    if get_champions_profile is None:
        return

    try:
        profile = get_champions_profile(pokemon_name)
    except Exception:
        return

    if not profile.get("available"):
        return

    appearances = int(profile.get("appearances") or 0)
    wins = int(profile.get("wins") or 0)
    losses = int(profile.get("losses") or 0)
    win_rate = profile.get("win_rate")
    top_cut_rate = profile.get("top_cut_rate")
    recent_win_rate = profile.get("recent_win_rate")
    partners = profile.get("partners") or []

    with strlit.expander("🏆 Champions Tournament Profile", expanded=True):
        strlit.caption("Historical Champions tournament data. This display does not alter the existing Strategizer score.")
        cols = strlit.columns(4)
        cols[0].metric("Team Appearances", f"{appearances:,}")
        cols[1].metric("Win Rate", f"{float(win_rate) * 100:.1f}%" if win_rate is not None else "N/A")
        cols[2].metric("Top-Cut Rate", f"{float(top_cut_rate) * 100:.1f}%" if top_cut_rate is not None else "N/A")
        cols[3].metric("Recent Win Rate", f"{float(recent_win_rate) * 100:.1f}%" if recent_win_rate is not None else "N/A")
        strlit.caption(f"Tournament game record: {wins:,} wins · {losses:,} losses")

        if partners:
            strlit.markdown("**Most common tournament partners**")
            partner_rows = []
            for partner in partners[:5]:
                partner_name = partner.get("pokemon")
                if not partner_name:
                    continue
                partner_rows.append({
                    "Partner": display_name_for_species_key(partner_name) or partner_name,
                    "Teams Together": int(partner.get("teams_together") or 0),
                    "Shared Win Rate": f"{float(partner.get('shared_win_rate') or 0) * 100:.1f}%",
                })
            if partner_rows:
                strlit.dataframe(partner_rows, hide_index=True, use_container_width=True)
        else:
            strlit.caption("No tournament partner data available.")

'''

CALL_ANCHOR = '''            if not meta:
                meta = {"tier": "Unknown", "viability": "0 / 100", "teammates": [], "counters": [], "speed_tier": "N/A", "momentum_rating": "N/A", "hazard_utility": "N/A", "offensive_profile": "N/A"}

'''
CALL_INSERT = CALL_ANCHOR + '''            render_champions_tournament_profile(slot_name)

'''


def replace_once(text: str, anchor: str, replacement: str, label: str) -> str:
    count = text.count(anchor)
    if count != 1:
        raise RuntimeError(f"Phase 15 patch anchor '{label}' expected once, found {count}.")
    return text.replace(anchor, replacement, 1)


def main() -> None:
    if not APP.exists():
        raise SystemExit(f"Could not find {APP}")

    text = APP.read_text(encoding="utf-8")
    if "def render_champions_tournament_profile(" in text:
        raise SystemExit("Phase 15 already appears to be applied; no changes made.")

    text = replace_once(text, IMPORT_ANCHOR, IMPORT_ANCHOR + IMPORT_INSERT, "integration import")
    text = replace_once(text, FUNCTION_ANCHOR, FUNCTION_INSERT + FUNCTION_ANCHOR, "UI function")
    text = replace_once(text, CALL_ANCHOR, CALL_INSERT, "UI call")

    APP.write_text(text, encoding="utf-8")
    print("Phase 15 patch applied successfully to app.py")
    print("Existing calculate_meta_viability scoring was not modified.")


if __name__ == "__main__":
    main()
