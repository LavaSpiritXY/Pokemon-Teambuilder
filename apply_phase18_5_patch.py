from __future__ import annotations

from pathlib import Path
import re

ROOT = Path(__file__).resolve().parent
APP = ROOT / "app.py"


def replace_once(text: str, pattern: str, replacement: str, label: str, flags: int = 0) -> str:
    count = len(re.findall(pattern, text, flags))
    if count != 1:
        raise RuntimeError(f"Phase 18.5 anchor '{label}' expected once, found {count}.")
    return re.sub(pattern, replacement, text, count=1, flags=flags)


def replace_all_at_least_once(text: str, pattern: str, replacement: str, label: str, flags: int = 0) -> str:
    count = len(re.findall(pattern, text, flags))
    if count < 1:
        raise RuntimeError(f"Phase 18.5 anchor '{label}' expected at least once, found {count}.")
    return re.sub(pattern, replacement, text, flags=flags)


def replace_renderer_call(text: str) -> str:
    """Replace whichever Phase 18.x renderer call is actually active.

    Earlier patches may leave v5, another render_champions_profile_* call, or
    no renderer call at all. Do not assume one exact historical spelling.
    """
    replacement = '''        render_champions_profile_v6(\n            slot_name,\n            meta=meta,\n            sprite_resolver=get_mini_sprite_url,\n            base_stats=mon_data.get("stats"),\n            sp_values=slot.get("evs") or {},\n        )\n'''

    # First handle any existing renderer call using a balanced-parenthesis scan.
    matches = list(re.finditer(r"(?m)^\s*(render_champions_profile_[A-Za-z0-9_]+)\(", text))
    if matches:
        match = matches[0]
        start = match.start()
        open_idx = text.find("(", match.start())
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
            raise RuntimeError("Phase 18.5 could not parse active renderer call.")
        return text[:start] + replacement + text[end:]

    # If the renderer call was removed by an earlier patch, insert the new
    # renderer immediately before the Moveset Configuration column. This is
    # inside the current slot loop and after meta/type summaries are computed.
    anchor = '        with col_set:\n            strlit.markdown("##### ⚔️ Moveset Configuration")'
    if anchor in text:
        return text.replace(
            anchor,
            replacement + "\n" + anchor,
            1,
        )

    raise RuntimeError("Phase 18.5 could not locate an active profile insertion point.")


def main() -> None:
    text = APP.read_text(encoding="utf-8")

    # Collapse any stale Phase 18.3 import(s), regardless of whether the
    # previous patch duplicated them.
    import_pattern = r"^\s*from champions_phase18_3_ui import render_champions_profile_v5(?:, render_base_stats_bubble)?\s*$"
    if "from champions_phase18_5 import render_champions_profile_v6" not in text:
        if re.search(import_pattern, text, re.MULTILINE):
            text = re.sub(
                import_pattern,
                "from champions_phase18_5 import render_champions_profile_v6",
                text,
                count=1,
                flags=re.MULTILINE,
            )
            text = re.sub(import_pattern, "", text, flags=re.MULTILINE)
        else:
            text = replace_once(
                text,
                r"^import pandas as pd\s*$",
                "import pandas as pd\nfrom champions_phase18_5 import render_champions_profile_v6",
                "Phase 18.5 renderer import",
                re.MULTILINE,
            )
    else:
        text = re.sub(import_pattern, "", text, flags=re.MULTILINE)

    if "render_champions_profile_v6(" not in text:
        text = replace_renderer_call(text)

    # Replace the legacy 252-EV input block with Champions SP controls.
    if '##### 📊 Champions SP Allocation' not in text:
        ev_pattern = r'(?ms)^\s*strlit\.markdown\("##### 📊 Effort Values \(EV Spread\)"\).*?(?=^\s*strlit\.markdown\("##### Type matchup"\))'
        sp_block = '''            strlit.markdown("##### 📊 Champions SP Allocation")\n            sp_cols = col_set.columns(3)\n            sp_keys = ["HP", "Atk", "Def", "SpA", "SpD", "Spe"]\n            sp_labels = ["HP", "Attack", "Defense", "Sp. Atk", "Sp. Def", "Speed"]\n            if "evs" not in slot or not isinstance(slot["evs"], dict):\n                slot["evs"] = {k: 0 for k in sp_keys}\n            current_sp = {k: max(0, min(32, int(slot["evs"].get(k, 0) or 0))) for k in sp_keys}\n            used_sp = sum(current_sp.values())\n            for idx, (key, label) in enumerate(zip(sp_keys, sp_labels)):\n                with sp_cols[idx % 3]:\n                    other_sp = used_sp - current_sp[key]\n                    max_allowed = min(32, 66 - other_sp)\n                    current_value = current_sp[key]\n                    new_value = strlit.number_input(\n                        label, min_value=0, max_value=max_allowed, step=1,\n                        value=min(current_value, max_allowed), key=f"stat_sp_{i}_{key}"\n                    )\n                    current_sp[key] = int(new_value)\n                    slot["evs"][key] = int(new_value)\n                    used_sp = other_sp + int(new_value)\n            strlit.caption(f"Champions SP: {sum(current_sp.values())}/66 total · maximum 32 per stat")\n\n'''
        # Support either the original EV block or a Phase 18.4 SP block that
        # still uses the old heading.
        if re.search(ev_pattern, text):
            text = replace_once(text, ev_pattern, sp_block, "Champions SP controls")
        else:
            raise RuntimeError("Phase 18.5 could not locate the EV/SP allocation block.")

    APP.write_text(text, encoding="utf-8")
    print("Phase 18.5 patch applied successfully to app.py")
    print("Unified profile, tournament-led display viability, prominent base stats, SP highlighting, larger sprites, and no-data state enabled.")
    print("Existing Strategizer scoring engine remains unchanged.")


if __name__ == "__main__":
    main()
