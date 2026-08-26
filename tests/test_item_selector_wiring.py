from pathlib import Path


def test_app_uses_champions_item_registry():
    text = Path("app.py").read_text(encoding="utf-8")
    assert "from champions.item_data import (" in text
    assert "CHAMPIONS_HELD_ITEMS" in text
    assert "MEGA_STONE_MAP" in text
    assert "BASE_HELD_ITEMS" not in text
    assert "CHAMPIONS_HELD_ITEMS = sorted(list(set(BASE_HELD_ITEMS" not in text
