from pathlib import Path
import re


def main() -> None:
    path = Path("app.py")
    text = path.read_text(encoding="utf-8")

    # Match the active EV/SP editor by its stable section header and the
    # following input loop, rather than requiring one exact previous patch.
    pattern = re.compile(
        r'''(?ms)^            strlit\.markdown\("##### (?:📊 )?(?:Effort Values \(EV Spread\)|Champions SP Allocation)"\)\n'
        r'''            ev_cols = col_set\.columns\(3\)\n'
        r'''            ev_keys = \["HP", "Atk", "Def", "SpA", "SpD", "Spe"\]\n'
        r'''            ev_labels = \["HP", "Attack", "Defense", "Sp\. Atk", "Sp\. Def", "Speed"\]\n'
        r'''            if "evs" not in slot or not isinstance\(slot\["evs"\], dict\):\n'
        r'''                slot\["evs"\] = \{k: 0 for k in ev_keys\}\n\n'
        r'''            for idx, \(key, label\) in enumerate\(zip\(ev_keys, ev_labels\)\):\n'
        r'''                with ev_cols\[idx % 3\]:\n'
        r'''                    slot\["evs"\]\[key\] = strlit\.number_input\(\n'
        r'''                        label, min_value=0, max_value=252, step=4,\n'
        r'''                        value=slot\["evs"\]\.get\(key, 0\), key=f"stat_ev_\{i\}_\{key\}"\n'
        r'''                    \)\n'''
    )

    replacement = '''            strlit.markdown("##### 📊 Champions SP Allocation")
            ev_cols = col_set.columns(3)
            ev_keys = ["HP", "Atk", "Def", "SpA", "SpD", "Spe"]
            ev_labels = ["HP", "Attack", "Defense", "Sp. Atk", "Sp. Def", "Speed"]
            if "evs" not in slot or not isinstance(slot["evs"], dict):
                slot["evs"] = {k: 0 for k in ev_keys}

            # Pokémon Champions uses Specialisation Points (SP):
            # at most 32 SP in one stat and 66 SP total.
            sp_total_cap = 66
            sp_per_stat_cap = 32

            for idx, (key, label) in enumerate(zip(ev_keys, ev_labels)):
                with ev_cols[idx % 3]:
                    other_sp = sum(
                        int(slot["evs"].get(k, 0) or 0)
                        for k in ev_keys
                        if k != key
                    )
                    allowed_max = min(
                        sp_per_stat_cap,
                        max(0, sp_total_cap - other_sp)
                    )
                    current_value = min(
                        int(slot["evs"].get(key, 0) or 0),
                        allowed_max
                    )
                    slot["evs"][key] = strlit.number_input(
                        label,
                        min_value=0,
                        max_value=allowed_max,
                        step=1,
                        value=current_value,
                        key=f"stat_ev_{i}_{key}"
                    )

            # Clamp legacy session-state values defensively.
            for key in ev_keys:
                slot["evs"][key] = min(
                    sp_per_stat_cap,
                    max(0, int(slot["evs"].get(key, 0) or 0))
                )

            total_sp = sum(int(slot["evs"].get(k, 0) or 0) for k in ev_keys)
            if total_sp > sp_total_cap:
                overflow = total_sp - sp_total_cap
                for key in reversed(ev_keys):
                    reduction = min(
                        int(slot["evs"].get(key, 0) or 0),
                        overflow
                    )
                    slot["evs"][key] = int(slot["evs"].get(key, 0) or 0) - reduction
                    overflow -= reduction
                    if overflow <= 0:
                        break

            strlit.caption(
                f"Champions SP: {sum(int(slot['evs'].get(k, 0) or 0) for k in ev_keys)}/{sp_total_cap} total · {sp_per_stat_cap} max per stat"
            )
'''

    matches = list(pattern.finditer(text))
    if len(matches) != 1:
        raise RuntimeError(
            f"Expected exactly one active EV/SP editor block, found {len(matches)}."
        )

    text = pattern.sub(replacement, text, count=1)
    path.write_text(text, encoding="utf-8")

    print("Champions SP limits fixed in app.py")
    print("Per-stat cap: 32")
    print("Team-slot total cap: 66")


if __name__ == "__main__":
    main()
