import re
from typing import Dict, Optional

import requests


SMOGON_USAGE_DB: Dict[str, dict] = {}


def fetch_smogon_usage_stats(display_name_for_move) -> Dict[str, dict]:
    """Fetch competitive usage statistics from Smogon's public Chaos JSON data."""
    url = "https://smogon.com/stats/2024-05/chaos/gen9ou-1825.json"
    usage_map = {}

    try:
        res = requests.get(url, timeout=15)
        if res.status_code != 200:
            return {}

        data = res.json()
        total_battles = max(1, data.get("info", {}).get("number of battles", 10000))

        for raw_name, details in data.get("data", {}).items():
            clean_key = raw_name.strip().lower()
            usage_count = details.get("usage", 0)
            meta_usage_tier = min(1.0, (usage_count / total_battles) * 2.0)

            raw_moves = details.get("Moves", {})
            move_sum = sum(raw_moves.values()) or 1
            common_moves_rates = {
                display_name_for_move(m_key): round(cnt / move_sum, 3)
                for m_key, cnt in raw_moves.items()
                if (cnt / move_sum) > 0.02
            }

            raw_abilities = details.get("Abilities", {})
            ab_sum = sum(raw_abilities.values()) or 1
            common_abilities_rates = {
                ab_name: round(cnt / ab_sum, 3)
                for ab_name, cnt in raw_abilities.items()
            }

            raw_items = details.get("Items", {})
            item_sum = sum(raw_items.values()) or 1
            common_items_rates = {
                item_name: round(cnt / item_sum, 3)
                for item_name, cnt in raw_items.items()
            }

            raw_teammates = details.get("Teammates", {})
            top_partners_rates = {
                tm_name.title(): min(1.0, val / usage_count)
                for tm_name, val in raw_teammates.items()
                if usage_count > 0 and (val / usage_count) > 0.05
            }

            usage_map[clean_key] = {
                "meta_usage_tier": meta_usage_tier,
                "common_moves": common_moves_rates,
                "common_abilities": common_abilities_rates,
                "common_items": common_items_rates,
                "top_partners": top_partners_rates,
            }

        return usage_map
    except Exception:
        return {}


def set_smogon_usage_db(usage_db: Optional[Dict[str, dict]]) -> None:
    global SMOGON_USAGE_DB
    SMOGON_USAGE_DB = usage_db or {}


def get_smogon_stats_for(mon_name: str) -> dict:
    if not mon_name:
        return {
            "meta_usage_tier": 0.15,
            "common_moves": {},
            "common_abilities": {},
            "common_items": {},
            "top_partners": {},
        }

    clean = mon_name.strip().lower()
    if clean in SMOGON_USAGE_DB:
        return SMOGON_USAGE_DB[clean]

    base = re.sub(r"^mega\s+", "", clean).strip()
    if base in SMOGON_USAGE_DB:
        return SMOGON_USAGE_DB[base]

    return {
        "meta_usage_tier": 0.15,
        "common_moves": {},
        "common_abilities": {},
        "common_items": {},
        "top_partners": {},
    }
