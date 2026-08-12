from pathlib import Path
import re
import shutil
from datetime import datetime

ROOT = Path(__file__).resolve().parent
APP = ROOT / "app.py"


def backup(path: Path) -> Path:
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    target = path.with_name(f"{path.stem}.phase18_7_backup_{stamp}{path.suffix}")
    shutil.copy2(path, target)
    return target


def patch_tournament_metrics(text: str) -> str:
    start = text.find("def calculate_tournament_metrics(")
    end = text.find("\ndef get_tournament_partners(", start)
    if start < 0 or end < 0:
        raise RuntimeError("Could not locate calculate_tournament_metrics().")

    replacement = '''def calculate_tournament_metrics(pokemon_name):
    """Convert raw Champions tournament evidence into roster-relative metrics.

    Usage is normalized against the most-used Pokémon actually present in the
    Champions dataset rather than an arbitrary fixed denominator. This keeps
    the index meaningful as the dataset grows.
    """
    key = get_champions_species_key(pokemon_name)
    record = CHAMPIONS_META_DB.get(key)

    empty = {
        "usage": 0.0,
        "top_cut_rate": 0.0,
        "win_rate": 0.0,
        "placement_score": 0.0,
        "partner_score": 0.0,
        "tournament_score": 0.0,
    }
    if not record:
        return empty

    appearances = max(0, int(record.get("appearances", 0) or 0))
    if appearances == 0:
        return empty

    active_records = [
        r for r in CHAMPIONS_META_DB.values()
        if int(r.get("appearances", 0) or 0) > 0
    ]
    max_appearances = max(
        (int(r.get("appearances", 0) or 0) for r in active_records),
        default=appearances,
    )
    usage_score = appearances / max(1, max_appearances)

    top_cuts = max(0, int(record.get("top_cuts", 0) or 0))
    top_cut_rate = min(1.0, top_cuts / appearances)

    wins = max(0, int(record.get("wins", 0) or 0))
    losses = max(0, int(record.get("losses", 0) or 0))
    games = wins + losses
    win_rate = wins / games if games else 0.0

    placement_points = float(record.get("placement_points", 0.0) or 0.0)
    placement_score = min(1.0, placement_points / max(1.0, appearances))

    partner_total = sum(
        max(0, int(v or 0)) for v in (record.get("partners") or {}).values()
    )
    partner_score = min(1.0, partner_total / max(1, appearances * 5))

    # If game-level W/L data is unavailable, do not manufacture a win-rate
    # penalty. Tournament usage + placement evidence remain the signal.
    if games:
        tournament_score = (
            usage_score * 0.35
            + win_rate * 0.25
            + top_cut_rate * 0.20
            + placement_score * 0.15
            + partner_score * 0.05
        )
    else:
        tournament_score = (
            usage_score * 0.40
            + top_cut_rate * 0.25
            + placement_score * 0.30
            + partner_score * 0.05
        )

    return {
        "usage": max(0.0, min(1.0, usage_score)),
        "top_cut_rate": max(0.0, min(1.0, top_cut_rate)),
        "win_rate": max(0.0, min(1.0, win_rate)),
        "placement_score": max(0.0, min(1.0, placement_score)),
        "partner_score": max(0.0, min(1.0, partner_score)),
        "tournament_score": max(0.0, min(1.0, tournament_score)),
    }
'''
    return text[:start] + replacement + text[end:]


def remove_duplicate_ev_editor(text: str) -> str:
    # The legacy editor starts at the Champions SP heading and ends immediately
    # before Type matchup. Different Phase 18.x versions varied in formatting,
    # so anchor on semantic text rather than exact indentation.
    pattern = re.compile(
        r'\n\s*strlit\.markdown\(["\']##### 📊 Champions SP Allocation["\']\)\n'
        r'.*?'
        r'(?=\n\s*strlit\.markdown\(["\']##### Type matchup["\'])',
        re.S,
    )
    new, count = pattern.subn("\n\n", text, count=1)
    if count == 1:
        return new

    # Fallback for the common heading variant without markdown level 5.
    pattern2 = re.compile(
        r'\n\s*strlit\.markdown\(["\']📊 Champions SP Allocation["\']\)\n'
        r'.*?'
        r'(?=\n\s*strlit\.markdown\(["\']##### Type matchup["\'])',
        re.S,
    )
    new, count = pattern2.subn("\n\n", text, count=1)
    if count == 1:
        return new

    return text


def main():
    if not APP.exists():
        raise RuntimeError("app.py was not found. Run this from the repository root.")

    original = APP.read_text(encoding="utf-8")
    patched = patch_tournament_metrics(original)
    patched = remove_duplicate_ev_editor(patched)

    if patched == original:
        raise RuntimeError("No Phase 18.7 changes were identified; app.py was left untouched.")

    backup_path = backup(APP)
    APP.write_text(patched, encoding="utf-8")
    print(f"Backup created: {backup_path.name}")
    print("Phase 18.7 app cleanup applied successfully.")
    print("- Removed legacy duplicate Champions SP editor when present.")
    print("- Rebuilt tournament index around roster-relative usage and placement evidence.")
    print("- Preserved local app.py changes by editing the existing file in place.")
    print("- Restart Streamlit to test the updated UI.")


if __name__ == "__main__":
    main()
