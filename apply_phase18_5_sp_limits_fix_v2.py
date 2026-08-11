from pathlib import Path
import re

APP = Path("app.py")


def main():
    text = APP.read_text(encoding="utf-8")

    pattern = re.compile(
        r'''(?P<indent>            )current_sp = \{k: max\(0, min\(32, int\(slot\["evs"\]\.get\(k, 0\) or 0\)\)\) for k in sp_keys\}\n'''
        r'''(?P=indent)used_sp = sum\(current_sp\.values\(\)\)\n'''
        r'''(?P=indent)for idx, \(key, label\) in enumerate\(zip\(sp_keys, sp_labels\)\):\n'''
        r'''(?P=indent)    with sp_cols\[idx % 3\]:\n'''
        r'''(?P=indent)        other_sp = used_sp - current_sp\[key\]\n'''
        r'''(?P=indent)        max_allowed = min\(32, 66 - other_sp\)\n'''
        r'''(?P=indent)        current_value = current_sp\[key\]\n'''
        r'''(?P=indent)        new_value = strlit\.number_input\(\n'''
        r'''(?P=indent)            label, min_value=0, max_value=max_allowed, step=1,\n'''
        r'''(?P=indent)            value=min\(current_value, max_allowed\), key=f"stat_sp_\{i\}_\{key\}"\n'''
        r'''(?P=indent)        \)\n'''
        r'''(?P=indent)        current_sp\[key\] = int\(new_value\)\n'''
        r'''(?P=indent)        slot\["evs"\]\[key\] = int\(new_value\)\n'''
        r'''(?P=indent)        used_sp = other_sp \+ int\(new_value\)\n'''
        r'''(?P=indent)strlit\.caption\(f"Champions SP: \{sum\(current_sp\.values\(\)\)\}/66 total · maximum 32 per stat"\)''',
        re.MULTILINE,
    )

    replacement = '''            sp_per_stat_cap = 32
            sp_total_cap = 66
            current_sp = {k: max(0, min(sp_per_stat_cap, int(slot["evs"].get(k, 0) or 0))) for k in sp_keys}
            used_sp = sum(current_sp.values())
            for idx, (key, label) in enumerate(zip(sp_keys, sp_labels)):
                with sp_cols[idx % 3]:
                    other_sp = used_sp - current_sp[key]
                    remaining = sp_total_cap - other_sp
                    max_allowed = min(sp_per_stat_cap, remaining)
                    current_value = current_sp[key]
                    new_value = strlit.number_input(
                        label, min_value=0, max_value=max_allowed, step=1,
                        value=min(current_value, max_allowed), key=f"stat_sp_{i}_{key}"
                    )
                    current_sp[key] = int(new_value)
                    slot["evs"][key] = int(new_value)
                    used_sp = other_sp + int(new_value)
            strlit.caption(f"Champions SP: {sum(current_sp.values())}/{sp_total_cap} total · maximum {sp_per_stat_cap} per stat")'''

    matches = list(pattern.finditer(text))
    if len(matches) != 1:
        raise RuntimeError(f"Expected current Phase 18.5 SP block exactly once; found {len(matches)}")

    text = pattern.sub(replacement, text, count=1)
    APP.write_text(text, encoding="utf-8")
    print("Phase 18.5 SP limits fixed: 32 per stat / 66 total")


if __name__ == "__main__":
    main()
