"""Phase 18.6/18.7 dynamic Champions stat-training UI."""
from __future__ import annotations
from typing import Any, Dict, Mapping, Optional
import streamlit as st

_STAT_KEYS = (("HP", "HP"), ("Attack", "Atk"), ("Defense", "Def"), ("Sp. Atk", "SpA"), ("Sp. Def", "SpD"), ("Speed", "Spe"))
_NATURE_EFFECTS = {"Lonely": ("Atk", "Def"), "Brave": ("Atk", "Spe"), "Adamant": ("Atk", "SpA"), "Naughty": ("Atk", "SpD"), "Bold": ("Def", "Atk"), "Relaxed": ("Def", "Spe"), "Impish": ("Def", "SpA"), "Lax": ("Def", "SpD"), "Timid": ("Spe", "Atk"), "Hasty": ("Spe", "Def"), "Jolly": ("Spe", "SpA"), "Naive": ("Spe", "SpD"), "Modest": ("SpA", "Atk"), "Mild": ("SpA", "Def"), "Quiet": ("SpA", "Spe"), "Rash": ("SpA", "SpD"), "Calm": ("SpD", "Atk"), "Gentle": ("SpD", "Def"), "Sassy": ("SpD", "Spe"), "Careful": ("SpD", "SpA"), "Hardy": (None, None), "Docile": (None, None), "Bashful": (None, None), "Quirky": (None, None), "Serious": (None, None)}

def _nature_effect(nature: str): return _NATURE_EFFECTS.get(str(nature or "Hardy").strip().split(" ")[0], (None, None))

def _base_stat(stats: Optional[Mapping[str, Any]], key: str) -> int:
    data=stats or {}; aliases={"HP":("HP","hp"),"Atk":("Atk","attack","Attack","atk"),"Def":("Def","defense","Defense","def"),"SpA":("SpA","special-attack","special_attack","specialAttack","Sp. Atk"),"SpD":("SpD","special-defense","special_defense","specialDefense","Sp. Def"),"Spe":("Spe","speed","Speed","spe")}
    for candidate in aliases.get(key,(key,)):
        if candidate in data:
            try: return max(0,int(data[candidate] or 0))
            except (TypeError,ValueError): return 0
    return 0

def _sanitize(slot: Dict[str, Any]) -> Dict[str,int]:
    raw=slot.get("evs") if isinstance(slot.get("evs"),dict) else {}; clean={}; total=0
    for _,key in _STAT_KEYS:
        try: value=max(0,min(32,int(raw.get(key,0) or 0)))
        except (TypeError,ValueError): value=0
        value=min(value,max(0,66-total)); clean[key]=value; total+=value
    slot["evs"]=clean; return clean

def _slider_max(values: Mapping[str,int], key: str) -> int:
    other=sum(v for k,v in values.items() if k!=key)
    return min(32,max(0,66-other))

def _sync_slider(slot_index: int, key: str) -> None:
    widget_key=f"stat_sp_slider_{slot_index}_{key}"
    try: requested=max(0,min(32,int(st.session_state.get(widget_key,0))))
    except (TypeError,ValueError): requested=0
    slot=st.session_state.team_slots[slot_index]; current=_sanitize(slot)
    allowed=_slider_max(current,key); requested=min(requested,allowed); current[key]=requested; slot["evs"]=current; st.session_state[widget_key]=requested

def _bar_colour(value: int) -> str:
    low,high=50.0,150.0; t=max(0.0,min(1.0,(float(value)-low)/(high-low))); stops=((0.0,(239,68,68)),(0.5,(249,145,0)),(1.0,(122,199,76)))
    if t<=0.5: a_pos,a=stops[0]; b_pos,b=stops[1]
    else: a_pos,a=stops[1]; b_pos,b=stops[2]
    p=(t-a_pos)/(b_pos-a_pos); rgb=tuple(round(a[i]+(b[i]-a[i])*p) for i in range(3)); return "#%02x%02x%02x"%rgb

