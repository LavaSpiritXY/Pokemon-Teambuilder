from pathlib import Path

APP = Path("app.py")


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"Phase 18.4 anchor '{label}' expected once, found {count}.")
    return text.replace(old, new, 1)


def patch_renderer_call(text: str) -> str:
    name = "render_champions_profile_v5"
    start = text.find(name + "(")
    if start < 0:
        raise RuntimeError("Phase 18.4 active renderer call not found.")
    open_idx = text.find("(", start)
    depth = 0
    quote = None
    escape = False
    end = None
    for idx in range(open_idx, len(text)):
        ch = text[idx]
        if quote:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == quote:
                quote = None
            continue
        if ch in "'\"":
            quote = ch
        elif ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
            if depth == 0:
                end = idx + 1
                break
    if end is None:
        raise RuntimeError("Phase 18.4 could not parse renderer call.")
    call = text[start:end]
    if "base_stats=" not in call:
        call = call[:-1] + ', base_stats=mon_data.get("stats"))'
        text = text[:start] + call + text[end:]
    return text


def main() -> None:
    text = APP.read_text(encoding="utf-8")

    import_line = "from champions_phase18_3_ui import render_champions_profile_v5, render_base_stats_bubble\n"
    if import_line not in text:
        text = replace_once(
            text,
            "import pandas as pd\n",
            "import pandas as pd\n" + import_line,
            "Phase 18.4 UI import",
        )

    text = patch_renderer_call(text)

    old_ev = '''            for idx, (key, label) in enumerate(zip(ev_keys, ev_labels)):\n                with ev_cols[idx % 3]:\n                    slot["evs"][key] = strlit.number_input(\n                        label, min_value=0, max_value=252, step=4,\n                        value=slot["evs"].get(key, 0), key=f"stat_ev_{i}_{key}"\n                    )\n'''
    new_ev = '''            # Pokémon Champions uses SP rather than SV-style 252 EV spreads:\n            # max 32 SP in one stat and 66 SP total across all six stats.\n            sp_total_cap = 66\n            sp_per_stat_cap = 32\n            for idx, (key, label) in enumerate(zip(ev_keys, ev_labels)):\n                with ev_cols[idx % 3]:\n                    other_total = sum(int(slot["evs"].get(k, 0) or 0) for k in ev_keys if k != key)\n                    remaining = max(0, sp_total_cap - other_total)\n                    allowed_max = min(sp_per_stat_cap, remaining)\n                    current_value = max(0, min(int(slot["evs"].get(key, 0) or 0), allowed_max))\n                    slot["evs"][key] = strlit.number_input(\n                        label, min_value=0, max_value=allowed_max, step=1,\n                        value=current_value, key=f"stat_ev_{i}_{key}"\n                    )\n\n            current_sp_total = sum(int(slot["evs"].get(k, 0) or 0) for k in ev_keys)\n            strlit.caption(f"Champions SP: {current_sp_total} / 66 total · maximum 32 per stat")\n'''
    text = replace_once(text, old_ev, new_ev, "Champions SP allocation")

    # The matchup/offensive coverage panels already exist in app.py. Put the
    # new base-stat bubble immediately after those panels, still inside the
    # current slot loop, rather than after the loop where mon_data would refer
    # only to the last slot.
    tail = '''                    strlit.html(\n                        render_type_chips(\n                            resisted_types,\n                            resisted_multipliers\n                        )\n                    )\n\n'''
    insertion = tail + '''            render_base_stats_bubble(mon_data.get("stats"))\n\n'''
    text = replace_once(text, tail, insertion, "base stats placement")

    APP.write_text(text, encoding="utf-8")
    print("Phase 18.4 patch applied successfully to app.py")
    print("Tournament-weighted display viability, evidence-based roles, Champions SP limits, and per-slot base stats enabled.")
    print("Existing Strategizer scoring engine remains unchanged.")


if __name__ == "__main__":
    main()
