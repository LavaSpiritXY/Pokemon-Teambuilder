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

    # Insert compact coverage cards directly beneath the performance profile.
    field_marker = '    st.markdown("<div style=\'font-size:20px;font-weight:900;margin:16px 0 12px;color:#f0f6fc;\'>🌦️ Field Control</div>", unsafe_allow_html=True)\n'
    coverage_block = '''    coverage_cols = st.columns(3)\n    defensive_colour = _interpolate_colour(len(defensive["covered_types"]) / 18 * 100)\n    offensive_colour = _interpolate_colour(len(offensive["covered_types"]) / 18 * 100)\n    variety_colour = _interpolate_colour(redundancy["score"])\n    with coverage_cols[0]:\n        _coverage_count_card("Defensive Answers", "🛡️", len(defensive["covered_types"]), 18, defensive_colour, "types answered")\n    with coverage_cols[1]:\n        _coverage_count_card("Offensive Pressure", "⚔️", len(offensive["covered_types"]), 18, offensive_colour, "types hit super-effectively")\n    with coverage_cols[2]:\n        _coverage_count_card("Team Variety", "♻️", round(redundancy["score"]), 100, variety_colour, "composition diversity")\n    if defensive["uncovered_types"]:\n        st.caption("Defensive gaps")\n        _analyzer_type_chips(defensive["uncovered_types"], {t: 2.0 for t in defensive["uncovered_types"]})\n    if offensive["quad_coverage"]:\n        st.caption("4× offensive pressure")\n        _analyzer_type_chips(offensive["quad_coverage"], {t: 4.0 for t in offensive["quad_coverage"]})\n\n'''
    # Remove the existing standalone Coverage Snapshot section.
    coverage_start = text.index('    st.markdown("<div style=\'font-size:20px;font-weight:900;margin:14px 0 12px;color:#f0f6fc;\'>🔍 Coverage Snapshot</div>")') if '<div style=\'font-size:20px;font-weight:900;margin:14px 0 12px;color:#f0f6fc;\'>🔍 Coverage Snapshot</div>' in text else -1
    field_start = text.index(field_marker)
    if coverage_start != -1 and coverage_start < field_start:
        text = text[:coverage_start] + coverage_block + text[field_start:]
    else:
        text = text.replace(field_marker, coverage_block + field_marker, 1)

    # Make Field Control a balanced row with Weather and Terrain side-by-side.
    text = text.replace('    field_cols = st.columns(2)\n', '    field_cols = st.columns(2)\n', 1)

    # Keep archetype details prominent in the detailed coverage drawer.
    text = text.replace('            st.markdown("**🧩 Archetypes**")\n            st.caption(" · ".join(sorted(archetypes["counts"])))', '            st.markdown("<div style=\'font-size:17px;font-weight:900;margin-top:12px;color:#f0f6fc;\'>🧩 Archetypes</div>", unsafe_allow_html=True)\n            st.markdown("<div style=\'font-size:15px;line-height:1.7;font-weight:800;color:#e6edf3;padding:8px 0;\'>" + " · ".join(sorted(archetypes["counts"])) + "</div>", unsafe_allow_html=True)', 1)

    # Remove any remaining standalone coverage heading/card block if the earlier anchor missed it.
    text = text.replace('    st.markdown("<div style=\'font-size:20px;font-weight:900;margin:14px 0 12px;color:#f0f6fc;\'>🔍 Coverage Snapshot</div>", unsafe_allow_html=True)\n', '', 1)

    PATH.write_text(text, encoding="utf-8")


if __name__ == "__main__":
    main()
