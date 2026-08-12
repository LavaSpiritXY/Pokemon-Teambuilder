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
.ch186-card{border:1px solid rgba(148,163,184,.24);border-radius:16px;padding:16px;background:rgba(148,163,184,.055);margin:8px 0}
.ch186-title{font-size:1.08rem;font-weight:850;margin-bottom:4px}.ch186-sub{font-size:.76rem;color:rgba(180,190,205,.72)}
.ch186-header{display:grid;grid-template-columns:115px 105px 105px 105px 1fr 72px;gap:10px;align-items:center;margin:10px 0 4px;padding:0 8px;color:rgba(180,190,205,.72);font-size:.68rem;font-weight:800;text-transform:uppercase;letter-spacing:.04em}
.ch186-row{display:grid;grid-template-columns:115px 105px 105px 105px 1fr 72px;gap:10px;align-items:center;margin:8px 0;padding:9px 8px;border-radius:10px;background:rgba(148,163,184,.035)}
.ch186-name{font-weight:800;font-size:.84rem}.ch186-value{text-align:center;font-weight:850;font-variant-numeric:tabular-nums}.ch186-note{font-size:.68rem;color:rgba(180,190,205,.68);margin-top:2px}
.ch186-track{height:24px;border-radius:999px;overflow:hidden;background:rgba(148,163,184,.13);border:1px solid rgba(148,163,184,.17)}.ch186-fill{height:100%;border-radius:999px;transition:width .2s ease,background .2s ease}.ch186-total{text-align:right;font-weight:950;font-variant-numeric:tabular-nums;font-size:1rem}
.ch186-badge{display:inline-block;border-radius:999px;padding:2px 7px;font-size:.66rem;font-weight:900;margin-left:4px}.ch186-up{background:rgba(122,199,76,.18);color:#7ac74c}.ch186-down{background:rgba(239,68,68,.16);color:#ef4444}.ch186-neutral{background:rgba(148,163,184,.14);color:#94a3b8}
.ch186-max{border:2px solid #ef4444}.ch186-legend{display:flex;justify-content:space-between;gap:12px;font-size:.68rem;color:rgba(180,190,205,.72);margin-top:8px}.ch186-low{color:#ef4444}.ch186-mid{color:#f97316}.ch186-high{color:#7ac74c}
@media (max-width:900px){.ch186-header{grid-template-columns:90px 72px 72px 72px 1fr 55px;gap:6px;font-size:.58rem}.ch186-row{grid-template-columns:90px 72px 72px 72px 1fr 55px;gap:6px}.ch186-value{font-size:.78rem}.ch186-note{font-size:.58rem}}
</style>
"""

def _nature_effect(nature: str):
    return _NATURE_EFFECTS.get(str(nature or "Hardy").strip().split(" ")[0], (None, None))

def _base_stat(stats: Optional[Mapping[str, Any]], key: str) -> int:
    data = stats or {}
    aliases = {"HP": ("HP", "hp"), "Atk": ("Atk", "attack", "Attack", "atk"), "Def": ("Def", "defense", "Defense", "def"), "SpA": ("SpA", "special-attack", "special_attack", "specialAttack", "Sp. Atk"), "SpD": ("SpD", "special-defense", "special_defense", "specialDefense", "Sp. Def"), "Spe": ("Spe", "speed", "Speed", "spe")}
    for candidate in aliases.get(key, (key,)):
        if candidate in data:
            try: return max(0, int(data[candidate] or 0))
            except (TypeError, ValueError): return 0
    return 0

def _sanitize(slot: Dict[str, Any]) -> Dict[str, int]:
    raw = slot.get("evs") if isinstance(slot.get("evs"), dict) else {}
    clean: Dict[str, int] = {}; total = 0
    for _, key in _STAT_KEYS:
        try: value = max(0, min(32, int(raw.get(key, 0) or 0)))
        except (TypeError, ValueError): value = 0
        value = min(value, max(0, 66 - total)); clean[key] = value; total += value
    slot["evs"] = clean
    return clean

def _sync_slider(slot_index: int, key: str) -> None:
    widget_key = f"stat_sp_slider_{slot_index}_{key}"
    try: requested = max(0, min(32, int(st.session_state.get(widget_key, 0))))
    except (TypeError, ValueError): requested = 0
    slot = st.session_state.team_slots[slot_index]; current = _sanitize(slot)
    other_total = sum(v for k, v in current.items() if k != key); allowed = min(32, max(0, 66 - other_total))
    if requested > allowed:
        requested = allowed; st.session_state[f"stat_sp_limit_notice_{slot_index}"] = True
    current[key] = requested; slot["evs"] = current

def _stat_colour(value: int) -> str:
    """Low stats are red, middle stats are orange, and high stats are green."""
    value = max(0.0, float(value))
    if value <= 80:
        ratio = value / 80.0
        hue = 0.0 + (30.0 * ratio)
    elif value <= 120:
        ratio = (value - 80.0) / 40.0
        hue = 30.0 + (90.0 * ratio)
    else:
        hue = 120.0
    return f"hsl({hue:.0f}, 78%, 48%)"

def render_dynamic_stat_training(slot_index: int, pokemon_name: str, base_stats: Optional[Mapping[str, Any]], nature: str, sprite_url: str = "", moves: Optional[list[str]] = None) -> Dict[str, int]:
    st.markdown(_CSS, unsafe_allow_html=True)
    values = render_dynamic_stat_controls(slot_index, pokemon_name, nature)
    render_dynamic_stat_graph(slot_index, pokemon_name, base_stats, nature)
    return values

def render_dynamic_stat_controls(slot_index: int, pokemon_name: str, nature: str) -> Dict[str, int]:
    slot = st.session_state.team_slots[slot_index]; values = _sanitize(slot)
    species_key = f"stat_sp_species_{slot_index}"
    if st.session_state.get(species_key) != pokemon_name:
        for _, key in _STAT_KEYS: st.session_state[f"stat_sp_slider_{slot_index}_{key}"] = values[key]
        st.session_state[species_key] = pokemon_name
    else:
        for _, key in _STAT_KEYS:
            widget_key = f"stat_sp_slider_{slot_index}_{key}"
            if widget_key not in st.session_state: st.session_state[widget_key] = values[key]
    st.markdown("<div class='ch186-card'><div class='ch186-title'>🎯 EV Training</div><div class='ch186-sub'>Each stat: 0–32 · Team total: 0–66.</div></div>", unsafe_allow_html=True)
    for label, key in _STAT_KEYS:
        st.slider(f"{label} EVs", 0, 32, value=values[key], step=1, key=f"stat_sp_slider_{slot_index}_{key}", on_change=_sync_slider, args=(slot_index, key))
    values = _sanitize(slot); total = sum(values.values())
    if st.session_state.pop(f"stat_sp_limit_notice_{slot_index}", False): st.warning("EV limit reached: maximum 32 in one stat and 66 total.")
    st.caption(f"Champions SP: {total}/66 total · maximum 32 per stat")
    return values

def render_dynamic_stat_graph(slot_index: int, pokemon_name: str, base_stats: Optional[Mapping[str, Any]], nature: str) -> Dict[str, int]:
    """Render a live stat-bar profile. No Plotly, no radar chart."""
    slot = st.session_state.team_slots[slot_index]; values = _sanitize(slot)
    boosted, lowered = _nature_effect(nature)
    stat_rows = []
    for label, key in _STAT_KEYS:
        base = _base_stat(base_stats, key)
        ev = values[key]
        pre_nature = base + ev
        if key == boosted:
            nature_delta = round(pre_nature * 0.10)
        elif key == lowered:
            nature_delta = -round(pre_nature * 0.10)
        else:
            nature_delta = 0
        total_stat = max(0, pre_nature + nature_delta)
        width = max(0.5, min(100.0, total_stat / 180.0 * 100.0))
        stat_rows.append((label, key, base, ev, nature_delta, total_stat, width))

    total_ev = sum(values.values())
    st.markdown(
        f"<div class='ch186-card'><div class='ch186-title'>📊 {html.escape(str(pokemon_name))} — LIVE STAT PROFILE</div>"
        f"<div class='ch186-sub'>{total_ev}/66 SP allocated · {html.escape(str(nature or 'Hardy'))} nature · bar colour reflects final stat magnitude</div></div>",
        unsafe_allow_html=True,
    )

    st.markdown(
        "<div class='ch186-header'><div>Stat</div><div style='text-align:center'>Initial Base Stat</div><div style='text-align:center'>EV Allocation</div><div style='text-align:center'>Nature Change</div><div>Stat Magnitude</div><div style='text-align:right'>Total Base Stat</div></div>",
        unsafe_allow_html=True,
    )

    rows = []
    for label, key, base, ev, nature_delta, total_stat, width in stat_rows:
        if key == boosted:
            badge = "<span class='ch186-badge ch186-up'>+</span>"
            nature_text = f"+{nature_delta}"
        elif key == lowered:
            badge = "<span class='ch186-badge ch186-down'>−</span>"
            nature_text = str(nature_delta)
        else:
            badge = "<span class='ch186-badge ch186-neutral'>0</span>"
            nature_text = "0"
        max_class = "ch186-max" if ev == 32 else ""
        rows.append(
            f"<div class='ch186-row {max_class}'>"
            f"<div><div class='ch186-name'>{label} {badge}</div></div>"
            f"<div class='ch186-value'>{base}</div>"
            f"<div class='ch186-value'>+{ev}</div>"
            f"<div class='ch186-value'>{nature_text}</div>"
            f"<div class='ch186-track'><div class='ch186-fill' style='width:{width:.1f}%;background:{_stat_colour(total_stat)}'></div></div>"
            f"<div class='ch186-total'>{total_stat}</div></div>"
        )

    st.markdown(
        "<div class='ch186-card'>"
        + "".join(rows)
        + "<div class='ch186-legend'><span class='ch186-low'>RED = SMALL</span><span class='ch186-mid'>ORANGE = MIDDLE</span><span class='ch186-high'>GREEN = BIG</span></div>"
        + "</div>",
        unsafe_allow_html=True,
    )
    return values
