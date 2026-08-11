from pathlib import Path
import re

APP = Path("app.py")


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"Phase 18.4 anchor '{label}' expected once, found {count}.")
    return text.replace(old, new, 1)


def replace_call(text: str, name: str, replacement: str) -> str:
    start = text.find(name + "(")
    if start < 0:
        raise RuntimeError(f"Phase 18.4 could not find active {name} call.")
    open_idx = text.find("(", start)
    depth = 0
    quote = None
    escape = False
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
            continue
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
            if depth == 0:
                return text[:start] + replacement + text[idx + 1:]
    raise RuntimeError(f"Phase 18.4 could not parse {name} call parentheses.")


def main() -> None:
    text = APP.read_text(encoding="utf-8")

    import_anchor = "import pandas as pd\n"
    if "from champions_phase18_3_ui import render_champions_profile_v5, render_base_stats_bubble" not in text:
        text = replace_once(
            text,
            import_anchor,
            import_anchor + "from champions_phase18_3_ui import render_champions_profile_v5, render_base_stats_bubble\n",
            "Phase 18.4 UI import",
        )

    # Pass the form's actual base stats into the renderer. The renderer itself
    # deliberately does not duplicate the type/offensive matchup panels.
    start = text.find("render_champions_profile_v5(")
    if start >= 0:
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
            call = call[:-1] + ", base_stats=mon_data.get(\"stats\"))"
            text = text[:start] + call + text[end:]
    else:
        raise RuntimeError("Phase 18.4 active renderer call not found.")

    old_ev = '''            for idx, (key, label) in enumerate(zip(ev_keys, ev_labels)):\n                with ev_cols[idx % 3]:\n                    slot["evs"][key] = strlit.number_input(\n                        label, min_value=0, max_value=252, step=4,\n                        value=slot["evs"].get(key, 0), key=f"stat_ev_{i}_{key}"\n                    )\n'''
    new_ev = '''            # Pokémon Champions uses SP rather than SV-style 252 EV spreads:\n            # max 32 SP in one stat and 66 SP total across all six stats.\n            sp_total_cap = 66\n            sp_per_stat_cap = 32\n            for idx, (key, label) in enumerate(zip(ev_keys, ev_labels)):\n                with ev_cols[idx % 3]:\n                    other_total = sum(int(slot["evs"].get(k, 0) or 0) for k in ev_keys if k != key)\n                    remaining = max(0, sp_total_cap - other_total)\n                    allowed_max = min(sp_per_stat_cap, remaining)\n                    current_value = max(0, min(int(slot["evs"].get(key, 0) or 0), allowed_max))\n                    slot["evs"][key] = strlit.number_input(\n                        label, min_value=0, max_value=allowed_max, step=1,\n                        value=current_value, key=f"stat_ev_{i}_{key}"\n                    )\n\n            current_sp_total = sum(int(slot["evs"].get(k, 0) or 0) for k in ev_keys)\n            strlit.caption(f"Champions SP: {current_sp_total} / 66 total · maximum 32 per stat")\n'''
    text = replace_once(text, old_ev, new_ev, "Champions SP allocation")

    # Add the single base-stat bubble after the existing defensive/offensive
    # coverage panels, before the Team Overview tab begins.
    marker = "# -----------------------------------------------------------------------------\n# 6. TAB 7: TEAM OVERVIEW & TEAM EVALUATOR INTEGRATION\n# -----------------------------------------------------------------------------"
    insertion = "render_base_stats_bubble(mon_data.get(\"stats\"))\n\n"
    if text.count(marker) != 1:
        raise RuntimeError("Phase 18.4 Team Overview marker expected once.")
    text = text.replace(marker, insertion + marker, 1)

    APP.write_text(text, encoding="utf-8")
    print("Phase 18.4 patch applied successfully to app.py")
    print("Tournament-weighted display viability, safe role labels, SP limits, and base-stat bubble enabled.")
    print("Existing Strategizer scoring engine remains unchanged.")


if __name__ == "__main__":
    main()
