"""Streamlit presentation layer for the whole-team analyzer."""
from __future__ import annotations

from typing import Any, Dict, Mapping

import streamlit as st

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


def _bar(label: str, value: float):
    value = max(0.0, min(100.0, float(value)))
    st.markdown(f"**{label}** · {value:.0f}/100")
    st.progress(int(value))


def render_team_analyzer_main(team_slots: Mapping[int, Mapping[str, Any]]) -> None:
    """Render the whole-team analyzer as a full-width dashboard."""
    active = _active_slots(team_slots)

    st.markdown("## 🧠 Whole-Team Analysis")
    st.caption("Your team's combined strengths, weaknesses, coverage and competitive toolkit.")

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

    hero_cols = st.columns([1.35, 1, 1, 1, 1])
    with hero_cols[0]:
        st.metric("Overall Team Score", f"{result['overall_score']:.1f} / 100", result["grade"])
    with hero_cols[1]:
        st.metric("🛡️ Defense", f"{result['defensive']['score']:.0f}")
    with hero_cols[2]:
        st.metric("⚔️ Offense", f"{result['offensive']['score']:.0f}")
    with hero_cols[3]:
        st.metric("🎛️ Function", f"{result['functions']['score']:.0f}")
    with hero_cols[4]:
        st.metric("♻️ Variety", f"{result['redundancy']['score']:.0f}")

    st.divider()

    graph_cols = st.columns(2)
    with graph_cols[0]:
        st.markdown("### 📊 Performance Profile")
        _bar("Defensive Coverage", result["defensive"]["score"])
        _bar("Offensive Coverage", result["offensive"]["score"])
        _bar("Competitive Function", result["functions"]["score"])
        _bar("Team Variety", result["redundancy"]["score"])
        _bar("Archetype Coherence", result["archetypes"]["score"])

    with graph_cols[1]:
        st.markdown("### 🧩 Functional Toolkit")
        rows = [
            ("Speed Control", result["functions"]["speed_control"]),
            ("Priority", result["functions"]["priority_moves"]),
            ("Weather", result["functions"]["weather"]),
            ("Terrain", result["functions"]["terrain"]),
            ("Disruption", result["functions"]["disruption"]),
            ("Support", result["functions"]["support"]),
            ("Setup", result["functions"]["setup"]),
        ]
        for label, values in rows:
            if values:
                st.markdown(f"✅ **{label}**")
                st.caption(", ".join(values[:6]))
            else:
                st.markdown(f"◽ **{label}**")
                st.caption("Not detected")

    st.markdown("### 🔍 Coverage Snapshot")
    defensive = result["defensive"]
    offensive = result["offensive"]
    coverage_cols = st.columns(3)

    with coverage_cols[0]:
        st.markdown("**🛡️ Defensive answers**")
        st.metric("Types covered", f"{len(defensive['covered_types'])} / 18")
        st.caption(
            "Multiple answers: " + ", ".join(defensive["best_answers"][:8])
            if defensive["best_answers"]
            else "No type currently has multiple clear answers."
        )

    with coverage_cols[1]:
        st.markdown("**⚔️ Offensive pressure**")
        st.metric("Super-effective coverage", f"{len(offensive['covered_types'])} / 18")
        st.caption(
            "4× pressure: " + ", ".join(offensive["quad_coverage"][:8])
            if offensive["quad_coverage"]
            else "No 4× offensive coverage detected."
        )

    with coverage_cols[2]:
        st.markdown("**⚠️ Major defensive gaps**")
        if defensive["severe_gaps"]:
            for gap in defensive["severe_gaps"][:6]:
                st.markdown(f"⚠️ **{gap}**")
        else:
            st.success("No severe team-wide defensive gap detected.")

    st.markdown("### 🧠 Team Verdict")
    summary = result["summary"]
    strengths_col, concerns_col = st.columns(2)
    with strengths_col:
        st.markdown("#### ✅ What you're doing well")
        if summary["strengths"]:
            for item in summary["strengths"][:6]:
                st.markdown(f"✅ {item}")
        else:
            st.caption("No standout strength detected yet.")
    with concerns_col:
        st.markdown("#### ⚠️ Things to watch")
        if summary["concerns"]:
            for item in summary["concerns"][:6]:
                st.markdown(f"⚠️ {item}")
        else:
            st.success("No major concern detected yet.")

    with st.expander("📋 Detailed coverage data", expanded=False):
        detail_cols = st.columns(2)
        with detail_cols[0]:
            st.markdown("**🛡️ Defensive coverage**")
            st.caption("Types with at least one defensive answer")
            covered_mult = {t: 1.0 for t in defensive["covered_types"]}
            st.html(render_type_chips(defensive["covered_types"], covered_mult))

            if defensive["uncovered_types"]:
                st.markdown("**⚠️ Uncovered**")
                uncovered_mult = {t: 2.0 for t in defensive["uncovered_types"]}
                st.html(render_type_chips(defensive["uncovered_types"], uncovered_mult))
            else:
                st.success("Every attacking type has at least one defensive answer.")

            st.markdown("**Resistance depth**")
            resistance_types = sorted(defensive["resistance_counts"].items(), key=lambda item: (-item[1], item[0]))[:10]
            if resistance_types:
                resistance_mult = {t: float(count) for t, count in resistance_types}
                st.html(render_type_chips([t for t, _ in resistance_types], resistance_mult))
            else:
                st.caption("No resistances detected.")

        with detail_cols[1]:
            st.markdown("**⚔️ Offensive coverage**")
            st.caption("Types your moves can hit super-effectively")
            offensive_mult = {t: float(offensive["best_multipliers"].get(t, 2.0)) for t in offensive["covered_types"]}
            st.html(render_type_chips(offensive["covered_types"], offensive_mult))

            if offensive["uncovered_types"]:
                st.markdown("**◽ Offensive gaps**")
                gap_mult = {t: 1.0 for t in offensive["uncovered_types"]}
                st.html(render_type_chips(offensive["uncovered_types"], gap_mult))

            if offensive["quad_coverage"]:
                st.markdown("**💥 4× pressure**")
                quad_mult = {t: 4.0 for t in offensive["quad_coverage"]}
                st.html(render_type_chips(offensive["quad_coverage"], quad_mult))

            if result["archetypes"]["counts"]:
                st.markdown("**🧩 Archetypes**")
                st.write(", ".join(sorted(result["archetypes"]["counts"])))


def render_team_analyzer_sidebar(team_slots: Mapping[int, Mapping[str, Any]]) -> None:
    """Compatibility entry point: render in the main page, never in the sidebar."""
    render_team_analyzer_main(team_slots)
