"""Streamlit presentation layer for the whole-team analyzer."""
from __future__ import annotations

from typing import Any, Dict, Mapping

import streamlit as st

from champions.constants import TYPE_COLORS, TYPE_SVG_URLS
from champions.move_data import fetch_move_type, get_hardcoded_move_type
from champions.pokemon_data import fetch_pokemon_details
from champions.team_analyzer import TeamAnalyzer, build_team_analyzer_input


_ALL_TYPES = tuple(TYPE_COLORS.keys())


def _active_slots(team_slots: Mapping[int, Mapping[str, Any]]):
    return [
        (idx, slot)
        for idx, slot in sorted(team_slots.items())
        if isinstance(slot, Mapping)
        and slot.get("name")
        and slot.get("name") != "-- Choose a Pokémon --"
    ]


def _interpolate_colour(value: float) -> str:
    """Interpolate the score colour like the EV stat bars."""
    value = max(0.0, min(100.0, float(value)))
    stops = (
        (0.00, (239, 68, 68)),
        (0.30, (245, 95, 20)),
        (0.55, (234, 179, 8)),
        (0.76, (180, 200, 50)),
        (1.00, (122, 199, 76)),
    )

    for index in range(len(stops) - 1):
        start_pos, start_rgb = stops[index]
        end_pos, end_rgb = stops[index + 1]
        if value <= end_pos * 100:
            t = (value - start_pos * 100) / ((end_pos - start_pos) * 100)
            rgb = tuple(
                round(start_rgb[channel] + (end_rgb[channel] - start_rgb[channel]) * t)
                for channel in range(3)
            )
            return "#%02x%02x%02x" % rgb

    return "#7ac74c"


