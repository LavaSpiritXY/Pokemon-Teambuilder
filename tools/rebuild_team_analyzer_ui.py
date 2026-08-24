from pathlib import Path

PATH = Path("champions/team_analyzer_ui.py")


def main() -> None:
    text = PATH.read_text(encoding="utf-8")

    # Make move cards comfortably readable while retaining compact dashboard density.
    text = text.replace(
        'width:118px;min-height:42px;padding:7px 9px;margin:4px 9px 5px 0;',
        'width:168px;min-height:44px;padding:8px 11px;margin:6px 14px 6px 0;',
        1,
    )
    text = text.replace('font-weight:850;font-size:13px;line-height:1.1;', 'font-weight:850;font-size:14px;line-height:1.15;', 1)
    text = text.replace('font-size:9px;font-weight:900;', 'font-size:10px;font-weight:900;', 1)

    # Remove the unhelpful implementation-note caption under the overall score.
    text = text.replace(
        '            st.caption("Score colour follows the same continuous red → orange → yellow → green scale used by EV training.")\n',
        '',
        1,
    )

    # Weather: professional pill, no emoji.
    old_weather = 'return f\'<span style="display:inline-flex;align-items:center;justify-content:center;min-width:105px;height:38px;padding:0 12px;margin:4px 9px 5px 0;border-radius:11px;background:{background};color:{text_colour};font-weight:900;font-size:13px;box-shadow:0 4px 12px rgba(0,0,0,0.22);">☁️ {display}</span>\''
    new_weather = 'return f\'<span style="display:inline-flex;align-items:center;justify-content:center;min-width:118px;height:40px;padding:0 13px;margin:6px 10px 6px 0;border-radius:12px;background:{background};color:{text_colour};font-weight:900;font-size:14px;box-shadow:0 4px 12px rgba(0,0,0,0.22);">{display}</span>\''
    text = text.replace(old_weather, new_weather, 1)

    # Terrain pill slightly larger and more prominent.
    text = text.replace(
        'min-width:140px;height:38px;padding:0 12px;margin:4px 9px 5px 0;border-radius:11px;',
        'min-width:150px;height:40px;padding:0 13px;margin:6px 10px 6px 0;border-radius:12px;',
        1,
    )
    text = text.replace('font-weight:900;font-size:13px;', 'font-weight:900;font-size:14px;', 1)

    # Roomier analyzer type bubbles.
    text = text.replace(
        'min-width:112px;height:40px;padding:0 11px;margin:5px 10px 5px 0;border-radius:11px;',
        'min-width:126px;height:42px;padding:0 12px;margin:6px 12px 7px 0;border-radius:12px;',
        1,
    )
    text = text.replace('font-weight:900;font-size:13px;box-sizing:border-box;', 'font-weight:900;font-size:14px;box-sizing:border-box;', 1)

    toolkit_start = text.index('    st.markdown("<div style=\'font-size:20px;font-weight:900;margin:14px 0 12px;color:#f0f6fc;\'>🧩 Functional Toolkit</div>", unsafe_allow_html=True)')
    coverage_start = text.index('    st.markdown("<div style=\'font-size:20px;font-weight:900;margin:14px 0 12px;color:#f0f6fc;\'>🔍 Coverage Snapshot</div>", unsafe_allow_html=True)', toolkit_start)

    rebuilt_sections = '''    st.markdown("<div style='font-size:20px;font-weight:900;margin:14px 0 12px;color:#f0f6fc;'>🧩 Functional Toolkit</div>", unsafe_allow_html=True)\n    toolkit_cols = st.columns(2)\n    toolkit = [\n        ("Speed Control", functions["speed_control"]),\n        ("Priority", functions["priority_moves"]),\n        ("Disruption", functions["disruption"]),\n        ("Support", functions["support"]),\n        ("Setup", functions["setup"]),\n    ]\n    for index, (label, values) in enumerate(toolkit):\n        with toolkit_cols[index % 2]:\n            st.markdown(f"<div style='font-size:15px;font-weight:900;margin:3px 0 5px;color:#f0f6fc;'>{'✅' if values else '◽'} {label}</div>", unsafe_allow_html=True)\n            _move_cards(values)\n\n    st.markdown("<div style='font-size:20px;font-weight:900;margin:16px 0 12px;color:#f0f6fc;'>🌦️ Field Control</div>", unsafe_allow_html=True)\n    field_cols = st.columns(2)\n    with field_cols[0]:\n        st.markdown("<div style='font-size:15px;font-weight:900;margin:3px 0 5px;color:#f0f6fc;'>Weather</div>", unsafe_allow_html=True)\n        if functions["weather"]:\n            _tool_pills(functions["weather"], "weather")\n        else:\n            st.caption("Not detected")\n    with field_cols[1]:\n        st.markdown("<div style='font-size:15px;font-weight:900;margin:3px 0 5px;color:#f0f6fc;'>Terrain</div>", unsafe_allow_html=True)\n        if functions["terrain"]:\n            _tool_pills(functions["terrain"], "terrain")\n        else:\n            st.caption("Not detected")\n\n'''
    text = text[:toolkit_start] + rebuilt_sections + text[coverage_start:]

    # Compact but integrated verdict cards: never let an empty "no concern" message float alone.
    verdict_start = text.index('    st.markdown("<div style=\'font-size:20px;font-weight:900;margin:14px 0 12px;color:#f0f6fc;\'>🧠 Team Verdict</div>", unsafe_allow_html=True)')
    detail_start = text.index('    with st.expander("📋 Detailed coverage", expanded=False):', verdict_start)
    verdict_block = '''    st.markdown("<div style='font-size:20px;font-weight:900;margin:16px 0 12px;color:#f0f6fc;'>🧠 Team Verdict</div>", unsafe_allow_html=True)\n    summary = result["summary"]\n    verdict_cols = st.columns(2)\n    with verdict_cols[0]:\n        with st.container(border=True):\n            st.markdown("<div style='font-size:16px;font-weight:900;margin-bottom:8px;color:#7ac74c;'>Strengths</div>", unsafe_allow_html=True)\n            if summary["strengths"]:\n                for item in summary["strengths"][:5]:\n                    st.markdown(f"✅ {item}")\n            else:\n                st.caption("No standout strength detected yet.")\n    with verdict_cols[1]:\n        with st.container(border=True):\n            st.markdown("<div style='font-size:16px;font-weight:900;margin-bottom:8px;color:#f59e0b;'>Things to watch</div>", unsafe_allow_html=True)\n            if summary["concerns"]:\n                for item in summary["concerns"][:5]:\n                    st.markdown(f"⚠️ {item}")\n            else:\n                st.caption("No major team-wide concern detected.")\n\n'''
    text = text[:verdict_start] + verdict_block + text[detail_start:]

    # Remove import of render_type_chips from the presentation layer; the analyzer uses its own roomier chips.
    text = text.replace('from champions.type_chart import render_type_chips\n', '', 1)

    PATH.write_text(text, encoding="utf-8")


if __name__ == "__main__":
    main()
