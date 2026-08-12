"""Phase 18.6 dynamic Champions training UI.

Presentation/training layer only. It does not modify the Strategizer scoring engine.
"""
from __future__ import annotations

import html
from typing import Any, Dict, Mapping, Optional

import streamlit as st


_STAT_KEYS = (("HP", "HP"), ("Attack", "Atk"), ("Defense", "Def"), ("Sp. Atk", "SpA"), ("Sp. Def", "SpD"), ("Speed", "Spe"))

# Nature -> (boosted stat, lowered stat). Neutral natures are (None, None).
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
.ch186-row{display:grid;grid-template-columns:105px 1fr 78px;gap:10px;align-items:center;margin:10px 0}.ch186-name{font-weight:800;font-size:.84rem}.ch186-note{font-size:.7rem;color:rgba(180,190,205,.68);margin-top:2px}
.ch186-track{height:22px;border-radius:999px;overflow:hidden;background:rgba(148,163,184,.13);border:1px solid rgba(148,163,184,.17);display:flex}
.ch186-base{height:100%;background:linear-gradient(90deg,#64748b,#94a3b8)}.ch186-ev{height:100%;background:linear-gradient(90deg,#f59e0b,#7ac74c)}
.ch186-total{text-align:right;font-weight:900;font-variant-numeric:tabular-nums}.ch186-badge{display:inline-block;border-radius:999px;padding:2px 7px;font-size:.66rem;font-weight:900;margin-left:4px}
.ch186-up{background:rgba(122,199,76,.18);color:#7ac74c}.ch186-down{background:rgba(239,68,68,.16);color:#ef4444}.ch186-neutral{background:rgba(148,163,184,.14);color:#94a3b8}
.ch186-max{border:2px solid #ef4444;border-radius:10px;padding:5px 7px}.ch186-warning{border:1px solid rgba(239,68,68,.55);background:rgba(239,68,68,.10);border-radius:10px;padding:8px 10px;color:#f87171;font-weight:800;font-size:.8rem;margin-top:8px}
.ch186-slot{display:flex;align-items:center;gap:9px;padding:8px 10px;border:1px solid rgba(148,163,184,.22);border-radius:12px;background:rgba(148,163,184,.045);margin:7px 0}.ch186-slot img{width:48px;height:48px;object-fit:contain}.ch186-slot-name{font-weight:850}.ch186-slot-meta{font-size:.72rem;color:rgba(180,190,205,.72)}
@media(max-width:800px){.ch186-row{grid-template-columns:80px 1fr 64px}}
</style>
"""


def _nature_effect(nature: str) -> tuple[Optional[str], Optional[str]]:
    name = str(nature or "Hardy").strip().split(" ")[0]
    return _NATURE_EFFECTS.get(name, (None, None))


def _base_stat(stats: Optional[Mapping[str, Any]], key: str) -> int:
    data = stats or {}
    raw = data.get(key, data.get(key.lower(), 0))
    try:
        return max(0, int(raw or 0))
    except (TypeError, ValueError):
        return 0


def _sanitize(slot: Dict[str, Any]) -> Dict[str, int]:
    values = slot.get("evs")
    if not isinstance(values, dict):
        values = {}
    clean = {}
    for _, key in _STAT_KEYS:
        try:
            clean[key] = max(0, min(32, int(values.get(key, 0) or 0)))
        except (TypeError, ValueError):
            clean[key] = 0
    # Repair old/invalid states while preserving as much allocation as possible.
    total = 0
    for _, key in _STAT_KEYS:
        allowed = min(clean[key], 66 - total)
        clean[key] = max(0, allowed)
        total += clean[key]
    slot["evs"] = clean
    return clean


def _sync_value(slot_index: int, key: str, source: str) -> None:
    slider_key = f"stat_sp_slider_{slot_index}_{key}"
    input_key = f"stat_sp_input_{slot_index}_{key}"
    raw = st.session_state.get(slider_key if source == "slider" else input_key, 0)
    try:
        requested = max(0, min(32, int(raw)))
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
    st.session_state[slider_key] = requested
    st.session_state[input_key] = requested


def _ensure_widget_state(slot_index: int, values: Mapping[str, int]) -> None:
    for _, key in _STAT_KEYS:
        slider_key = f"stat_sp_slider_{slot_index}_{key}"
        input_key = f"stat_sp_input_{slot_index}_{key}"
        if slider_key not in st.session_state:
            st.session_state[slider_key] = int(values.get(key, 0))
        if input_key not in st.session_state:
            st.session_state[input_key] = int(values.get(key, 0))


def render_dynamic_stat_training(
    slot_index: int,
    pokemon_name: str,
    base_stats: Optional[Mapping[str, Any]],
    nature: str,
    sprite_url: str = "",
    moves: Optional[list[str]] = None,
) -> Dict[str, int]:
    """Render a dynamic Base Stat + EV planning panel and return sanitized EVs."""
    st.markdown(_CSS, unsafe_allow_html=True)
    slot = st.session_state.team_slots[slot_index]
    values = _sanitize(slot)
    _ensure_widget_state(slot_index, values)

    boosted, lowered = _nature_effect(nature)
    total = sum(values.values())

    sprite = html.escape(sprite_url, quote=True)
    safe_name = html.escape(str(pokemon_name))
    image = f"<img src='{sprite}' alt='{safe_name}'>" if sprite else ""
    nature_text = f"Nature: {html.escape(str(nature))}"
    if boosted:
        nature_text += f" · +{boosted} / -{lowered}"
    else:
        nature_text += " · neutral"

    st.markdown(
        f"<div class='ch186-slot'>{image}<div><div class='ch186-slot-name'>{safe_name}</div><div class='ch186-slot-meta'>{nature_text} · {total}/66 EVs allocated</div></div></div>",
        unsafe_allow_html=True,
    )

    st.markdown(
        "<div class='ch186-card'><div class='ch186-title'>📊 Dynamic Stat Training</div>"
        "<div class='ch186-sub'>Visual planning total = Base Stat + Champions EVs. Nature is shown dynamically; this is a planning chart, not the game's final-stat formula.</div></div>",
        unsafe_allow_html=True,
    )

    # Render the combined chart before the controls so every widget interaction redraws it immediately.
    rows = []
    for label, key in _STAT_KEYS:
        base = _base_stat(base_stats, key)
        ev = values[key]
        visual = base + ev
        nature_factor = 1.0
        if key == boosted:
            nature_factor = 1.10
        elif key == lowered:
            nature_factor = 0.90
        adjusted = round(visual * nature_factor)
        badge = "<span class='ch186-badge ch186-up'>+ Nature</span>" if key == boosted else ("<span class='ch186-badge ch186-down'>− Nature</span>" if key == lowered else "<span class='ch186-badge ch186-neutral'>Neutral</span>")
        # 180 base + 32 EV is the visual ceiling for this planning chart.
        base_width = max(0, min(100, base / 212 * 100))
        ev_width = max(0, min(100 - base_width, ev / 212 * 100))
        max_class = "ch186-max" if ev >= 32 else ""
        rows.append(
            f"<div class='ch186-row {max_class}'><div><div class='ch186-name'>{label} {badge}</div>"
            f"<div class='ch186-note'>Base {base} · EV {ev}</div></div>"
            f"<div class='ch186-track'><div class='ch186-base' style='width:{base_width:.1f}%'></div><div class='ch186-ev' style='width:{ev_width:.1f}%'></div></div>"
            f"<div class='ch186-total'>{adjusted}</div></div>"
        )
    st.markdown("<div class='ch186-card'>" + "".join(rows) + "</div>", unsafe_allow_html=True)

    notice_key = f"stat_sp_limit_notice_{slot_index}"
    if st.session_state.pop(notice_key, False):
        st.markdown("<div class='ch186-warning'>⚠️ EV limit reached — Champions allows a maximum of 66 total EVs and 32 EVs in any one stat.</div>", unsafe_allow_html=True)

    st.markdown("##### EV allocation")
    cols = st.columns(2)
    for idx, (label, key) in enumerate(_STAT_KEYS):
        with cols[idx % 2]:
            other_total = sum(values[k] for _, k in _STAT_KEYS if k != key)
            max_allowed = min(32, max(0, 66 - other_total))
            _ensure_widget_state(slot_index, values)
            st.slider(
                f"{label} EVs",
                min_value=0,
                max_value=32,
                step=1,
                key=f"stat_sp_slider_{slot_index}_{key}",
                on_change=_sync_value,
                args=(slot_index, key, "slider"),
            )
            st.number_input(
                f"{label} EVs (type)",
                min_value=0,
                max_value=max_allowed,
                step=1,
                key=f"stat_sp_input_{slot_index}_{key}",
                on_change=_sync_value,
                args=(slot_index, key, "input"),
            )
            if values[key] >= 32:
                st.markdown("<div class='ch186-warning'>EV limit reached for this stat.</div>", unsafe_allow_html=True)

    # Re-sanitize after all widget callbacks and persist the authoritative state.
    values = _sanitize(slot)
    for _, key in _STAT_KEYS:
        st.session_state[f"stat_sp_slider_{slot_index}_{key}"] = values[key]
        st.session_state[f"stat_sp_input_{slot_index}_{key}"] = values[key]
    slot["evs"] = values
    st.caption(f"EVs allocated: {sum(values.values())}/66 · per-stat cap: 32")
    return values