def _score_bar(label: str, value: float, compact: bool = False) -> None:
    """Render a magnitude-coloured filled bar matching the EV graph aesthetic."""
    value = max(0.0, min(100.0, float(value)))
    colour = _interpolate_colour(value)
    height = 12 if compact else 16
    margin = 8 if compact else 13
    label_size = 12 if compact else 13
    st.markdown(
        f"""
        <div style="margin:0 0 {margin}px 0;">
          <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:5px;">
            <span style="font-weight:700;color:#e6edf3;font-size:{label_size}px;">{label}</span>
            <span style="font-weight:900;color:{colour};font-size:{label_size}px;">{value:.0f}</span>
          </div>
          <div style="height:{height}px;border-radius:999px;background:#263241;border:1px solid #526071;overflow:hidden;box-sizing:border-box;">
            <div style="width:{value:.1f}%;height:100%;background:{colour};border-radius:999px;box-shadow:0 0 8px {colour}88;"></div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _type_for_move(move: str) -> str:
    """Resolve a move type through the same engine as the main move selector."""
    return get_hardcoded_move_type(move) or fetch_move_type(move)


def _display_move_name(move: str) -> str:
    """Preserve existing display names while fixing lower-case internal keys."""
    value = " ".join(str(move or "").replace("-", " ").split()).strip()
    if not value:
        return ""
    return value.title()


def _move_card(move: str) -> str:
    """Compact move card using the same type colour/icon system as the teambuilder."""
    display_name = _display_move_name(move)
    if not display_name:
        return ""
    move_type = _type_for_move(display_name)
    background = TYPE_COLORS.get(move_type, "#555")
    icon = TYPE_SVG_URLS.get(move_type, "")
    icon_html = f'<img src="{icon}" width="18" height="18" style="filter: brightness(0) invert(1);" />' if icon else ""
    return (
        '<div style="display:inline-flex;align-items:center;justify-content:space-between;gap:8px;'
        'width:168px;min-height:44px;padding:8px 11px;margin:6px 14px 6px 0;border-radius:10px;'
        'background:' + background + ';color:white;box-sizing:border-box;box-shadow:0 4px 10px rgba(0,0,0,0.25);vertical-align:top;">'
        f'<span style="min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;font-weight:850;font-size:14px;line-height:1.15;">{display_name}</span>'
        '<span style="display:flex;align-items:center;gap:4px;flex:0 0 auto;font-size:10px;font-weight:900;">'
        f'{icon_html}<span>{str(move_type).upper()}</span></span>'
        '</div>'
    )


def _move_cards(values, *, max_items: int = 6) -> None:
    values = list(values or [])
    if not values:
        st.caption("Not detected")
        return
    st.markdown("".join(_move_card(value) for value in values[:max_items]), unsafe_allow_html=True)


def _weather_pill(value: str) -> str:
    display = " ".join(str(value or "").replace("-", " ").split()).title()
    palette = {
        "Sun": ("#e87922", "#fff7ed"),
        "Rain": ("#3b82f6", "#eff6ff"),
        "Sand": ("#a8873b", "#fff8df"),
        "Snow": ("#69b8d8", "#effcff"),
        "Hail": ("#69b8d8", "#effcff"),
    }
    background, text_colour = palette.get(display, ("#64748b", "#f8fafc"))
    return f'<span style="display:inline-flex;align-items:center;justify-content:center;min-width:118px;height:40px;padding:0 13px;margin:6px 10px 6px 0;border-radius:12px;background:{background};color:{text_colour};font-weight:900;font-size:14px;box-shadow:0 4px 12px rgba(0,0,0,0.22);">{display}</span>'


def _terrain_pill(value: str) -> str:
    display = " ".join(str(value or "").replace("-", " ").split()).title()
    type_for_terrain = {"Electric Terrain": "Electric", "Grassy Terrain": "Grass", "Misty Terrain": "Fairy", "Psychic Terrain": "Psychic"}
    terrain_type = type_for_terrain.get(display, "Psychic")
    background = TYPE_COLORS.get(terrain_type, "#777")
    icon = TYPE_SVG_URLS.get(terrain_type, "")
    icon_html = f'<img src="{icon}" width="18" height="18" style="filter: brightness(0) invert(1);" />' if icon else ""
    return f'<span style="display:inline-flex;align-items:center;justify-content:center;gap:7px;min-width:150px;height:40px;padding:0 13px;margin:6px 10px 6px 0;border-radius:12px;background:{background};color:white;font-weight:900;font-size:14px;box-shadow:0 4px 12px rgba(0,0,0,0.22);">{icon_html}{display}</span>'


def _tool_pills(values, kind: str = "tool") -> None:
    values = list(values or [])
    if not values:
        st.caption("Not detected")
        return
    if kind == "weather":
        html = "".join(_weather_pill(value) for value in values[:6])
    elif kind == "terrain":
        html = "".join(_terrain_pill(value) for value in values[:6])
    else:
        html = "".join(f'<span style="display:inline-flex;align-items:center;justify-content:center;min-width:105px;height:38px;padding:0 11px;margin:4px 9px 5px 0;border-radius:11px;background:rgba(255,255,255,0.09);border:1px solid rgba(255,255,255,0.16);color:#f0f6fc;font-weight:850;font-size:13px;">{" ".join(str(value).replace("-", " ").split()).title()}</span>' for value in values[:6])
    st.markdown(html, unsafe_allow_html=True)


def _analyzer_type_chips(values, multipliers=None) -> None:
    values = list(values or [])
    if not values:
        st.caption("None")
        return
    multipliers = multipliers or {}
    cards = []
    for type_name in values:
        t = str(type_name).title()
        background = TYPE_COLORS.get(t, "#777")
        icon = TYPE_SVG_URLS.get(t, "")
        icon_html = f'<img src="{icon}" width="20" height="20" style="filter: brightness(0) invert(1);" />' if icon else ""
        mult = multipliers.get(t)
        suffix = f'<span style="font-size:12px;font-weight:900;opacity:.95;">×{mult:g}</span>' if isinstance(mult, (int, float)) and mult != 1 else ""
        cards.append(f'<span style="display:inline-flex;align-items:center;justify-content:space-between;gap:7px;min-width:126px;height:42px;padding:0 12px;margin:6px 12px 7px 0;border-radius:12px;background:{background};color:white;font-weight:900;font-size:14px;box-sizing:border-box;box-shadow:0 3px 9px rgba(0,0,0,0.20);">{icon_html}<span style="flex:1;text-align:left;">{t}</span>{suffix}</span>')
    st.markdown("".join(cards), unsafe_allow_html=True)



def _coverage_count_card(title: str, icon: str, covered: int, total: int, colour: str, caption: str) -> None:
    pct = (covered / total * 100.0) if total else 0.0
    st.markdown(
        f"""
        <div style="background:rgba(18,23,35,0.72);border:1px solid rgba(255,255,255,0.10);"
        "border-radius:14px;padding:13px 14px;margin-bottom:8px;">
          <div style="font-size:14px;font-weight:800;color:#f0f6fc;margin-bottom:2px;">{icon} {title}</div>
          <div style="display:flex;align-items:baseline;gap:6px;margin-bottom:6px;">
            <span style="font-size:31px;font-weight:900;color:{colour};line-height:1;">{covered}</span>
            <span style="font-size:13px;color:#8b949e;font-weight:700;">/ {total}</span>
          </div>
          <div style="height:10px;border-radius:999px;background:#263241;border:1px solid #526071;overflow:hidden;">
            <div style="width:{pct:.1f}%;height:100%;background:{colour};border-radius:999px;"></div>
          </div>
          <div style="font-size:11px;color:#8b949e;margin-top:6px;">{caption}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_team_analyzer_main(team_slots: Mapping[int, Mapping[str, Any]]) -> None:
    """Render the whole-team analyzer as the single Team Overview analysis dashboard."""
    active = _active_slots(team_slots)

    st.markdown(
        "<div style='margin-bottom:3px;font-size:25px;font-weight:900;color:#f0f6fc;'>🧠 Team Analysis</div>",
        unsafe_allow_html=True,
    )
    st.caption("A unified view of how the selected Pokémon work together.")

    if not active:
        st.info("Add Pokémon to your team slots to unlock the full team analysis.")
        return

    details: Dict[str, Dict[str, Any]] = {}
    with st.spinner("Analyzing team…"):
        for _, slot in active:
            name = str(slot["name"])
            details[name] = fetch_pokemon_details(name)

    team = build_team_analyzer_input(active, details)
    result = TeamAnalyzer(team).analyze()
    defensive = result["defensive"]
    offensive = result["offensive"]
    functions = result["functions"]
    redundancy = result["redundancy"]
    archetypes = result["archetypes"]
    overall_colour = _interpolate_colour(result["overall_score"])

    with st.container(border=True):
        top_cols = st.columns([1.15, 3.0])
        with top_cols[0]:
            st.markdown("**Overall Team Score**")
            st.markdown(
                f"<div style='font-size:48px;font-weight:950;color:{overall_colour};line-height:1;'>"
                f"{result['overall_score']:.0f}<span style='font-size:17px;color:#8b949e;'> / 100</span></div>",
                unsafe_allow_html=True,
            )
            st.caption(f"Grade **{result['grade']}** · {result['team_size']}/6 selected")
        with top_cols[1]:
            _score_bar("Overall team health", result["overall_score"])

    st.markdown("<div style='font-size:20px;font-weight:900;margin:6px 0 12px;color:#f0f6fc;'>📊 Performance Profile</div>", unsafe_allow_html=True)
    profile_cols = st.columns(2)
    profile = [
        ("Defensive Coverage", defensive["score"]),
        ("Offensive Coverage", offensive["score"]),
        ("Competitive Function", functions["score"]),
        ("Team Variety", redundancy["score"]),
        ("Archetype Coherence", archetypes["score"]),
    ]
    for index, (label, value) in enumerate(profile):
        with profile_cols[index % 2]:
            _score_bar(label, value, compact=True)

    st.markdown("<div style='font-size:20px;font-weight:900;margin:14px 0 12px;color:#f0f6fc;'>🧩 Functional Toolkit</div>", unsafe_allow_html=True)
    toolkit_cols = st.columns(2)
    toolkit = [
        ("Speed Control", functions["speed_control"]),
        ("Priority", functions["priority_moves"]),
        ("Disruption", functions["disruption"]),
        ("Support", functions["support"]),
        ("Setup", functions["setup"]),
    ]
    for index, (label, values) in enumerate(toolkit):
        with toolkit_cols[index % 2]:
            st.markdown(f"<div style='font-size:15px;font-weight:900;margin:3px 0 5px;color:#f0f6fc;'>{'✅' if values else '◽'} {label}</div>", unsafe_allow_html=True)
            _move_cards(values)

    st.markdown("<div style='font-size:20px;font-weight:900;margin:16px 0 12px;color:#f0f6fc;'>🌦️ Field Control</div>", unsafe_allow_html=True)
    field_cols = st.columns(2)
    with field_cols[0]:
        st.markdown("<div style='font-size:15px;font-weight:900;margin:3px 0 5px;color:#f0f6fc;'>Weather</div>", unsafe_allow_html=True)
        if functions["weather"]:
            _tool_pills(functions["weather"], "weather")
        else:
            st.caption("Not detected")
    with field_cols[1]:
        st.markdown("<div style='font-size:15px;font-weight:900;margin:3px 0 5px;color:#f0f6fc;'>Terrain</div>", unsafe_allow_html=True)
        if functions["terrain"]:
            _tool_pills(functions["terrain"], "terrain")
        else:
            st.caption("Not detected")

    st.markdown("<div style='font-size:20px;font-weight:900;margin:14px 0 12px;color:#f0f6fc;'>🔍 Coverage Snapshot</div>", unsafe_allow_html=True)
    coverage_cols = st.columns(3)
    defensive_colour = _interpolate_colour(len(defensive["covered_types"]) / 18 * 100)
    offensive_colour = _interpolate_colour(len(offensive["covered_types"]) / 18 * 100)
    variety_colour = _interpolate_colour(redundancy["score"])

    with coverage_cols[0]:
        _coverage_count_card(
            "Defensive Answers",
            "🛡️",
            len(defensive["covered_types"]),
            18,
            defensive_colour,
            "attacking types with at least one team answer",
        )
        if defensive["uncovered_types"]:
            st.caption("Gaps")
            _analyzer_type_chips(defensive["uncovered_types"], {t: 2.0 for t in defensive["uncovered_types"]})
        else:
            st.success("All attacking types covered")

    with coverage_cols[1]:
        _coverage_count_card(
            "Offensive Pressure",
            "⚔️",
            len(offensive["covered_types"]),
            18,
            offensive_colour,
            "defending types hit super-effectively",
        )
        if offensive["quad_coverage"]:
            st.caption("4× pressure")
            _analyzer_type_chips(offensive["quad_coverage"], {t: 4.0 for t in offensive["quad_coverage"]})
        else:
            st.caption("No 4× coverage detected")

    with coverage_cols[2]:
        _coverage_count_card(
            "Team Variety",
            "♻️",
            round(redundancy["score"]),
            100,
            variety_colour,
            "typing and team composition diversity score",
        )
        duplicates = redundancy["duplicate_types"]
        if duplicates:
            st.caption("Repeated typings")
            _analyzer_type_chips(sorted(duplicates), {t: float(c) for t, c in duplicates.items()})
        else:
            st.success("No heavy typing redundancy")

    st.markdown("<div style='font-size:20px;font-weight:900;margin:16px 0 12px;color:#f0f6fc;'>🧠 Team Verdict</div>", unsafe_allow_html=True)
    summary = result["summary"]
    verdict_cols = st.columns(2)
    with verdict_cols[0]:
        with st.container(border=True):
            st.markdown("<div style='font-size:16px;font-weight:900;margin-bottom:8px;color:#7ac74c;'>Strengths</div>", unsafe_allow_html=True)
            if summary["strengths"]:
                for item in summary["strengths"][:5]:
                    st.markdown(f"✅ {item}")
            else:
                st.caption("No standout strength detected yet.")
    with verdict_cols[1]:
        with st.container(border=True):
            st.markdown("<div style='font-size:16px;font-weight:900;margin-bottom:8px;color:#f59e0b;'>Things to watch</div>", unsafe_allow_html=True)
            if summary["concerns"]:
                for item in summary["concerns"][:5]:
                    st.markdown(f"⚠️ {item}")
            else:
                st.caption("No major team-wide concern detected.")

    with st.expander("📋 Detailed coverage", expanded=False):
        detail_cols = st.columns(2)
        with detail_cols[0]:
            st.markdown("**🛡️ Defensive coverage**")
            _analyzer_type_chips(defensive["covered_types"], {t: 1.0 for t in defensive["covered_types"]})
            st.markdown("**Resistance depth**")
            resistance_types = sorted(defensive["resistance_counts"].items(), key=lambda item: (-item[1], item[0]))[:10]
            if resistance_types:
                _analyzer_type_chips([t for t, _ in resistance_types], {t: float(c) for t, c in resistance_types})
            else:
                st.caption("No resistances detected.")
        with detail_cols[1]:
            st.markdown("**⚔️ Offensive coverage**")
            _analyzer_type_chips(offensive["covered_types"], {t: float(offensive["best_multipliers"].get(t, 2.0)) for t in offensive["covered_types"]})
            st.markdown("**Offensive gaps**")
            if offensive["uncovered_types"]:
                _analyzer_type_chips(offensive["uncovered_types"], {t: 1.0 for t in offensive["uncovered_types"]})
            else:
                st.caption("No major offensive gaps.")
        if archetypes["counts"]:
            st.markdown("**🧩 Archetypes**")
            st.caption(" · ".join(sorted(archetypes["counts"])))


def render_team_analyzer_sidebar(team_slots: Mapping[int, Mapping[str, Any]]) -> None:
    """Compatibility entry point retained for older callers."""
    render_team_analyzer_main(team_slots)
