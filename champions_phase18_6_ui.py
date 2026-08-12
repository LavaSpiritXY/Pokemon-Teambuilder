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
.ch186-name{font-weight:800;font-size:.84rem}.ch186-value{text-align:center;font-weight:850;font-variant-numeric:tabular-nums}.ch186-track{height:24px;border-radius:999px;overflow:hidden;background:rgba(148,163,184,.13);border:1px solid rgba(148,163,184,.25);box-shadow:inset 0 1px 3px rgba(0,0,0,.25)}.ch186-fill{height:100%;min-width:6px;border-radius:999px;transition:width .2s ease}.ch186-total{text-align:right;font-weight:950;font-variant-numeric:tabular-nums;font-size:1rem}
.ch186-badge{display:inline-block;border-radius:999px;padding:2px 7px;font-size:.66rem;font-weight:900;margin-left:4px}.ch186-up{background:rgba(122,199,76,.18);color:#7ac74c}.ch186-down{background:rgba(239,68,68,.16);color:#ef4444}.ch186-neutral{background:rgba(148,163,184,.14);color:#94a3b8}
.ch186-max{border:2px solid #ef4444}.ch186-legend{display:flex;justify-content:space-between;gap:12px;font-size:.68rem;color:rgba(180,190,205,.72);margin-top:8px}.ch186-low{color:#ef4444}.ch186-mid{color:#f97316}.ch186-high{color:#7ac74c}
@media (max-width:900px){.ch186-header{grid-template-columns:90px 72px 72px 72px 1fr 55px;gap:6px;font-size:.58rem}.ch186-row{grid-template-columns:90px 72px 72px 72px 1fr 55px;gap:6px}.ch186-value{font-size:.78rem}}
</style>
"""

def _nature_effect(nature: str): return _NATURE_EFFECTS.get(str(nature or "Hardy").strip().split(" ")[0], (None, None))

def _base_stat(stats: Optional[Mapping[str, Any]], key: str) -> int:
    data = stats or {}; aliases = {"HP": ("HP","hp"), "Atk": ("Atk","attack","Attack","atk"), "Def": ("Def","defense","Defense","def"), "SpA": ("SpA","special-attack","special_attack","specialAttack","Sp. Atk"), "SpD": ("SpD","special-defense","special_defense","specialDefense","Sp. Def"), "Spe": ("Spe","speed","Speed","spe")}
    for candidate in aliases.get(key, (key,)):
        if candidate in data:
            try: return max(0, int(data[candidate] or 0))
            except (TypeError, ValueError): return 0
    return 0

def _sanitize(slot: Dict[str, Any]) -> Dict[str, int]:
    raw = slot.get("evs") if isinstance(slot.get("evs"), dict) else {}; clean: Dict[str,int] = {}; total = 0
    for _, key in _STAT_KEYS:
        try: value = max(0, min(32, int(raw.get(key, 0) or 0)))
        except (TypeError, ValueError): value = 0
        value = min(value, max(0, 66-total)); clean[key] = value; total += value
    slot["evs"] = clean; return clean

def _sync_slider(slot_index: int, key: str) -> None:
    widget_key=f"stat_sp_slider_{slot_index}_{key}"
    try: requested=max(0,min(32,int(st.session_state.get(widget_key,0))))
    except (TypeError,ValueError): requested=0
    slot=st.session_state.team_slots[slot_index]; current=_sanitize(slot); other=sum(v for k,v in current.items() if k!=key); allowed=min(32,max(0,66-other)); requested=min(requested,allowed); current[key]=requested; slot["evs"]=current

def _stat_colour(value: int) -> str:
    if value <= 80: return "#ef4444"
    if value <= 120: return "#f97316"
    return "#7ac74c"

def _stat_bar(value: int) -> str:
    """Build a deliberately visible text bar so the magnitude colour cannot disappear with HTML/CSS."""
    segments = max(1, min(20, round(value / 180 * 20)))
    if value <= 80: block = "🟥"
    elif value <= 120: block = "🟧"
    else: block = "🟩"
    return block * segments

def render_dynamic_stat_training(slot_index: int, pokemon_name: str, base_stats: Optional[Mapping[str, Any]], nature: str, sprite_url: str = "", moves: Optional[list[str]] = None) -> Dict[str, int]:
    st.markdown(_CSS, unsafe_allow_html=True); values=render_dynamic_stat_controls(slot_index,pokemon_name,nature); render_dynamic_stat_graph(slot_index,pokemon_name,base_stats,nature); return values

def render_dynamic_stat_controls(slot_index: int, pokemon_name: str, nature: str) -> Dict[str, int]:
    slot=st.session_state.team_slots[slot_index]; values=_sanitize(slot); species_key=f"stat_sp_species_{slot_index}"
    if st.session_state.get(species_key)!=pokemon_name:
        for _,key in _STAT_KEYS: st.session_state[f"stat_sp_slider_{slot_index}_{key}"]=values[key]
        st.session_state[species_key]=pokemon_name
    else:
        for _,key in _STAT_KEYS:
            if f"stat_sp_slider_{slot_index}_{key}" not in st.session_state: st.session_state[f"stat_sp_slider_{slot_index}_{key}"]=values[key]
    st.markdown("<div class='ch186-card'><div class='ch186-title'>🎯 EV Training</div><div class='ch186-sub'>Each stat: 0–32 · Team total: 0–66.</div></div>",unsafe_allow_html=True)
    for label,key in _STAT_KEYS: st.slider(f"{label} EVs",0,32,value=values[key],step=1,key=f"stat_sp_slider_{slot_index}_{key}",on_change=_sync_slider,args=(slot_index,key))
    values=_sanitize(slot); st.caption(f"Champions SP: {sum(values.values())}/66 total · maximum 32 per stat"); return values

def render_dynamic_stat_graph(slot_index: int, pokemon_name: str, base_stats: Optional[Mapping[str, Any]], nature: str) -> Dict[str, int]:
    slot=st.session_state.team_slots[slot_index]; values=_sanitize(slot); boosted,lowered=_nature_effect(nature); rows=[]
    for label,key in _STAT_KEYS:
        base=_base_stat(base_stats,key); ev=values[key]; pre=base+ev; delta=round(pre*.10) if key==boosted else -round(pre*.10) if key==lowered else 0; total=max(0,pre+delta); width=max(3,min(100,total/180*100)); rows.append((label,key,base,ev,delta,total,width))
    st.markdown(f"<div class='ch186-card'><div class='ch186-title'>📊 {html.escape(str(pokemon_name))} — LIVE STAT PROFILE</div><div class='ch186-sub'>{sum(values.values())}/66 SP allocated · {html.escape(str(nature or 'Hardy'))} nature · bar colour reflects final stat magnitude</div></div>",unsafe_allow_html=True)
    st.markdown("<div class='ch186-header'><div>Stat</div><div style='text-align:center'>Initial Base Stat</div><div style='text-align:center'>EV Allocation</div><div style='text-align:center'>Nature Change</div><div>Stat Magnitude</div><div style='text-align:right'>Total Base Stat</div></div>",unsafe_allow_html=True)
    out=[]
    for label,key,base,ev,delta,total,width in rows:
        badge="<span class='ch186-badge ch186-up'>+</span>" if key==boosted else "<span class='ch186-badge ch186-down'>−</span>" if key==lowered else "<span class='ch186-badge ch186-neutral'>0</span>"; nature_text=f"+{delta}" if delta>0 else str(delta); bar=_stat_bar(total)
        out.append(f"<div class='ch186-row'><div class='ch186-name'>{label} {badge}</div><div class='ch186-value'>{base}</div><div class='ch186-value'>+{ev}</div><div class='ch186-value'>{nature_text}</div><div class='ch186-track'><div class='ch186-fill' style='width:{width:.1f}%;background:{_stat_colour(total)}'></div></div><div class='ch186-total'>{total}</div></div>")
        out.append(f"<div style='margin:-5px 0 9px 360px;font-size:12px;line-height:1.1;white-space:nowrap'>{bar}</div>")
    st.markdown("<div class='ch186-card'>"+"".join(out)+"<div class='ch186-legend'><span class='ch186-low'>🟥 RED = SMALL</span><span class='ch186-mid'>🟧 ORANGE = MIDDLE</span><span class='ch186-high'>🟩 GREEN = BIG</span></div></div>",unsafe_allow_html=True); return values
