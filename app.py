import streamlit as strlit
from champions.constants import (
    TYPE_COLORS,
    TYPE_SVG_URLS,
    NATURES,
    CUSTOM_MEGAS_DATA,
    BASE_HELD_ITEMS,
)

from typing import Dict, List, Set, Tuple

from champions.move_data import (
    fetch_move_type,
    get_hardcoded_move_type,
)

from champions.roster_data import (
    fetch_pokemon_roster,
)

from champions.meta_analytics import compute_meta_analytics

from champions.roles import infer_slot_role
from champions.team_moves import generate_synergistic_moveset, normalize_moves

from champions.species_keys import canonical_species_key

from champions.pokemon_data import (
    fetch_pokemon_details,
    get_mini_sprite_url,
)

from champions.type_chart import (
    get_type_defense_summary,
    get_offensive_type_summary,
    render_type_chips,
)

from champions.meta_engine import (
    MonMetaProfile,
    TeamEvaluator,
    slot_to_mon_meta_profile,
)

from champions.competitive_profile import render_champions_profile_v6
from champions.stat_training import render_dynamic_stat_controls, render_dynamic_stat_graph
from champions.team_io import export_slot_to_showdown, export_team_to_showdown, parse_showdown_text
from champions.team_analyzer_ui import render_team_analyzer_sidebar

from champions.team_state import ensure_slot_structure, on_species_change


# ==========================================
# 3. META-GATED CHECKS, COUNTERS & SYNERGY
# ==========================================



# -----------------------------------------------------------------------------
# 0. COMPETITIVE META EVALUATION ENGINE & DATA MODELS
# -----------------------------------------------------------------------------

# -----------------------------------------------------------------------------
# 1. CONFIG & VISUAL STYLING
# -----------------------------------------------------------------------------
strlit.set_page_config(
    page_title="Pokémon Champions Teambuilder",
    page_icon="⚔️",
    layout="wide",
    initial_sidebar_state="expanded"
)


