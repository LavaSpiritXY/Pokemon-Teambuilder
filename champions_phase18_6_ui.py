"""Phase 18.6/18.7 dynamic Champions stat-training UI."""
from __future__ import annotations

import html
from typing import Any, Dict, Mapping, Optional

import streamlit as st

_STAT_KEYS = (("HP", "HP"), ("Attack", "Atk"), ("Defense", "Def"), ("Sp. Atk", "SpA"), ("Sp. Def", "SpD"), ("Speed", "Spe"))
_NATURE_EFFECTS = {
    "Lonely": ("Atk", "Def"), "Brave": ("Atk", "Spe"), "Adamant": ("Atk", "SpA"), "Naughty": ("Atk", "SpD"),
    "Bold": ("Def", "Atk"), "Relaxed": ("Def", "Spe"), "Impish": ("Def", "SpA"), "Lax": ("Def", "SpD"),
    "Timid": ("Spe", "Atk"), "Hasty": ("Spe", "Def"), "Jolly": ("Spe", "SpA"), "Naive": ("Spe", "SpD"),
    "Modest": ("SpA", "Atk"), "Mild": ("SpA", "Def"), "Quiet": ("SpA", "Spe"), "Rash": ("SpA", "SpD"),
    "Calm": ("SpD", "Atk"), "Gentle": ("SpD", "Def"), "Sassy": ("SpD", "Spe"), "Careful": ("SpD", "SpA"),
    "Hardy": (None, None), "Docile": (None, None), "Bashful": (None, None), "Quirky": (None, None), "Serious": (None, None),
}

def _nature_effect(nature: str):
    return _NATURE_EFFECTS.get(str(nature or "Hardy").strip().split(" ")[0], (None, None))

def _base_stat(stats: Optional[Mapping[str, Any]], key: str) -> int:
    data = stats or {}
    aliases = {"HP": ("HP", "hp"), "Atk": ("Atk", "attack", "Attack", "atk"), "Def": ("Def", "defense", "Defense", "def"), "SpA": ("SpA", "special-attack", "special_attack", "specialAttack", "Sp. Atk"), "SpD": ("SpD", "special-defense", "special_defense", "specialDefense", "Sp. Def"), "Spe": ("Spe", "speed", "Speed", "spe")}
    for candidate in aliases.get(key, (key,)):
        if candidate in data:
            try:
                return max(0, int(data[candidate] or 0))
            except (TypeError, ValueError):
                return 0
    return 0

def _sanitize(slot: Dict[str, Any]) -> Dict[str, int]:
    raw = slot.get("evs") if isinstance(slot.get("evs"), dict) else {}
    clean: Dict[str, int] = {}
    total = 0
    for _, key in _STAT_KEYS:
        try:
            value = max(0, min(32, int(raw.get(key, 0) or 0)))
        except (TypeError, ValueError):
            value = 0
        value = min(value, max(0, 66 - total))
        clean[key] = value
        total += value
    slot["evs"] = clean
    return clean

def _sync_slider(slot_index: int, key: str) -> None:
    widget_key = f"stat_sp_slider_{slot_index}_{key}"
    try:
        requested = max(0, min(32, int(st.session_state.get(widget_key, 0))))
    except (TypeError, ValueError):
        requested = 0
    slot = st.session_state.team_slots[slot_index]
    current = _sanitize(slot)
    other_total = sum(v for k, v in current.items() if k != key)
    allowed = min(32, max(0, 66 - other_total))
    if requested > allowed:
        requested = allowed
        st.session_state[f"stat_sp_limit_notice_{slot_index}"] = True
    current[key] = requested
    slot["evs"] = current

def render_dynamic_stat_training(slot_index: int, pokemon_name: str, base_stats: Optional[Mapping[str, Any]], nature: str, sprite_url: str = "", moves: Optional[list[str]] = None) -> Dict[str, int]:
    values = render_dynamic_stat_controls(slot_index, pokemon_name, nature)
    render_dynamic_stat_graph(slot_index, pokemon_name, base_stats, nature)
    return values

