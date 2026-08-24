"""Streamlit presentation layer for the whole-team analyzer."""
from __future__ import annotations

from typing import Any, Dict, Mapping

import streamlit as st

from champions.pokemon_data import fetch_pokemon_details
from champions.team_analyzer import TeamAnalyzer, build_team_analyzer_input


def _active_slots(team_slots: Mapping[int, Mapping[str, Any]]):
    return [
        (idx, slot)
        for idx, slot in sorted(team_slots.items())
        if isinstance(slot, Mapping)
        and slot.get("name")
        and slot.get("name") != "-- Choose a Pokémon --"
    ]


def render_team_analyzer_sidebar(team_slots: Mapping[int, Mapping[str, Any]]) -> None:
    """Render the whole-team analyzer in the persistent sidebar."""
    active = _active_slots(team_slots)

    with st.sidebar.expander("🧠 Whole-Team Analyzer", expanded=True):
        if not active:
            st.caption("Build at least one Pokémon to start the team-wide analysis.")
            return

        details: Dict[str, Dict[str, Any]] = {}
        with st.spinner("Analyzing team…"):
            for _, slot in active:
                name = str(slot["name"])
                details[name] = fetch_pokemon_details(name)

        team = build_team_analyzer_input(active, details)
        result = TeamAnalyzer(team).analyze()

        st.metric("Team Score", f"{result['overall_score']:.1f} / 100", result["grade"])
        st.caption(f"Analyzing {result['team_size']} active Pokémon")

        score_cols = st.columns(2)
        score_cols[0].metric("🛡️ Defense", f"{result['defensive']['score']:.0f}")
        score_cols[1].metric("⚔️ Offense", f"{result['offensive']['score']:.0f}")
        score_cols = st.columns(2)
        score_cols[0].metric("🎛️ Function", f"{result['functions']['score']:.0f}")
        score_cols[1].metric("♻️ Redundancy", f"{result['redundancy']['score']:.0f}")

        summary = result["summary"]
        if summary["strengths"]:
            st.markdown("**What the team does well**")
            for item in summary["strengths"][:4]:
                st.markdown(f"✅ {item}")

        if summary["concerns"]:
            st.markdown("**Potential problems**")
            for item in summary["concerns"][:4]:
                st.markdown(f"⚠️ {item}")

        if result["functions"]["speed_control"]:
            st.markdown("**Speed control**")
            st.caption(", ".join(result["functions"]["speed_control"]))
        else:
            st.caption("No obvious speed-control option detected in the current moves/abilities.")

        with st.expander("Coverage details", expanded=False):
            defensive = result["defensive"]
            offensive = result["offensive"]
            st.markdown(f"**Defensively covered:** {len(defensive['covered_types'])}/{18} attacking types")
            if defensive["severe_gaps"]:
                st.markdown("**Defensive gaps:** " + ", ".join(defensive["severe_gaps"]))
            st.markdown(f"**Offensive super-effective coverage:** {len(offensive['covered_types'])}/{18} defending types")
            if offensive["quad_coverage"]:
                st.markdown("**4× pressure:** " + ", ".join(offensive["quad_coverage"]))
            if result["functions"]["priority_moves"]:
                st.markdown("**Priority:** " + ", ".join(result["functions"]["priority_moves"]))
            if result["functions"]["weather"]:
                st.markdown("**Weather:** " + ", ".join(result["functions"]["weather"]))
            if result["functions"]["terrain"]:
                st.markdown("**Terrain:** " + ", ".join(result["functions"]["terrain"]))
            if result["functions"]["disruption"]:
                st.markdown("**Disruption:** " + ", ".join(result["functions"]["disruption"][:8]))
            if result["archetypes"]["counts"]:
                st.markdown("**Archetypes:** " + ", ".join(sorted(result["archetypes"]["counts"])))
