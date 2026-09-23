#!/usr/bin/env python3
"""Generate the canonical Pokemon Champions registry from Showdown data."""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests


REPO_ROOT = Path(__file__).resolve().parents[1]
REGISTRY_PATH = REPO_ROOT / "champions_registry.json"
HISTORY_PATH = REPO_ROOT / "champions_meta_history.json"

POKEDEX_URL = (
    "https://raw.githubusercontent.com/smogon/pokemon-showdown/"
    "master/data/pokedex.ts"
)
CHAMPIONS_LEARNSETS_URL = (
    "https://raw.githubusercontent.com/smogon/pokemon-showdown/"
    "master/data/mods/champions/learnsets.ts"
)

REQUEST_TIMEOUT_SECONDS = 30
REGULATION_RE = re.compile(r"^M-[A-Z0-9]+$")


def _fetch_text(url: str) -> str:
    response = requests.get(
        url,
        timeout=REQUEST_TIMEOUT_SECONDS,
        headers={"User-Agent": "Pokemon-Champions-Strategizer/registry-sync"},
    )
    response.raise_for_status()
    if not response.text.strip():
        raise ValueError(f"Upstream source was empty: {url}")
    return response.text


def _to_id(value: Any) -> str:
    return re.sub(r"[^a-z0-9]", "", str(value or "").casefold())


def _quoted_value(block: str, field: str) -> Optional[str]:
    match = re.search(
        rf"""\b{re.escape(field)}\s*:\s*(?:"([^"]*)"|'([^']*)')""",
        block,
    )
    if not match:
        return None
    return (match.group(1) or match.group(2) or "").strip()


def _quoted_list(block: str, field: str) -> List[str]:
    match = re.search(
        rf"""\b{re.escape(field)}\s*:\s*\[([^\]]*)\]""",
        block,
        flags=re.DOTALL,
    )
    if not match:
        return []

    values = re.findall(r'''(?:"([^"]*)"|'([^']*)')''', match.group(1))
    return [
        (first or second).strip()
        for first, second in values
        if (first or second).strip()
    ]


def _numeric_object(block: str, field: str) -> Dict[str, int]:
    match = re.search(
        rf"""\b{re.escape(field)}\s*:\s*\{{([^{{}}]*)\}}""",
        block,
        flags=re.DOTALL,
    )
    if not match:
        return {}

    output: Dict[str, int] = {}
    for key, value in re.findall(
        r"""\b([a-z]+)\s*:\s*(-?\d+)\b""",
        match.group(1),
    ):
        output[key] = int(value)
    return output


def _ability_names(block: str) -> List[str]:
    match = re.search(
        r"""\babilities\s*:\s*\{([^{}]*)\}""",
        block,
        flags=re.DOTALL,
    )
    if not match:
        return []

    values = re.findall(r'''(?:"([^"]*)"|'([^']*)')''', match.group(1))
    output: List[str] = []
    for first, second in values:
        value = (first or second).strip()
        if value and value not in output:
            output.append(value)
    return output


def _parse_top_level_entries(source: str) -> Dict[str, str]:
    """Parse Showdown top-level species blocks using brace depth."""
    entries: Dict[str, str] = {}
    current_id: Optional[str] = None
    current_lines: List[str] = []
    depth = 0
    entry_pattern = re.compile(r"""^\s*([a-z0-9]+)\s*:\s*\{\s*$""")

    for line in source.splitlines():
        if current_id is None:
            match = entry_pattern.match(line)
            if not match:
                continue
            current_id = match.group(1)
            current_lines = [line]
            depth = line.count("{") - line.count("}")
            continue

        current_lines.append(line)
        depth += line.count("{") - line.count("}")

        if depth <= 0:
            entries[current_id] = "\n".join(current_lines)
            current_id = None
            current_lines = []
            depth = 0

    if current_id is not None:
        raise ValueError(f"Unterminated upstream entry: {current_id}")

    return entries


def _display_name(
    source_name: str,
    species_id: str,
    base_species: Optional[str],
    forme: Optional[str],
) -> str:
    raw = str(source_name or "").strip() or species_id

    if forme and forme.casefold().startswith("mega"):
        base = str(base_species or raw).strip()
        suffix = ""
        match = re.search(r"""mega[- ]*([xyz])$""", forme, flags=re.IGNORECASE)
        if match:
            suffix = f" {match.group(1).upper()}"
        return f"Mega {base}{suffix}"

    pretty = raw.replace("-", " ").replace("_", " ")
    special = {
        "Mr Mime": "Mr. Mime",
        "Mime Jr": "Mime Jr.",
        "Farfetchd": "Farfetch'd",
        "Sirfetchd": "Sirfetch'd",
        "Ho Oh": "Ho-Oh",
        "Flabebe": "Flabébé",
        "Type Null": "Type: Null",
    }

    if pretty.casefold().endswith(" f"):
        prefix = pretty.rsplit(" ", 1)[0]
        if prefix.casefold() in {"indeedee", "meowstic", "oinkologne"}:
            return f"{prefix} Female"

    if pretty.casefold().endswith(" m"):
        prefix = pretty.rsplit(" ", 1)[0]
        if prefix.casefold() in {"indeedee", "meowstic", "oinkologne"}:
            return f"{prefix} Male"

    return special.get(pretty, " ".join(part.title() for part in pretty.split()))


