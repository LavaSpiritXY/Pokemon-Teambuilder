"""Streamlit presentation layer for the whole-team analyzer."""
from __future__ import annotations

from typing import Any, Dict, Mapping

import streamlit as st

from champions.constants import TYPE_COLORS, TYPE_SVG_URLS
from champions.pokemon_data import fetch_pokemon_details
from champions.team_analyzer import TeamAnalyzer, build_team_analyzer_input
from champions.type_chart import render_type_chips


def _active_slots(team_slots: Mapping[int, Mapping[str, Any]]):
    return [
        (idx, slot)
        for idx, slot in sorted(team_slots.items())
        if isinstance(slot, Mapping)
        and slot.get("name")
        and slot.get("name") != "-- Choose a Pokémon --"
    ]


def _score_colour(score: float) -> str:
    score = max(0.0, min(100.0, float(score)))
    if score < 50:
        return "#ef4444"
    if score < 70:
        return "#f59e0b"
    if score < 85:
        return "#eab308"
    return "#22c55e"


def _score_bar(label: str, value: float) -> None:
    value = max(0.0, min(100.0, float(value)))
    colour = _score_colour(value)
    st.markdown(
        f"""
        <div style="margin: 0 0 14px 0;">
          <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:5px;">
            <span style="font-weight:700;color:#e6edf3;font-size:13px;">{label}</span>
            <span style="font-weight:800;color:{colour};font-size:13px;">{value:.0f}</span>
          </div>
          <div style="height:10px;border-radius:999px;background:rgba(255,255,255,0.08);overflow:hidden;">
            <div style="height:100%;width:{value:.1f}%;border-radius:999px;background:linear-gradient(90deg,#ef4444 0%,#f59e0b 45%,#eab308 70%,#22c55e 100%);"></div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _move_chip(move: str, kind: str = "utility") -> str:
    move_type = ""
    move_name = " ".join(str(move).split()).strip()
    if not move_name:
        return ""
    # The analyzer stores utility labels, while actual moves are inferred from the
    # same canonical move names used elsewhere in the app. Keep the chip neutral
    # when we do not know a precise move type here.
    background = "rgba(255,255,255,0.08)"
    border = "rgba(255,255,255,0.13)"
    if kind == "priority":
        background = "rgba(236,72,153,0.16)"
        border = "rgba(236,72,153,0.35)"
    elif kind == "speed":
        background = "rgba(59,130,246,0.16)"
        border = "rgba(59,130,246,0.35)"
    elif kind == "support":
        background = "rgba(16,185,129,0.16)"
        border = "rgba(16,185,129,0.35)"
    elif kind == "disruption":
        background = "rgba(245,158,11,0.16)"
        border = "rgba(245,158,11,0.35)"
    elif kind == "setup":
        background = "rgba(168,85,247,0.16)"
        border = "rgba(168,85,247,0.35)"
    return (
        f'<span style="display:inline-flex;align-items:center;padding:6px 10px;margin:3px 5px 3px 0;'
        f'border-radius:9px;background:{background};border:1px solid {border};color:#f0f6fc;'
        f'font-weight:700;font-size:12px;white-space:nowrap;">{move_name}</span>'
    )


def _move_chips(values, kind: str = "utility") -> None:
    values = list(values or [])
    if not values:
        st.caption("Not detected")
        return
    html = "".join(_move_chip(value, kind) for value in values[:8])
    st.markdown(html, unsafe_allow_html=True)


def _section_card(title: str, body_html: str) -> None:
    st.markdown(
        f"""
        <div style="background:rgba(18,23,35,0.72);border:1px solid rgba(255,255,255,0.10);'
        border-radius:14px;padding:14px 16px;margin-bottom:12px;">
          <div style="font-size:14px;font-weight:800;color:#f0f6fc;margin-bottom:9px;">{title}</div>
          {body_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_team_analyzer_main(team_slots: Mapping[int, Mapping[str, Any]]) -> None:
    """Render the whole-team analyzer as the single Team Overview analysis dashboard."""
    active = _active_slots(team_slots)

    st.markdown("## 🧠 Team Analysis")
    st.caption("A single, unified view of how the six Pokémon work together."
               )

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

    hero = st.container(border=True)
    with hero:
        score_cols = st.columns([1.4, 1, 1, 1])
        with score_cols[0]:
            st.markdown("### Overall Team Score")
            st.markdown(
                f"<div style='font-size:42px;font-weight:900;color:{_score_colour(result['overall_score'])};line-height:1;'>{result['overall_score']:.0f}<span style='font-size:16px;color:#8b949e;'> / 100</span></div>",
                unsafe_allow_html=True,
            )
            st.caption(f"Grade **{result['grade']}** · {result['team_size']}/6 Pokémon selected")
            _score_bar("Overall", result["overall_score"])
        with score_cols[1]:
            st.metric("Defense", f"{defensive['score']:.0f}")
        with score_cols[2]:
            st.metric("Offense", f"{offensive['score']:.0f}")
        with score_cols[3]:
            st.metric("Function", f"{functions['score']:.0f}")

    st.markdown("### 📊 Performance Profile")
    profile_cols = st.columns(5)
    profile = [
        ("Defense", defensive["score"]),
        ("Offense", offensive["score"]),
        ("Function", functions["score"]),
        ("Variety", redundancy["score"]),
        ("Coherence", archetypes["score"]),
    ]
    for col, (label, value) in zip(profile_cols, profile):
        with col:
            _score_bar(label, value)

    st.markdown("### 🧩 Functional Toolkit")
    toolkit_cols = st.columns(2)
    toolkit = [
        ("Speed Control", functions["speed_control"], "speed"),
        ("Priority", functions["priority_moves"], "priority"),
        ("Weather", functions["weather"], "utility"),
        ("Terrain", functions["terrain"], "utility"),
        ("Disruption", functions["disruption"], "disruption"),
        ("Support", functions["support"], "support"),
        ("Setup", functions["setup"], "setup"),
    ]
    for idx, (label, values, kind) in enumerate(toolkit):
        with toolkit_cols[idx % 2]:
            mark = "✅" if values else "◽"
            st.markdown(f"**{mark} {label}**")
            _move_chips(values, kind)

    st.markdown("### 🔍 Coverage Snapshot")
    coverage_cols = st.columns(3)

    with coverage_cols[0]:
        with st.container(border=True):
            st.markdown("**🛡️ Defensive answers**")
            st.markdown(
                f"<div style='font-size:28px;font-weight:900;'>{len(defensive['covered_types'])}<span style='font-size:13px;color:#8b949e;'> / 18 types</span></div>",
                unsafe_allow_html=True,
            )
            _score_bar("Coverage", len(defensive["covered_types"]) / 18 * 100)
            if defensive["uncovered_types"]:
                st.caption("Gaps")
                st.html(render_type_chips(defensive["uncovered_types"], {t: 2.0 for t in defensive["uncovered_types"]}))
            else:
                st.success("All attacking types covered")

    with coverage_cols[1]:
        with st.container(border=True):
            st.markdown("**⚔️ Offensive pressure**")
            st.markdown(
                f"<div style='font-size:28px;font-weight:900;'>{len(offensive['covered_types'])}<span style='font-size:13px;color:#8b949e;'> / 18 types</span></div>",
                unsafe_allow_html=True,
            )
            _score_bar("Coverage", len(offensive["covered_types"]) / 18 * 100)
            if offensive["quad_coverage"]:
                st.caption("4× pressure")
                st.html(render_type_chips(offensive["quad_coverage"], {t: 4.0 for t in offensive["quad_coverage"]}))
            else:
                st.caption("No 4× coverage detected")

    with coverage_cols[2]:
        with st.container(border=True):
            st.markdown("**♻️ Team variety**")
            _score_bar("Typing diversity", redundancy["score"])
            duplicates = redundancy["duplicate_types"]
            if duplicates:
                st.caption("Repeated typings")
                st.html(render_type_chips(sorted(duplicates), {t: float(c) for t, c in duplicates.items()}))
            else:
                st.success("No heavy typing redundancy")

    st.markdown("### 🧠 Team Verdict")
    summary = result["summary"]
    verdict_cols = st.columns(2)
    with verdict_cols[0]:
        st.markdown("#### ✅ Strengths")
        for item in summary["strengths"][:5] or ["No standout strength detected yet."]:
            st.markdown(f"✅ {item}")
    with verdict_cols[1]:
        st.markdown("#### ⚠️ Things to watch")
        for item in summary["concerns"][:5] or ["No major concern detected yet."]:
            st.markdown(f"⚠️ {item}")

    with st.expander("📋 Detailed coverage", expanded=False):
        detail_cols = st.columns(2)
        with detail_cols[0]:
            st.markdown("**🛡️ Defensive coverage**")
            st.html(render_type_chips(defensive["covered_types"], {t: 1.0 for t in defensive["covered_types"]}))
            st.markdown("**Resistance depth**")
            resistance_types = sorted(defensive["resistance_counts"].items(), key=lambda item: (-item[1], item[0]))[:10]
            if resistance_types:
                st.html(render_type_chips([t for t, _ in resistance_types], {t: float(c) for t, c in resistance_types}))
            else:
                st.caption("No resistances detected.")
        with detail_cols[1]:
            st.markdown("**⚔️ Offensive coverage**")
            st.html(render_type_chips(offensive["covered_types"], {t: float(offensive["best_multipliers"].get(t, 2.0)) for t in offensive["covered_types"]}))
            st.markdown("**Offensive gaps**")
            if offensive["uncovered_types"]:
                st.html(render_type_chips(offensive["uncovered_types"], {t: 1.0 for t in offensive["uncovered_types"]}))
            else:
                st.caption("No major offensive gaps.")
        if archetypes["counts"]:
            st.markdown("**🧩 Archetypes**")
            st.caption(" · ".join(sorted(archetypes["counts"])))


def render_team_analyzer_sidebar(team_slots: Mapping[int, Mapping[str, Any]]) -> None:
    """Compatibility entry point retained for older callers."""
    render_team_analyzer_main(team_slots)
