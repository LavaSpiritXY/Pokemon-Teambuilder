from champions.constants import BASE_HELD_ITEMS
from champions.item_data import (
    CHAMPIONS_HELD_ITEMS,
    MEGA_STONE_MAP,
    get_champions_held_items,
    is_champions_item,
    normalize_item_name,
)


def test_champions_item_pool_excludes_known_legacy_only_items():
    assert "Assault Vest" not in CHAMPIONS_HELD_ITEMS
    assert "Choice Band" not in CHAMPIONS_HELD_ITEMS
    assert "Choice Specs" not in CHAMPIONS_HELD_ITEMS
    assert "Heavy-Duty Boots" not in CHAMPIONS_HELD_ITEMS
    assert "Eviolite" not in CHAMPIONS_HELD_ITEMS


def test_champions_item_pool_contains_current_core_items():
    for item in ("Focus Sash", "Sitrus Berry", "Life Orb", "Leftovers", "Choice Scarf"):
        assert is_champions_item(item)


def test_legacy_pool_is_not_used_as_the_legality_source():
    assert "Assault Vest" in BASE_HELD_ITEMS
    assert not is_champions_item("Assault Vest")


def test_mega_stones_align_with_supported_mega_roster():
    assert MEGA_STONE_MAP["Mega Charizard Y"] == "Charizardite Y"
    assert MEGA_STONE_MAP["Mega Raichu Y"] == "Raichunite Y"
    assert MEGA_STONE_MAP["Mega Excadrill"] == "Excadrite"
    assert is_champions_item("Charizardite Y")


def test_item_normalisation_handles_common_variants():
    assert normalize_item_name("  King's   Rock ") == "King's Rock"
    assert normalize_item_name("never melt ice") == "Never-Melt Ice"
    assert normalize_item_name("") == ""
