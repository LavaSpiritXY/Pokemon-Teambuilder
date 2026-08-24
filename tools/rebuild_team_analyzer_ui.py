from pathlib import Path

PATH = Path("champions/team_analyzer_ui.py")


def main() -> None:
    text = PATH.read_text(encoding="utf-8")

    # Make move cards responsive to move-name length so long names remain readable.
    old_move = '''    return (\n        '<div style="display:inline-flex;align-items:center;justify-content:space-between;gap:8px;'\n        'width:168px;min-height:44px;padding:8px 11px;margin:6px 14px 6px 0;border-radius:10px;'\n        'background:' + background + ';color:white;box-sizing:border-box;box-shadow:0 4px 10px rgba(0,0,0,0.25);vertical-align:top;">'\n        f'<span style="min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;font-weight:850;font-size:14px;line-height:1.15;">{display_name}</span>'\n        '<span style="display:flex;align-items:center;gap:4px;flex:0 0 auto;font-size:10px;font-weight:900;">'\n        f'{icon_html}<span>{str(move_type).upper()}</span></span>'\n        '</div>'\n    )'''
    new_move = '''    card_width = min(220, max(150, 104 + len(display_name) * 7))\n    return (\n        '<div style="display:inline-flex;align-items:center;justify-content:space-between;gap:8px;'\n        f'width:{card_width}px;min-height:44px;padding:8px 11px;margin:6px 14px 6px 0;border-radius:10px;'\n        'background:' + background + ';color:white;box-sizing:border-box;box-shadow:0 4px 10px rgba(0,0,0,0.25);vertical-align:top;">'\n        f'<span style="min-width:0;white-space:nowrap;font-weight:850;font-size:14px;line-height:1.15;">{display_name}</span>'\n        '<span style="display:flex;align-items:center;gap:4px;flex:0 0 auto;font-size:10px;font-weight:900;">'\n        f'{icon_html}<span>{str(move_type).upper()}</span></span>'\n        '</div>'\n    )'''
    text = text.replace(old_move, new_move, 1)

    # Make the performance bars span the usable Team Overview width, like the EV bars.
    text = text.replace('    profile_cols = st.columns(2)\n', '    profile_cols = [st.container()]\n', 1)
    old_profile_loop = '''    for index, (label, value) in enumerate(profile):\n        with profile_cols[index % 2]:\n            _score_bar(label, value, compact=True)\n'''
    new_profile_loop = '''    for label, value in profile:\n        with profile_cols[0]:\n            _score_bar(label, value, compact=False)\n'''
    text = text.replace(old_profile_loop, new_profile_loop, 1)

    # Center the overall health bar vertically without changing its horizontal placement.
    text = text.replace(
        'def _score_bar(label: str, value: float, compact: bool = False) -> None:',
        'def _score_bar(label: str, value: float, compact: bool = False, top_padding: int = 0) -> None:',
        1,
    )
    text = text.replace(
        '<div style="margin:0 0 {margin}px 0;">',
        '<div style="margin:0 0 {margin}px 0;padding-top:{top_padding}px;">',
        1,
    )
    text = text.replace(
        '_score_bar("Overall team health", result["overall_score"])',
        '_score_bar("Overall team health", result["overall_score"], top_padding=28)',
        1,
    )

    # Remove the duplicated coverage-score row and replace it with genuinely new team-composition information.
    coverage_start = text.find('    coverage_cols = st.columns(3)\n')
    field_marker = '    st.markdown("<div style=\'font-size:20px;font-weight:900;margin:16px 0 12px;color:#f0f6fc;\'>🌦️ Field Control</div>", unsafe_allow_html=True)\n'
    field_start = text.find(field_marker, coverage_start if coverage_start != -1 else 0)

    if coverage_start != -1 and field_start != -1 and coverage_start < field_start:
        snapshot_block = '''    st.markdown("<div style='font-size:20px;font-weight:900;margin:16px 0 10px;color:#f0f6fc;'>📌 Team Snapshot</div>", unsafe_allow_html=True)\n    snapshot_cols = st.columns(3)\n\n    physical_members = int(functions.get("physical_members", 0))\n    special_members = int(functions.get("special_members", 0))\n    unique_types = len(redundancy.get("type_counts", {}))\n    team_size = int(result.get("team_size", 0))\n    damage_total = max(physical_members + special_members, 1)\n    physical_pct = physical_members / damage_total * 100.0\n    special_pct = special_members / damage_total * 100.0\n\n    with snapshot_cols[0]:\n        st.markdown(\n            f\"\"\"<div style='background:rgba(18,23,35,0.72);border:1px solid rgba(255,255,255,0.10);border-radius:14px;padding:15px 16px;height:100%;box-sizing:border-box;'>\n<div style='font-size:14px;font-weight:900;color:#f0f6fc;margin-bottom:8px;'>⚔️ Damage Profile</div>\n<div style='display:flex;justify-content:space-between;font-size:13px;font-weight:800;margin-bottom:6px;'><span>Physical</span><span>{physical_members}</span></div>\n<div style='display:flex;justify-content:space-between;font-size:13px;font-weight:800;margin-bottom:8px;'><span>Special</span><span>{special_members}</span></div>\n<div style='display:flex;height:11px;border-radius:999px;overflow:hidden;background:#263241;border:1px solid #526071;'>\n<div style='width:{physical_pct:.1f}%;background:#e67e22;'></div>\n<div style='width:{special_pct:.1f}%;background:#5b8ff9;'></div>\n</div></div>\"\"\",\n            unsafe_allow_html=True,\n        )\n\n    with snapshot_cols[1]:\n        st.markdown(\n            f\"\"\"<div style='background:rgba(18,23,35,0.72);border:1px solid rgba(255,255,255,0.10);border-radius:14px;padding:15px 16px;height:100%;box-sizing:border-box;'>\n<div style='font-size:14px;font-weight:900;color:#f0f6fc;margin-bottom:8px;'>🔷 Typing Diversity</div>\n<div style='font-size:30px;font-weight:950;color:#e6edf3;line-height:1;'>{unique_types}<span style='font-size:13px;color:#8b949e;font-weight:800;'> / 18 types</span></div>\n<div style='font-size:11px;color:#8b949e;margin-top:7px;'>unique team typing represented across the six members</div>\n</div>\"\"\",\n            unsafe_allow_html=True,\n        )\n\n    with snapshot_cols[2]:\n        st.markdown(\n            f\"\"\"<div style='background:rgba(18,23,35,0.72);border:1px solid rgba(255,255,255,0.10);border-radius:14px;padding:15px 16px;height:100%;box-sizing:border-box;'>\n<div style='font-size:14px;font-weight:900;color:#f0f6fc;margin-bottom:8px;'>👥 Active Team</div>\n<div style='font-size:30px;font-weight:950;color:#e6edf3;line-height:1;'>{team_size}<span style='font-size:13px;color:#8b949e;font-weight:800;'> / 6 selected</span></div>\n<div style='height:10px;border-radius:999px;background:#263241;border:1px solid #526071;overflow:hidden;margin-top:10px;'><div style='width:{min(100, team_size / 6 * 100):.1f}%;height:100%;background:#7ac74c;border-radius:999px;'></div></div>\n</div>\"\"\",\n            unsafe_allow_html=True,\n        )\n\n'''
        text = text[:coverage_start] + snapshot_block + text[field_start:]
    else:
        raise RuntimeError("Expected coverage and field-control layout markers were not found in team_analyzer_ui.py")

    # Keep archetype details prominent in the detailed coverage drawer.
    text = text.replace(
        '            st.markdown("**🧩 Archetypes**")\n            st.caption(" · ".join(sorted(archetypes["counts"])))',
        '            st.markdown("<div style=\'font-size:17px;font-weight:900;margin-top:12px;color:#f0f6fc;\'>🧩 Archetypes</div>", unsafe_allow_html=True)\n            st.markdown("<div style=\'font-size:15px;line-height:1.7;font-weight:800;color:#e6edf3;padding:8px 0;\'>" + " · ".join(sorted(archetypes["counts"])) + "</div>", unsafe_allow_html=True)',
        1,
    )

    PATH.write_text(text, encoding="utf-8")


if __name__ == "__main__":
    main()
