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
_CSS = """
<style>
.ch186-card{border:1px solid rgba(148,163,184,.24);border-radius:14px;padding:14px 16px;background:rgba(148,163,184,.055);margin:8px 0}
.ch186-title{font-size:1.08rem;font-weight:850;margin-bottom:4px}.ch186-sub{font-size:.76rem;color:rgba(180,190,205,.72)}
.ch186-plot{width:100%;padding:8px 0 2px}.ch186-bar-row{display:grid;grid-template-columns:142px 1fr 52px;gap:12px;align-items:center;margin:12px 0}.ch186-bar-label{font-weight:800;font-size:.84rem}.ch186-bar-label small{display:block;font-size:.68rem;font-weight:650;color:rgba(180,190,205,.68);margin-top:2px}.ch186-track{height:25px;border-radius:7px;overflow:hidden;background:rgba(148,163,184,.13);border:1px solid rgba(148,163,184,.18);position:relative}.ch186-base{position:absolute;left:0;top:0;height:100%;background:rgba(148,163,184,.42)}.ch186-trained{position:absolute;top:0;height:100%;background:rgba(122,199,76,.78)}.ch186-value{text-align:right;font-weight:900;font-variant-numeric:tabular-nums}.ch186-scale{display:flex;justify-content:space-between;margin:2px 52px 0 154px;font-size:.62rem;color:rgba(180,190,205,.5)}
.ch186-badge{display:inline-block;border-radius:999px;padding:2px 7px;font-size:.66rem;font-weight:900;margin-left:4px}.ch186-up{background:rgba(122,199,76,.18);color:#7ac74c}.ch186-down{background:rgba(239,68,68,.16);color:#ef4444}.ch186-neutral{background:rgba(148,163,184,.14);color:#94a3b8}
.ch186-max{outline:2px solid rgba(239,68,68,.72);outline-offset:2px;border-radius:8px}.ch186-slot{display:flex;align-items:center;gap:9px;padding:8px 10px;border:1px solid rgba(148,163,184,.22);border-radius:12px;background:rgba(148,163,184,.045);margin:7px 0}.ch186-slot img{width:48px;height:48px;object-fit:contain}.ch186-slot-name{font-weight:850}.ch186-slot-meta{font-size:.72rem;color:rgba(180,190,205,.72)}
</style>
"""

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
    clean = {}
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
    st.markdown(_CSS, unsafe_allow_html=True)
    values = render_dynamic_stat_controls(slot_index, pokemon_name, nature)
    render_dynamic_stat_graph(slot_index, pokemon_name, base_stats, nature)
    return values

def render_dynamic_stat_controls(slot_index: int, pokemon_name: str, nature: str) -> Dict[str, int]:
    """Render the single authoritative Champions SP slider editor."""
    st.markdown("<div class='ch186-card'><div class='ch186-title'>🎯 EV Training</div><div class='ch186-sub'>Each stat: 0–32 · Team total: 0–66.</div></div>", unsafe_allow_html=True)
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
    """Render the intended live stacked bar chart: base stat plus trained contribution."""
    slot = st.session_state.team_slots[slot_index]
    values = _sanitize(slot)
    boosted, lowered = _nature_effect(nature)
    total = sum(values.values())
    labels = [label for label, _ in _STAT_KEYS]
    base_values = []
    actual_values = []
    for _, key in _STAT_KEYS:
        base = _base_stat(base_stats, key)
        ev = values[key]
        multiplier = 1.10 if key == boosted else (0.90 if key == lowered else 1.0)
        actual = round((base + ev) * multiplier)
        base_values.append(base)
        actual_values.append(actual)
    max_value = max(180, max(actual_values or [0]) + 10)

    st.markdown(
        f"<div class='ch186-card'><div class='ch186-title'>📊 Dynamic Stat Training</div><div class='ch186-sub'>Live totals · {total}/66 EVs allocated · {html.escape(str(nature))}</div></div>",
        unsafe_allow_html=True,
    )

    rows = []
    for label, key, base, actual in zip(labels, [k for _, k in _STAT_KEYS], base_values, actual_values):
        badge = "<span class='ch186-badge ch186-up'>+ Nature</span>" if key == boosted else "<span class='ch186-badge ch186-down'>− Nature</span>" if key == lowered else "<span class='ch186-badge ch186-neutral'>Neutral</span>"
        base_pct = max(0.0, min(100.0, base / max_value * 100.0))
        actual_pct = max(base_pct, min(100.0, actual / max_value * 100.0))
        trained_pct = max(0.0, actual_pct - base_pct)
        rows.append(
            f"<div class='ch186-bar-row'><div class='ch186-bar-label'>{html.escape(label)} {badge}<small>Base {base}</small></div>"
            f"<div class='ch186-track'><div class='ch186-base' style='width:{base_pct:.2f}%'></div><div class='ch186-trained' style='left:{base_pct:.2f}%;width:{trained_pct:.2f}%'></div></div>"
            f"<div class='ch186-value'>{actual}</div></div>"
        )
    st.markdown("<div class='ch186-card ch186-plot'>" + "".join(rows) + "<div class='ch186-scale'><span>0</span><span>60</span><span>120</span><span>180+</span></div></div>", unsafe_allow_html=True)
    return values