strlit.markdown("""
<style>
    .stApp {
        background: linear-gradient(135deg, #0b0e14 0%, #1a1f2c 100%);
        color: #e6edf3;
    }
    header[data-testid="stHeader"] { background: transparent; }
    
    .type-badge {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        padding: 4px 10px;
        border-radius: 6px;
        font-weight: 700;
        font-size: 13px;
        color: white;
        white-space: nowrap;
    }
    
    .move-card {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 8px;
        padding: 10px 14px;
        border-radius: 8px;
        font-weight: 600;
        color: white;
        margin-top: -4px;
        margin-bottom: 14px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.3);
        width: 100%;
        box-sizing: border-box;
        overflow: hidden;
    }
    
    .move-name {
        flex: 1;
        min-width: 0;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }

    .move-type-badge {
        flex-shrink: 0;
        display: flex;
        align-items: center;
        gap: 4px;
        font-size: 11px;
    }

    .analytics-container {
        background: rgba(18, 23, 35, 0.8);
        border: 1px solid rgba(255, 255, 255, 0.15);
        border-radius: 12px;
        padding: 16px;
        margin-top: 14px;
        box-shadow: 0 8px 24px rgba(0,0,0,0.4);
    }

    .analytics-title {
        font-size: 16px;
        font-weight: 700;
        color: #f0f6fc;
        margin-bottom: 12px;
        display: flex;
        align-items: center;
        gap: 8px;
        border-bottom: 1px solid rgba(255, 255, 255, 0.1);
        padding-bottom: 8px;
    }

    .stat-box-row {
        display: flex;
        gap: 12px;
        margin-bottom: 12px;
    }

    .stat-box {
        flex: 1;
        background: rgba(255, 255, 255, 0.04);
        border-left: 4px solid #6390F0;
        border-radius: 6px;
        padding: 10px 12px;
    }

    .stat-box.counter-box {
        border-left-color: #EE8130;
    }

    .stat-box.viability-box {
        border-left-color: #7AC74C;
    }

    .stat-label {
        font-size: 11px;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        color: #8b949e;
        font-weight: 700;
        margin-bottom: 4px;
    }

    .stat-value {
        font-size: 15px;
        font-weight: 700;
        color: #e6edf3;
    }

    .type-chip {
        display: inline-flex;
        align-items: center;
        justify-content: space-between;
        gap: 4px;
        box-sizing: border-box;
        border-radius: 8px;
        color: white;
        font-size: 13px;
        font-weight: 700;
        margin: 10px 8px 0 0;
        min-height: 38px;
        padding: 5px 11px;
        width: 132px;
    }

    .type-chip img {
        height: 18px;
        width: 18px;
        filter: brightness(0) invert(1);
    }

    .type-multiplier {
        font-size: 13px;
        font-weight: 800;
        opacity: 0.9;
    }

    .type-chart-empty {
        color: #8b949e;
        font-size: 14px;
        font-weight: 700;
        margin-top: 4px;
    }

    .entity-pill {
        display: inline-flex;
        align-items: center;
        background: rgba(255, 255, 255, 0.08);
        border: 1px solid rgba(255, 255, 255, 0.12);
        border-radius: 20px;
        padding: 4px 10px 4px 4px;
        margin: 4px 6px 4px 0;
        font-size: 13px;
        font-weight: 600;
        color: #f0f6fc;
    }

    .entity-pill img {
        width: 38px;
        height: 38px;
        margin-right: 8px;
        border-radius: 50%;
        background: rgba(0,0,0,0.2);
        object-fit: contain;
    }
</style>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 2. DYNAMIC MASTER MOVE DICTIONARY & ROSTER DATA
# -----------------------------------------------------------------------------


MEGA_STONE_MAP = {name: f"{name.replace('Mega ', '')}ite" for name in CUSTOM_MEGAS_DATA.keys()}





CHAMPIONS_ALL_FORMS = fetch_pokemon_roster()

CHAMPIONS_HELD_ITEMS = sorted(list(set(BASE_HELD_ITEMS + list(MEGA_STONE_MAP.values()))))

# -----------------------------------------------------------------------------
# 3. HELPER FUNCTIONS & API FETCHING
# -----------------------------------------------------------------------------


# -----------------------------------------------------------------------------
# 3.5 SMOGON COMPETITIVE USAGE DATA SOURCE ENGINE
# -----------------------------------------------------------------------------



# Helper to convert slot state into MonMetaProfile for TeamEvaluator using real Smogon stats

# Showdown export/import utilities




# -----------------------------------------------------------------------------
# 4. INITIALIZE SESSION STATE
# -----------------------------------------------------------------------------
if "team_slots" not in strlit.session_state:
    strlit.session_state.team_slots = {}
for i in range(6):
    ensure_slot_structure(i, "-- Choose a Pokémon --")

# Whole-team analyzer: render independently of the individual slot tabs.
# It reads the same live team_slots state and therefore updates whenever a slot changes.
render_team_analyzer_sidebar(strlit.session_state.team_slots)

# -----------------------------------------------------------------------------
# 5. APP INTERFACE
# -----------------------------------------------------------------------------
strlit.title("⚔️ Pokémon Champions Teambuilder")

with strlit.sidebar:
    strlit.header("🛠️ Team Actions")
    if strlit.button("Reset Team"):
        strlit.session_state.team_slots = {}
        for idx in range(6):
            for key in (f"species_select_{idx}", f"ab_{idx}", f"item_{idx}", f"nat_{idx}"):
                strlit.session_state.pop(key, None)
            for move_idx in range(4):
                strlit.session_state.pop(f"move_{idx}_{move_idx}", None)
            for ev_key in ("HP", "Atk", "Def", "SpA", "SpD", "Spe"):
                strlit.session_state.pop(f"stat_ev_{idx}_{ev_key}", None)
            ensure_slot_structure(idx, "-- Choose a Pokémon --")
        strlit.rerun()

    strlit.checkbox("Only show legal moves", value=True, key="legal_moves_only")
    strlit.caption("Uses Smogon Showdown learnsets for legal verification.")

tabs = strlit.tabs([f"Slot {i+1}" for i in range(6)] + ["📊 Team Overview"])

for i in range(6):
    with tabs[i]:
        slot = ensure_slot_structure(i, "-- Choose a Pokémon --")
        slot_name = slot.get('name', '-- Choose a Pokémon --')
        strlit.subheader(f"Slot {i+1}: {slot_name if slot_name != '-- Choose a Pokémon --' else '(Empty Slot)'}")
        
        try:
            default_index = CHAMPIONS_ALL_FORMS.index(slot_name)
        except ValueError:
            default_index = 0

        selected_mon = strlit.selectbox(
            f"Species (Slot {i+1})",
            options=CHAMPIONS_ALL_FORMS,
            index=default_index,
            key=f"species_select_{i}",
            on_change=on_species_change,
            args=(i,)
        )

        slot = strlit.session_state.team_slots[i]
        slot_name = slot.get('name', selected_mon)

        if slot_name == "-- Choose a Pokémon --":
            strlit.info("👆 Please select a Pokémon from the dropdown above to begin building this slot.")
            continue

        col_mon, col_set = strlit.columns([1, 2])
        
        with col_mon:
            mon_data = fetch_pokemon_details(slot_name)
            strlit.image(mon_data["sprite"], width=170)
            
            badge_html = "".join([
                f'<div class="type-badge" style="background-color: {TYPE_COLORS.get(t, "#777")}; margin-right: 6px;">'
                f'<img src="{TYPE_SVG_URLS.get(t, "")}" width="14" height="14" style="filter: brightness(0) invert(1);" />'
                f'<span>{t.upper()}</span>'
                f'</div>'
                for t in mon_data["types"]
            ])
            strlit.markdown(f'<div style="display:flex; margin-bottom:12px;">{badge_html}</div>', unsafe_allow_html=True)

            ability_options = mon_data.get("abilities", ["Standard"])
            current_ability = slot.get("ability", ability_options[0])
            if current_ability not in ability_options:
                current_ability = ability_options[0]

            slot["ability"] = strlit.selectbox("Ability", options=ability_options, index=ability_options.index(current_ability), key=f"ab_{i}")
            strlit.caption(f"Suggested role: {infer_slot_role(slot)}")

            if slot_name in MEGA_STONE_MAP:
                correct_stone = MEGA_STONE_MAP[slot_name]
                slot["item"] = correct_stone
                strlit.text_input("Held Item", value=correct_stone, key=f"item_locked_{i}_{slot_name}", disabled=True)
            else:
                item_opts = CHAMPIONS_HELD_ITEMS
                current_item = slot.get("item", item_opts[0])
                if current_item not in item_opts:
                    current_item = item_opts[0]
                slot["item"] = strlit.selectbox("Held Item", options=item_opts, index=item_opts.index(current_item), key=f"item_{i}")

            nat_opts = NATURES
            current_nature = slot.get("nature", "Hardy")
            nat_match = [n for n in nat_opts if n.startswith(current_nature.split(" ")[0])]
            nat_idx = nat_opts.index(nat_match[0]) if nat_match else 0
            slot["nature"] = strlit.selectbox("Nature", options=nat_opts, index=nat_idx, key=f"nat_{i}")
            render_dynamic_stat_controls(
                slot_index=i,
                pokemon_name=slot_name,
                nature=slot.get("nature", "Hardy"),
            )


            meta = compute_meta_analytics(slot_name)
            type_summary = get_type_defense_summary(mon_data["types"])
            offensive_summary = get_offensive_type_summary(mon_data["types"])

            if not meta:
                meta = {
                    "tier": "Unknown",
                    "viability": "0 / 100",
                    "teammates": [],
                    "counters": [],
                    "speed_tier": "N/A",
                    "momentum_rating": "N/A",
                    "hazard_utility": "N/A",
                    "offensive_profile": "N/A",
                }
        render_champions_profile_v6(
            slot_name,
            meta=meta,
            sprite_resolver=get_mini_sprite_url,
            base_stats=mon_data.get("stats"),
            sp_values=slot.get("evs") or {},
        )

        with col_set:
            strlit.markdown("##### ⚔️ Moveset Configuration")
            all_moves = mon_data.get("moves", ["Protect", "Tackle"])
            slot["moves"] = normalize_moves(slot.get("moves", []), all_moves)

            for row_idx in range(2):
                m_col1, m_col2 = col_set.columns(2)
                for c_i, col in enumerate([m_col1, m_col2]):
                    m_idx = row_idx * 2 + c_i
                    current_selected = slot["moves"][m_idx]
                    available_options = [m for m in all_moves if m not in slot["moves"] or m == current_selected]
                    if current_selected not in available_options:
                        current_selected = available_options[0] if available_options else all_moves[0]
                        slot["moves"][m_idx] = current_selected

                    selected_move = col.selectbox(
                        f"Move {m_idx+1}",
                        options=available_options,
                        index=available_options.index(current_selected) if current_selected in available_options else 0,
                        key=f"move_{i}_{m_idx}"
                    )
                    slot["moves"][m_idx] = selected_move

                    m_type = get_hardcoded_move_type(selected_move) or fetch_move_type(selected_move)
                    col.markdown(f'''
                        <div class="move-card" style="background-color: {TYPE_COLORS.get(m_type, "#555")};">
                            <span class="move-name">{selected_move}</span>
                            <div class="move-type-badge">
                                <img src="{TYPE_SVG_URLS.get(m_type, "")}" width="14" height="14" style="filter: brightness(0) invert(1);" />
                                <span>{m_type.upper()}</span>
                            </div>
                        </div>
                    ''', unsafe_allow_html=True)


            strlit.markdown("##### Type matchup")
            with strlit.container(border=True):
                weak_col, resist_col, immune_col = strlit.columns(3)
                with weak_col:
                    strlit.caption("Weak to")
                    strlit.html(render_type_chips(type_summary["weak"], type_summary["multipliers"]))
                with resist_col:
                    strlit.caption("Resists")
                    strlit.html(render_type_chips(type_summary["resist"], type_summary["multipliers"]))
                with immune_col:
                    strlit.caption("Immune to")
                    strlit.html(render_type_chips(type_summary["immune"], type_summary["multipliers"]))

            strlit.markdown("##### Offensive coverage")

            with strlit.container(border=True):

                strong_col, resisted_col = strlit.columns(2)

                with strong_col:
                    strlit.caption("STAB attacks are strong against")

                    strong_multipliers = offensive_summary.get(
                        "strong_multipliers",
                        offensive_summary.get("strong_against", {})
                    )

                    strong_types = list(strong_multipliers.keys())

                    strlit.html(
                        render_type_chips(
                            strong_types,
                            strong_multipliers
                        )
                    )

                with resisted_col:
                    strlit.caption("STAB attacks are resisted by")

                    resisted_multipliers = offensive_summary.get(
                        "resisted_multipliers",
                        offensive_summary.get("resisted_by", {})
                    )

                    resisted_types = list(resisted_multipliers.keys())

                    strlit.html(
                        render_type_chips(
                            resisted_types,
                            resisted_multipliers
                        )
                    )

            render_dynamic_stat_graph(
                slot_index=i,
                pokemon_name=slot_name,
                base_stats=mon_data.get("stats"),
                nature=slot.get("nature", "Hardy"),
            )

# -----------------------------------------------------------------------------
# 6. TAB 7: TEAM OVERVIEW & TEAM EVALUATOR INTEGRATION
# -----------------------------------------------------------------------------
with tabs[6]:
    strlit.subheader("📊 Comprehensive Team Overview & Meta Evaluator")

    active_slots = [
        (idx, slot) for idx, slot in strlit.session_state.team_slots.items()
        if slot.get("name") and slot.get("name") != "-- Choose a Pokémon --"
    ]

    # Showdown Import / Export Section
    exp_col, imp_col = strlit.columns(2)
    with exp_col:
        with strlit.expander("📤 Export Showdown Pokepaste Text", expanded=False):
            exported_text = export_team_to_showdown(strlit.session_state.team_slots)
            strlit.code(exported_text if exported_text else "No Pokémon selected.", language="text")

    with imp_col:
        with strlit.expander("📥 Import Showdown Format", expanded=False):
            import_input = strlit.text_area("Paste Showdown format team below:", height=120)
            if strlit.button("Import Team"):
                if import_input.strip():
                    parsed = parse_showdown_text(import_input)
                    for idx in range(6):
                        if idx < len(parsed):
                            strlit.session_state.team_slots[idx] = parsed[idx]
                        else:
                            ensure_slot_structure(idx, "-- Choose a Pokémon --")
                    strlit.success(f"Imported {len(parsed)} Pokémon into team slots!")
                    strlit.rerun()

    strlit.divider()

    if not active_slots:
        strlit.info("💡 Add Pokémon to your team slots to run dynamic competitive evaluation.")
    else:
        # Build meta profiles for current team and evaluation candidates
        active_names = [slot["name"] for _, slot in active_slots]
        meta_db: Dict[str, MonMetaProfile] = {}

        for _, slot in active_slots:
            meta_db[slot["name"]] = slot_to_mon_meta_profile(slot)

        # Pre-populate meta DB with a sample pool of candidate threats for counter / synergy calculation
        top_candidates = ["Garchomp", "Gengar", "Dragonite", "Tyranitar", "Lucario", "Rotom Wash", "Ferrothorn", "Corviknight", "Clefable"]
        for cand_name in top_candidates:
            if cand_name not in meta_db:
                cand_slot = {"name": cand_name, "moves": ["Earthquake", "Swords Dance", "Stealth Rock", "Protect"], "ability": "Standard", "item": "Leftovers"}
                meta_db[cand_name] = slot_to_mon_meta_profile(cand_slot)

        evaluator = TeamEvaluator(meta_db)

        strlit.markdown("### 🏆 Team Synergy & Fit Ratings (`TeamEvaluator`)")
        
        slot_eval_cols = strlit.columns(len(active_slots))
        team_ratings = []

        for col_idx, (slot_i, slot) in enumerate(active_slots):
            mon_name = slot["name"]
            other_team = [n for n in active_names if n != mon_name]

            eval_res = evaluator.evaluate_candidate(mon_name, other_team)
            team_ratings.append(eval_res["final_rating"])

            with slot_eval_cols[col_idx]:
                mon_info = fetch_pokemon_details(mon_name)
                strlit.image(mon_info["box_sprite"], width=60)
                strlit.markdown(f"**{mon_name}**")
                strlit.metric("Fit Score", f"{eval_res['final_rating']} / 100")
                strlit.caption(f"**Class:** {eval_res['recommendation_class']}")
                strlit.markdown(
                    f"- **Defensive Fit:** {eval_res['defensive_fit']}\n"
                    f"- **Meta Coverage:** {eval_res['meta_coverage']}\n"
                    f"- **Synergy Index:** {eval_res['synergy_index']}\n"
                    f"- **Counter Utility:** {eval_res['counter_utility']}"
                )

        avg_score = round(sum(team_ratings) / len(team_ratings), 1) if team_ratings else 0
        strlit.markdown(f"#### 📊 Overall Composite Team Rating: **{avg_score} / 100**")

        # Candidate Suggestions for Open Slots
        if len(active_slots) < 6:
            strlit.markdown("### 💡 Top Recommended Picks for Next Slot")
            candidate_pool = [c for c in CHAMPIONS_ALL_FORMS if c != "-- Choose a Pokémon --" and c not in active_names][:12]
            
            recommendations = []
            for cand in candidate_pool:
                if cand not in meta_db:
                    meta_db[cand] = slot_to_mon_meta_profile({"name": cand, "moves": ["Protect"], "ability": "Standard", "item": ""})
                evaluator.meta = meta_db
                score = evaluator.evaluate_candidate(cand, active_names)
                recommendations.append((score["final_rating"], cand, score["recommendation_class"]))

            recommendations.sort(key=lambda x: -x[0])
            rec_cols = strlit.columns(min(4, len(recommendations)))
            for i_rec, (score_val, cand_name, rec_class) in enumerate(recommendations[:4]):
                with rec_cols[i_rec]:
                    c_info = fetch_pokemon_details(cand_name)
                    strlit.image(c_info["box_sprite"], width=50)
                    strlit.markdown(f"**{cand_name}**")
                    strlit.metric("Fit Score", f"{score_val} / 100")
                    strlit.caption(rec_class)

    strlit.divider()
    strlit.success("✓ `TeamEvaluator` integrated: candidate scoring, defensive weakness mitigation, and threat coverage active.")
    strlit.success("✓ Authoritative Smogon Chaos usage statistics engine integrated for tiering, abilities, items, and partner metrics.")
    strlit.success("✓ Dynamic moveset names fetched directly from Pokémon Showdown's GitHub repository.")
    strlit.success("✓ Showdown text format Pokepaste import and export functional.")



