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


def main() -> None:
    text = APP.read_text(encoding="utf-8")

    # Some earlier Phase 18.x edits can leave the legacy renderer import
    # duplicated. Collapse every legacy import into one Phase 18.5 import.
    import_pattern = r"^\s*from champions_phase18_3_ui import render_champions_profile_v5(?:, render_base_stats_bubble)?\s*$"
    if "from champions_phase18_5 import render_champions_profile_v6" not in text:
        text = replace_all_at_least_once(
            text,
            import_pattern,
            "from champions_phase18_5 import render_champions_profile_v6",
            "Phase 18.5 renderer import",
            re.MULTILINE,
        )
    else:
        # If the new import already exists, remove any stale duplicate legacy imports.
        text = re.sub(import_pattern, "", text, flags=re.MULTILINE)

    call_pattern = r"(?ms)^        render_champions_profile_v5\(\n.*?^        \)\n"
    if "render_champions_profile_v6(" not in text:
        replacement = '''        render_champions_profile_v6(\n            slot_name,\n            meta=meta,\n            sprite_resolver=get_mini_sprite_url,\n            base_stats=mon_data.get("stats"),\n            sp_values=slot.get("evs") or {},\n        )\n'''
        text = replace_once(text, call_pattern, replacement, "Phase 18.5 profile call")

    # Replace the legacy 252-EV input block with Champions SP controls.
    if '##### 📊 Champions SP Allocation' not in text:
        ev_pattern = r'(?ms)^\s*strlit\.markdown\("##### 📊 Effort Values \(EV Spread\)"\).*?(?=^\s*strlit\.markdown\("##### Type matchup"\))'
        sp_block = '''            strlit.markdown("##### 📊 Champions SP Allocation")\n            sp_cols = col_set.columns(3)\n            sp_keys = ["HP", "Atk", "Def", "SpA", "SpD", "Spe"]\n            sp_labels = ["HP", "Attack", "Defense", "Sp. Atk", "Sp. Def", "Speed"]\n            if "evs" not in slot or not isinstance(slot["evs"], dict):\n                slot["evs"] = {k: 0 for k in sp_keys}\n            current_sp = {k: max(0, min(32, int(slot["evs"].get(k, 0) or 0))) for k in sp_keys}\n            used_sp = sum(current_sp.values())\n            for idx, (key, label) in enumerate(zip(sp_keys, sp_labels)):\n                with sp_cols[idx % 3]:\n                    other_sp = used_sp - current_sp[key]\n                    max_allowed = min(32, 66 - other_sp)\n                    current_value = current_sp[key]\n                    new_value = strlit.number_input(\n                        label, min_value=0, max_value=max_allowed, step=1,\n                        value=min(current_value, max_allowed), key=f"stat_sp_{i}_{key}"\n                    )\n                    current_sp[key] = int(new_value)\n                    slot["evs"][key] = int(new_value)\n                    used_sp = other_sp + int(new_value)\n            strlit.caption(f"Champions SP: {sum(current_sp.values())}/66 total · maximum 32 per stat")\n\n'''
        text = replace_once(text, ev_pattern, sp_block, "Champions SP controls")

    APP.write_text(text, encoding="utf-8")
    print("Phase 18.5 patch applied successfully to app.py")
    print("Unified profile, tournament-led display viability, prominent base stats, SP highlighting, larger sprites, and no-data state enabled.")
    print("Existing Strategizer scoring engine remains unchanged.")


if __name__ == "__main__":
    main()