def _history_metadata() -> tuple[Optional[str], List[str]]:
    if not HISTORY_PATH.exists():
        return None, []

    try:
        payload = json.loads(HISTORY_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None, []

    if not isinstance(payload, dict):
        return None, []

    current = str(payload.get("active_regulation") or "").strip().upper()
    current = current if REGULATION_RE.fullmatch(current) else None

    detected_values = payload.get("detected_regulations") or []
    detected = sorted(
        {
            value
            for value in (
                str(item or "").strip().upper()
                for item in detected_values
            )
            if REGULATION_RE.fullmatch(value)
        }
    )
    return current, detected


def build_registry() -> Dict[str, Any]:
    pokedex_source = _fetch_text(POKEDEX_URL)
    learnsets_source = _fetch_text(CHAMPIONS_LEARNSETS_URL)

    pokedex_blocks = _parse_top_level_entries(pokedex_source)
    champions_species = set(_parse_top_level_entries(learnsets_source))

    if not pokedex_blocks:
        raise ValueError("No Pokedex entries were parsed from upstream.")
    if not champions_species:
        raise ValueError("No Champions learnset species were parsed from upstream.")

    parsed: Dict[str, Dict[str, Any]] = {}

    for species_id, block in pokedex_blocks.items():
        base_species = _quoted_value(block, "baseSpecies")
        forme = _quoted_value(block, "forme")

        base_species_key = _to_id(base_species or species_id)
        is_mega = bool(
            (forme and forme.casefold().startswith("mega"))
            or re.search(
                r"""mega(?:x|y|z)?$""",
                species_id,
                flags=re.IGNORECASE,
            )
        )

        is_champions_species = species_id in champions_species
        is_champions_mega = is_mega and base_species_key in champions_species

        if not (is_champions_species or is_champions_mega):
            continue

        stats = _numeric_object(block, "baseStats")
        abilities = _ability_names(block)
        types = _quoted_list(block, "types")

        required_stats = {"hp", "atk", "def", "spa", "spd", "spe"}
        missing_stats = required_stats - stats.keys()
        if missing_stats:
            raise ValueError(
                f"Missing base stats for Champions species {species_id!r}: "
                f"{', '.join(sorted(missing_stats))}"
            )
        if not types:
            raise ValueError(f"Missing type data for Champions species {species_id!r}.")
        if not abilities:
            raise ValueError(
                f"Missing ability data for Champions species {species_id!r}."
            )

        parsed[species_id] = {
            "display_name": _display_name(
                _quoted_value(block, "name") or species_id,
                species_id,
                base_species,
                forme,
            ),
            "base_species_key": base_species_key,
            "forme": forme or "",
            "types": types,
            "base_stats": {
                key: stats[key]
                for key in ("hp", "atk", "def", "spa", "spd", "spe")
            },
            "abilities": abilities,
            "required_item": _quoted_value(block, "requiredItem"),
            "is_mega": is_mega,
        }

    if not parsed:
        raise ValueError("No Champions species survived registry filtering.")

    base_roster = sorted(
        {
            entry["display_name"]
            for entry in parsed.values()
            if not entry["is_mega"]
        },
        key=str.casefold,
    )

    megas = {
        key: entry
        for key, entry in parsed.items()
        if entry["is_mega"]
    }

    mega_stones = sorted(
        {
            str(entry["required_item"]).strip()
            for entry in megas.values()
            if entry.get("required_item")
        },
        key=str.casefold,
    )

    current_regulation, detected_regulations = _history_metadata()

    return {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "sources": {
            "pokedex": POKEDEX_URL,
            "champions_learnsets": CHAMPIONS_LEARNSETS_URL,
        },
        "current_regulation": current_regulation,
        "detected_regulations": detected_regulations,
        "species": dict(sorted(parsed.items())),
        "megas": dict(sorted(megas.items())),
        "mega_stones": mega_stones,
        "base_roster": base_roster,
        "champions_species_keys": sorted(champions_species),
    }


def write_registry(payload: Dict[str, Any], path: Path = REGISTRY_PATH) -> None:
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def refresh_regulation_metadata(path: Path = REGISTRY_PATH) -> None:
    if not path.exists():
        raise FileNotFoundError(path)

    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("Existing registry is not a JSON object.")

    current_regulation, detected_regulations = _history_metadata()
    payload["current_regulation"] = current_regulation
    payload["detected_regulations"] = detected_regulations
    payload["generated_at"] = datetime.now(timezone.utc).isoformat()
    write_registry(payload, path)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--refresh-regulation-only", action="store_true")
    args = parser.parse_args()

    if args.refresh_regulation_only:
        refresh_regulation_metadata()
        print("Updated Champions registry regulation metadata.")
        return 0

    payload = build_registry()

    from champions.registry import validate_registry

    validate_registry(payload)
    write_registry(payload)

    print("=== Champions registry sync ===")
    print(f"Species/forms registered: {len(payload['species'])}")
    print(f"Mega forms registered: {len(payload['megas'])}")
    print(f"Mega Stones registered: {len(payload['mega_stones'])}")
    print(f"Base roster entries: {len(payload['base_roster'])}")
    print(f"Current regulation: {payload.get('current_regulation') or 'unknown'}")
    print(
        "Detected regulations: "
        f"{', '.join(payload.get('detected_regulations', [])) or 'none'}"
    )
    print(f"Wrote: {REGISTRY_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
