from pathlib import Path
import re

ROOT = Path(__file__).resolve().parent
APP = ROOT / "app.py"
PROFILE = ROOT / "champions_phase18_5.py"


def replace_once(text, pattern, replacement, label, flags=0):
    new, count = re.subn(pattern, replacement, text, count=1, flags=flags)
    if count != 1:
        raise RuntimeError(f"Phase 18.6 anchor '{label}' expected once, found {count}. No changes were made to that file.")
    return new


def patch_app():
    text = APP.read_text(encoding="utf-8")

    if "from champions_phase18_6_ui import render_dynamic_stat_training" not in text:
        text = replace_once(
            text,
            r"from champions_phase18_5 import render_champions_profile_v6\n",
            "from champions_phase18_5 import render_champions_profile_v6\nfrom champions_phase18_6_ui import render_dynamic_stat_training\n",
            "Phase 18.6 UI import",
        )

    # Remove the old static SP widget block. The new renderer owns the controls,
    # the 32-per-stat cap, and the 66-total cap.
    old_sp = re.compile(
        r"            strlit\.markdown\(\"##### 📊 Champions SP Allocation\"\)\n"
        r".*?"
        r"            strlit\.caption\(f\"Champions SP: \{sum\(current_sp\.values\(\)\)\}/66 total · maximum 32 per stat\"\)\n",
        re.S,
    )
    text, sp_count = old_sp.subn("", text, count=1)
    if sp_count == 0 and "stat_sp_slider_" not in text:
        raise RuntimeError("Could not locate the old Champions SP allocation block in app.py. No app.py changes were written.")

    # The old base-stat helper was removed during Phase 18.5. Replace its stale
    # call with the Phase 18.6 dynamic chart/control renderer.
    stale = re.compile(r"            render_base_stats_bubble\(mon_data\.get\(\"stats\"\)\)\n")
    if stale.search(text):
        text = stale.sub(
            "            render_dynamic_stat_training(\n"
            "                slot_index=i,\n"
            "                pokemon_name=slot_name,\n"
            "                base_stats=mon_data.get(\"stats\"),\n"
            "                nature=slot.get(\"nature\", \"Hardy\"),\n"
            "                sprite_url=get_mini_sprite_url(slot_name),\n"
            "                moves=slot.get(\"moves\") or [],\n"
            "            )\n",
            text,
            count=1,
        )
    elif "render_dynamic_stat_training(" not in text:
        raise RuntimeError("Could not locate the stale base-stat renderer call in app.py. No app.py changes were written.")

    # Make slot tabs remember the selected Pokémon by name.
    old_tabs = 'tabs = strlit.tabs([f"Slot {i+1}" for i in range(6)] + ["📊 Team Overview"])'
    new_tabs = (
        'tab_labels = []\n'
        'for _tab_i in range(6):\n'
        '    _tab_slot = strlit.session_state.team_slots.get(_tab_i, {})\n'
        '    _tab_name = _tab_slot.get("name") or "Empty"\n'
        '    tab_labels.append(f"Slot {_tab_i + 1} · {_tab_name}")\n'
        'tabs = strlit.tabs(tab_labels + ["📊 Team Overview"])'
    )
    if old_tabs in text:
        text = text.replace(old_tabs, new_tabs, 1)

    APP.write_text(text, encoding="utf-8")
    return sp_count


def patch_profile():
    text = PROFILE.read_text(encoding="utf-8")

    # Phase 18.5's profile renderer owns tournament/strategic information.
    # Phase 18.6 moves Base Stats + EVs into one interactive panel, so remove
    # the two old static sections from the profile renderer.
    pattern = re.compile(
        r"    st\.markdown\(\"<div class='ch185-section'>📊 Base Stats.*?"
        r"    st\.markdown\(\"</div>\", unsafe_allow_html=True\)\n"
        r"    return True",
        re.S,
    )
    if pattern.search(text):
        text = pattern.sub(
            "    st.markdown(\"</div>\", unsafe_allow_html=True)\n    return True",
            text,
            count=1,
        )
    elif "ch185-section'>📊 Base Stats" in text:
        raise RuntimeError("Phase 18.5 Base Stats section was found but could not be safely removed. No profile changes were written.")

    PROFILE.write_text(text, encoding="utf-8")


def main():
    if not APP.exists() or not PROFILE.exists():
        raise RuntimeError("Run this script from the Pokemon-Teambuilder repository root.")

    patch_app()
    patch_profile()
    print("Phase 18.6 dynamic stat training patch applied successfully.")
    print("Combined Base Stat + EV chart, dynamic sliders/text inputs, nature effects, EV caps, slot labels, and old static stat panel cleanup enabled.")


if __name__ == "__main__":
    main()