def render_dynamic_stat_controls(slot_index: int, pokemon_name: str, nature: str) -> Dict[str, int]:
    slot = st.session_state.team_slots[slot_index]
    values = _sanitize(slot)
    species_key = f"stat_sp_species_{slot_index}"
    if st.session_state.get(species_key) != pokemon_name:
        for _, key in _STAT_KEYS:
            st.session_state[f"stat_sp_slider_{slot_index}_{key}"] = values[key]
        st.session_state[species_key] = pokemon_name
    else:
        for _, key in _STAT_KEYS:
            widget_key = f"stat_sp_slider_{slot_index}_{key}"
            if widget_key not in st.session_state:
                st.session_state[widget_key] = values[key]
    st.markdown("### 🎯 EV Training")
    st.caption("Each stat: 0–32 · Team total: 0–66.")
    for label, key in _STAT_KEYS:
        st.slider(f"{label} EVs", min_value=0, max_value=32, value=values[key], step=1, key=f"stat_sp_slider_{slot_index}_{key}", on_change=_sync_slider, args=(slot_index, key))
        current = int(st.session_state.team_slots[slot_index].get("evs", {}).get(key, 0) or 0)
        st.caption(f"{current}/32")
    values = _sanitize(slot)
    total = sum(values.values())
    notice_key = f"stat_sp_limit_notice_{slot_index}"
    if st.session_state.pop(notice_key, False):
        st.warning("EV limit reached: maximum 32 in one stat and 66 total.")
    st.caption(f"Champions SP: {total}/66 total · maximum 32 per stat")
    return values

def render_dynamic_stat_graph(slot_index: int, pokemon_name: str, base_stats: Optional[Mapping[str, Any]], nature: str) -> Dict[str, int]:
    slot = st.session_state.team_slots[slot_index]
    values = _sanitize(slot)
    boosted, lowered = _nature_effect(nature)
    total = sum(values.values())
    labels = [label for label, _ in _STAT_KEYS]
    base_values: list[int] = []
    ev_values: list[int] = []
    actual_values: list[int] = []
    for _, key in _STAT_KEYS:
        base = _base_stat(base_stats, key)
        ev = values[key]
        multiplier = 1.10 if key == boosted else (0.90 if key == lowered else 1.0)
        base_values.append(base)
        ev_values.append(ev)
        actual_values.append(round((base + ev) * multiplier))

    st.markdown("### 📊 Dynamic Stat Training")
    st.caption(f"Live totals · {total}/66 EVs allocated · {html.escape(str(nature))}")

    import plotly.graph_objects as go
    y = labels[::-1]
    base = base_values[::-1]
    ev = ev_values[::-1]
    actual = actual_values[::-1]
    hover = []
    for label, key, b, e, a in zip(labels[::-1], [k for _, k in _STAT_KEYS][::-1], base, ev, actual):
        tag = "+ Nature" if key == boosted else "− Nature" if key == lowered else "Neutral"
        hover.append(f"{label}<br>Base: {b}<br>EV: +{e}<br>{tag}<br>Final: {a}")

    fig = go.Figure()
    fig.add_trace(go.Bar(y=y, x=base, orientation="h", name="Base", hoverinfo="text", hovertext=hover))
    fig.add_trace(go.Bar(y=y, x=ev, orientation="h", name="EV Training", hoverinfo="text", hovertext=hover))
    fig.update_layout(
        barmode="stack",
        height=390,
        margin=dict(l=10, r=45, t=15, b=10),
        xaxis=dict(range=[0, max(180, max(actual or [0]) + 10)], title=None, showgrid=True, zeroline=False),
        yaxis=dict(title=None, categoryorder="array", categoryarray=y),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        showlegend=True,
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(size=12),
    )
    fig.update_traces(marker_line_width=0)
    for y_value, value in zip(y, actual):
        fig.add_annotation(x=value, y=y_value, text=str(value), showarrow=False, xanchor="left", yshift=0, font=dict(size=13))
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
    return values
