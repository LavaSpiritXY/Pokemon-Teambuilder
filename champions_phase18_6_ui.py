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
.ch186-row{display:grid;grid-template-columns:112px 1fr 58px;gap:10px;align-items:center;margin:10px 0;padding:3px 0;border-radius:10px}.ch186-name{font-weight:800;font-size:.84rem}.ch186-note{font-size:.7rem;color:rgba(180,190,205,.68);margin-top:2px}
.ch186-track{height:24px;border-radius:999px;overflow:hidden;background:rgba(148,163,184,.13);border:1px solid rgba(148,163,184,.17)}.ch186-fill{height:100%;border-radius:999px}.ch186-total{text-align:right;font-weight:900;font-variant-numeric:tabular-nums}.ch186-badge{display:inline-block;border-radius:999px;padding:2px 7px;font-size:.66rem;font-weight:900;margin-left:4px}.ch186-up{background:rgba(122,199,76,.18);color:#7ac74c}.ch186-down{background:rgba(239,68,68,.16);color:#ef4444}.ch186-neutral{background:rgba(148,163,184,.14);color:#94a3b8}
.ch186-max{border:2px solid #ef4444;border-radius:10px;padding:5px 7px}
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
    ratio = max(0.0, min(1.0, float(value) / 180.0)); return f"hsl({ratio * 120:.0f}, 72%, 48%)"

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
    """The full former-glory live radar: six axes, base outline, trained polygon, markers and stat bars."""
    slot = st.session_state.team_slots[slot_index]; values = _sanitize(slot)
    boosted, lowered = _nature_effect(nature)
    labels = [label for label, _ in _STAT_KEYS]; base_values = []; trained_values = []
    for _, key in _STAT_KEYS:
        base = _base_stat(base_stats, key); ev = values[key]
        multiplier = 1.10 if key == boosted else (0.90 if key == lowered else 1.0)
        base_values.append(base); trained_values.append(round((base + ev) * multiplier))
    st.markdown(f"<div class='ch186-card'><div class='ch186-title'>📊 {html.escape(str(pokemon_name))} — LIVE STAT RADAR</div><div class='ch186-sub'>{sum(values.values())}/66 SP allocated · {html.escape(str(nature or 'Hardy'))} nature</div></div>", unsafe_allow_html=True)
    try:
        import plotly.graph_objects as go
        theta = labels + [labels[0]]
        base = base_values + [base_values[0]]; trained = trained_values + [trained_values[0]]
        fig = go.Figure()
        fig.add_trace(go.Scatterpolar(r=base, theta=theta, mode="lines+markers", fill="toself", name="Base", line=dict(width=2), marker=dict(size=5)))
        fig.add_trace(go.Scatterpolar(r=trained, theta=theta, mode="lines+markers", fill="toself", name="Trained", line=dict(width=3), marker=dict(size=7)))
        fig.update_layout(height=470, margin=dict(l=35,r=35,t=35,b=30), showlegend=True,
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5),
            polar=dict(bgcolor="rgba(0,0,0,0)", radialaxis=dict(visible=True, range=[0,max(180,max(base_values+trained_values+[0])+15)]), angularaxis=dict(tickfont=dict(size=12))),
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font=dict(size=12))
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False, "responsive": True}, key=f"stat_radar_{slot_index}")
    except ImportError:
        st.error("Plotly is required for the radar graph. Run: pip install plotly")
    rows=[]
    for label,key in _STAT_KEYS:
        base=_base_stat(base_stats,key); ev=values[key]; multiplier=1.10 if key==boosted else (0.90 if key==lowered else 1.0); adjusted=round((base+ev)*multiplier); width=max(.5,min(100,adjusted/180*100))
        badge="<span class='ch186-badge ch186-up'>+ Nature</span>" if key==boosted else "<span class='ch186-badge ch186-down'>− Nature</span>" if key==lowered else "<span class='ch186-badge ch186-neutral'>Neutral</span>"
        rows.append(f"<div class='ch186-row {'ch186-max' if ev == 32 else ''}'><div><div class='ch186-name'>{label} {badge}</div><div class='ch186-note'>Base {base} · SP +{ev} · Nature ×{multiplier:.2f}</div></div><div class='ch186-track'><div class='ch186-fill' style='width:{width:.1f}%;background:{_stat_colour(adjusted)}'></div></div><div class='ch186-total'>{adjusted}</div></div>")
    st.markdown("<div class='ch186-card'>"+"".join(rows)+"</div>", unsafe_allow_html=True)
    return values
