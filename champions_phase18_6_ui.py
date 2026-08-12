"""Phase 18.6/18.7 dynamic Champions stat-training UI."""
from __future__ import annotations

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

def _nature_effect(nature: str): return _NATURE_EFFECTS.get(str(nature or "Hardy").strip().split(" ")[0], (None, None))

def _base_stat(stats: Optional[Mapping[str, Any]], key: str) -> int:
    data = stats or {}; aliases = {"HP": ("HP", "hp"), "Atk": ("Atk", "attack", "Attack", "atk"), "Def": ("Def", "defense", "Defense", "def"), "SpA": ("SpA", "special-attack", "special_attack", "specialAttack", "Sp. Atk"), "SpD": ("SpD", "special-defense", "special_defense", "specialDefense", "Sp. Def"), "Spe": ("Spe", "speed", "Speed", "spe")}
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
    slot=st.session_state.team_slots[slot_index]; current=_sanitize(slot); other=sum(v for k,v in current.items() if k!=key); allowed=min(32,max(0,66-other)); current[key]=min(requested,allowed); slot["evs"]=current

def _bar_colour(value: int) -> str:
    # Smooth red -> orange -> green based on the final stat's magnitude.
    # 60 is low, 100 is middle, 150+ is high; values between blend naturally.
    low, high = 60.0, 150.0
    t = max(0.0, min(1.0, (value - low) / (high - low)))
    if t < 0.5:
        # red -> orange
        p = t / 0.5
        r = 239
        g = round(68 + (115 - 68) * p)
        b = round(68 - 68 * p)
    else:
        # orange -> green
        p = (t - 0.5) / 0.5
        r = round(249 - (249 - 122) * p)
        g = round(115 + (199 - 115) * p)
        b = round(0 + 76 * p)
    return f"#{r:02x}{g:02x}{b:02x}"

def _stat_bar_html(value: int) -> str:
    width=max(4,min(100,round(value/180*100))); colour=_bar_colour(value)
    return f'<div style="width:100%;height:22px;border-radius:999px;background:#263241;border:1px solid #526071;overflow:hidden;"><div style="width:{width}%;height:100%;background:{colour};border-radius:999px;"></div></div>'

def render_dynamic_stat_training(slot_index: int, pokemon_name: str, base_stats: Optional[Mapping[str, Any]], nature: str, sprite_url: str = "", moves: Optional[list[str]] = None) -> Dict[str, int]:
    values=render_dynamic_stat_controls(slot_index,pokemon_name,nature); render_dynamic_stat_graph(slot_index,pokemon_name,base_stats,nature); return values

def render_dynamic_stat_controls(slot_index: int, pokemon_name: str, nature: str) -> Dict[str, int]:
    slot=st.session_state.team_slots[slot_index]; values=_sanitize(slot); species_key=f"stat_sp_species_{slot_index}"
    if st.session_state.get(species_key)!=pokemon_name:
        for _,key in _STAT_KEYS: st.session_state[f"stat_sp_slider_{slot_index}_{key}"]=values[key]
        st.session_state[species_key]=pokemon_name
    else:
        for _,key in _STAT_KEYS:
            if f"stat_sp_slider_{slot_index}_{key}" not in st.session_state: st.session_state[f"stat_sp_slider_{slot_index}_{key}"]=values[key]
    st.subheader("🎯 EV Training"); st.caption("Each stat: 0–32 · Team total: 0–66.")
    for label,key in _STAT_KEYS: st.slider(f"{label} EVs",0,32,value=values[key],step=1,key=f"stat_sp_slider_{slot_index}_{key}",on_change=_sync_slider,args=(slot_index,key))
    values=_sanitize(slot); st.caption(f"Champions SP: {sum(values.values())}/66 total · maximum 32 per stat"); return values

def render_dynamic_stat_graph(slot_index: int, pokemon_name: str, base_stats: Optional[Mapping[str, Any]], nature: str) -> Dict[str, int]:
    slot=st.session_state.team_slots[slot_index]; values=_sanitize(slot); boosted,lowered=_nature_effect(nature)
    st.markdown(f"### 📊 {pokemon_name} — LIVE STAT PROFILE"); st.caption(f"{sum(values.values())}/66 SP allocated · {nature or 'Hardy'} nature · bar colour reflects final stat magnitude")
    header=st.columns([1.15,1.05,1.05,1.05,3.0,0.85])
    for col,text in zip(header,["Stat","Initial Base Stat","EV Allocation","Nature Change","Stat Magnitude","Total Base Stat"]): col.markdown(f"**{text}**")
    for label,key in _STAT_KEYS:
        base=_base_stat(base_stats,key); ev=values[key]; pre_nature=base+ev
        delta=round(pre_nature*.10) if key==boosted else -round(pre_nature*.10) if key==lowered else 0
        total=max(0,pre_nature+delta); nature_text=f"+{delta}" if delta>0 else str(delta); marker=" ↑" if key==boosted else " ↓" if key==lowered else ""
        cols=st.columns([1.15,1.05,1.05,1.05,3.0,0.85]); cols[0].markdown(f"**{label}{marker}**"); cols[1].write(base); cols[2].write(f"+{ev}"); cols[3].write(nature_text); cols[4].html(_stat_bar_html(total)); cols[5].markdown(f"**{total}**")
    st.caption("🔴 RED = SMALL  🟠 ORANGE = MIDDLE  🟢 GREEN = BIG"); return values