def _stat_bar_html(value:int)->str:
    width=max(4,min(100,round(value/180*100))); colour=_bar_colour(value)
    return f'''<div style="width:100%;height:22px;border-radius:999px;background:#263241;border:1px solid #526071;overflow:hidden;box-sizing:border-box;"><div style="width:{width}%;height:100%;background:{colour};border-radius:999px;box-shadow:0 0 7px {colour}88;"></div></div>'''

def render_dynamic_stat_training(slot_index:int,pokemon_name:str,base_stats:Optional[Mapping[str,Any]],nature:str,sprite_url:str="",moves:Optional[list[str]]=None)->Dict[str,int]:
    values=render_dynamic_stat_controls(slot_index,pokemon_name,nature); render_dynamic_stat_graph(slot_index,pokemon_name,base_stats,nature); return values

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
            if f"stat_sp_slider_{slot_index}_{key}" not in st.session_state:
                st.session_state[f"stat_sp_slider_{slot_index}_{key}"] = values[key]

    st.subheader("🎯 EV Training")
    st.caption("Each stat: 0–32 · Team total: 0–66.")

    for label, key in _STAT_KEYS:
        max_allowed = _slider_max(values, key)
        current = min(values[key], max_allowed)
        widget_key = f"stat_sp_slider_{slot_index}_{key}"

        if max_allowed == 0:
            # Keep the same slider UI, but lock it when no SP remains.
            st.slider(
                f"{label} EVs — 🔒 MAX POINTS USED",
                min_value=0,
                max_value=32,
                value=0,
                step=1,
                disabled=True,
                key=f"stat_sp_locked_{slot_index}_{key}"
            )
            st.session_state[widget_key] = 0
        else:
            st.session_state[widget_key] = current
            st.slider(
                f"{label} EVs",
                0,
                max_allowed,
                value=current,
                step=1,
                key=widget_key,
                on_change=_sync_slider,
                args=(slot_index, key)
            )

    values = _sanitize(slot)
    st.caption(
        f"Champions SP: {sum(values.values())}/66 total · maximum 32 per stat"
    )
    return values

def render_dynamic_stat_graph(slot_index:int,pokemon_name:str,base_stats:Optional[Mapping[str,Any]],nature:str)->Dict[str,int]:
    slot=st.session_state.team_slots[slot_index]; values=_sanitize(slot); boosted,lowered=_nature_effect(nature)
    st.markdown(f"### 📊 {pokemon_name} — LIVE STAT PROFILE"); st.caption(f"{sum(values.values())}/66 SP allocated · {nature or 'Hardy'} nature · bar colour reflects final stat magnitude")
    header=st.columns([1.15,1.05,1.05,1.05,3.0,0.85])
    for col,text in zip(header,["Stat","Initial Base Stat","EV Allocation","Nature Change","Stat Magnitude","Total Base Stat"]): col.markdown(f"**{text}**")
    for label,key in _STAT_KEYS:
        base=_base_stat(base_stats,key); ev=values[key]; pre_nature=base+ev; delta=round(pre_nature*.10) if key==boosted else -round(pre_nature*.10) if key==lowered else 0; total=max(0,pre_nature+delta); nature_text=f"+{delta}" if delta>0 else str(delta); marker=" ↑" if key==boosted else " ↓" if key==lowered else ""
        cols=st.columns([1.15,1.05,1.05,1.05,3.0,0.85]); cols[0].markdown(f"**{label}{marker}**"); cols[1].markdown(f"<span style='color:#f1f5f9'>{base}</span>",unsafe_allow_html=True); cols[2].markdown(f"<span style='color:#f1f5f9'>+{ev}</span>",unsafe_allow_html=True); cols[3].markdown(f"<span style='color:#f1f5f9'>{nature_text}</span>",unsafe_allow_html=True); cols[4].html(_stat_bar_html(total)); cols[5].markdown(f"<span style='color:#f1f5f9;font-weight:700'>{total}</span>",unsafe_allow_html=True)
    st.caption("🔴 low → 🟠 medium → 🟢 high · colour changes continuously with the final stat"); return values

