"""Showdown team import/export helpers for the Champions teambuilder."""

import re


def export_slot_to_showdown(slot):
    """Convert one team slot dictionary to Showdown text."""
    if not slot or slot.get("name", "-- Choose a Pokémon --") == "-- Choose a Pokémon --":
        return ""

    lines = []
    item_str = f" @ {slot['item']}" if slot.get("item") else ""
    lines.append(f"{slot['name']}{item_str}")

    if slot.get("ability"):
        lines.append(f"Ability: {slot['ability']}")

    ev_parts = []
    for key in ["HP", "Atk", "Def", "SpA", "SpD", "Spe"]:
        value = slot.get("evs", {}).get(key, 0)
        if value > 0:
            ev_parts.append(f"{value} {key}")
    if ev_parts:
        lines.append(f"EVs: {' / '.join(ev_parts)}")

    if slot.get("nature"):
        nature_name = slot["nature"].split(" ")[0]
        lines.append(f"{nature_name} Nature")

    for move in slot.get("moves", []):
        if move:
            lines.append(f"- {move}")

    return "\n".join(lines)


def export_team_to_showdown(team_slots):
    """Convert the six-slot team state into Showdown text."""
    exported = []
    for index in range(6):
        slot = team_slots.get(index)
        if slot and slot.get("name") != "-- Choose a Pokémon --":
            exported.append(export_slot_to_showdown(slot))
    return "\n\n".join(exported)


def parse_showdown_text(text, champions_all_forms, natures, mega_stone_map):
    """Parse Showdown text into the app's normalized slot dictionaries."""
    blocks = [block.strip() for block in text.strip().split("\n\n") if block.strip()]
    parsed_slots = []

    for block in blocks[:6]:
        lines = [line.strip() for line in block.split("\n") if line.strip()]
        if not lines:
            continue

        line1 = lines[0]
        item = ""
        if " @ " in line1:
            line1_parts = line1.split(" @ ", 1)
            item = line1_parts[1].strip()
            name_part = line1_parts[0].strip()
        else:
            name_part = line1.strip()

        species = name_part
        if "(" in name_part and ")" in name_part:
            match = re.search(r"\(([^)]+)\)", name_part)
            if match:
                potential_species = match.group(1).strip()
                if potential_species not in ["M", "F"]:
                    species = potential_species
                else:
                    species = name_part.split("(")[0].strip()

        matched_species = "-- Choose a Pokémon --"
        for option in champions_all_forms:
            if option.lower() == species.lower():
                matched_species = option
                break
        if matched_species == "-- Choose a Pokémon --":
            for option in champions_all_forms:
                if species.lower() in option.lower():
                    matched_species = option
                    break

        ability = "Standard"
        nature = "Hardy"
        evs = {"HP": 0, "Atk": 0, "Def": 0, "SpA": 0, "SpD": 0, "Spe": 0}
        moves = []

        for line in lines[1:]:
            if line.startswith("Ability:"):
                ability = line.replace("Ability:", "", 1).strip()
            elif line.startswith("EVs:"):
                ev_string = line.replace("EVs:", "", 1).strip()
                for part in ev_string.split("/"):
                    pieces = part.strip().split()
                    if len(pieces) == 2 and pieces[0].isdigit():
                        stat_key = pieces[1].strip()
                        if stat_key in evs:
                            evs[stat_key] = int(pieces[0])
            elif "Nature" in line:
                nature_word = line.replace("Nature", "").strip()
                for option in natures:
                    if option.startswith(nature_word):
                        nature = option
                        break
            elif line.startswith("-"):
                move_name = line.replace("-", "", 1).strip()
                if move_name:
                    moves.append(move_name)

        final_species = matched_species if matched_species != "-- Choose a Pokémon --" else species.title()
        parsed_slots.append({
            "name": final_species,
            "ability": ability,
            "item": item if item else mega_stone_map.get(final_species, "Focus Sash"),
            "nature": nature,
            "moves": moves[:4] if moves else ["Protect", "Substitute", "Rest", "Toxic"],
            "evs": evs,
        })

    return parsed_slots
