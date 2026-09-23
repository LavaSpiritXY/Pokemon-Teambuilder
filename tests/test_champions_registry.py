from champions.registry import REGISTRY_SCHEMA_VERSION, validate_registry
from tools.sync_champions_registry import _display_name, _parse_top_level_entries


def _sample_registry():
    return {
        "schema_version": REGISTRY_SCHEMA_VERSION,
        "current_regulation": "M-C",
        "detected_regulations": ["M-A", "M-B", "M-C"],
        "species": {
            "charizard": {
                "display_name": "Charizard",
                "base_species_key": "charizard",
                "forme": "",
                "types": ["Fire", "Flying"],
                "base_stats": {
                    "hp": 78,
                    "atk": 84,
                    "def": 78,
                    "spa": 109,
                    "spd": 85,
                    "spe": 100,
                },
                "abilities": ["Blaze"],
                "required_item": None,
                "is_mega": False,
            },
            "charizardmegay": {
                "display_name": "Mega Charizard Y",
                "base_species_key": "charizard",
                "forme": "Mega-Y",
                "types": ["Fire", "Flying"],
                "base_stats": {
                    "hp": 78,
                    "atk": 104,
                    "def": 78,
                    "spa": 159,
                    "spd": 115,
                    "spe": 100,
                },
                "abilities": ["Drought"],
                "required_item": "Charizardite Y",
                "is_mega": True,
            },
        },
        "megas": {
            "charizardmegay": {
                "display_name": "Mega Charizard Y",
                "base_species_key": "charizard",
                "forme": "Mega-Y",
                "types": ["Fire", "Flying"],
                "base_stats": {
                    "hp": 78,
                    "atk": 104,
                    "def": 78,
                    "spa": 159,
                    "spd": 115,
                    "spe": 100,
                },
                "abilities": ["Drought"],
                "required_item": "Charizardite Y",
                "is_mega": True,
            }
        },
        "mega_stones": ["Charizardite Y"],
        "base_roster": ["Charizard"],
        "champions_species_keys": ["charizard"],
        "sources": {},
    }


def test_registry_schema_validation():
    validate_registry(_sample_registry())


def test_registry_rejects_missing_mega_item():
    payload = _sample_registry()
    payload["megas"]["charizardmegay"]["required_item"] = None

    try:
        validate_registry(payload)
    except ValueError as exc:
        assert "required item" in str(exc)
    else:
        raise AssertionError("Expected missing Mega item to fail validation")


def test_showdown_entry_parser_handles_nested_objects():
    source = '''
export const Pokedex = {
    charizard: {
        baseStats: { hp: 78, atk: 84, def: 78, spa: 109, spd: 85, spe: 100 },
        abilities: { 0: "Blaze" },
    },
    charizardmegay: {
        baseStats: { hp: 78, atk: 104, def: 78, spa: 159, spd: 115, spe: 100 },
        abilities: { 0: "Drought" },
    },
};
'''
    parsed = _parse_top_level_entries(source)
    assert set(parsed) == {"charizard", "charizardmegay"}
    assert "baseStats" in parsed["charizard"]
    assert "abilities" in parsed["charizard"]


def test_mega_display_name_normalisation():
    assert _display_name(
        "Absol-Mega-Z",
        "absolmegaz",
        "Absol",
        "Mega-Z",
    ) == "Mega Absol Z"


def test_legacy_mega_view_comes_from_generated_registry():
    from champions.constants import CUSTOM_MEGAS_DATA

    for name in (
        "Mega Absol Z",
        "Mega Salamence",
        "Mega Garchomp Z",
        "Mega Lucario Z",
        "Mega Golisopod",
        "Mega Baxcalibur",
    ):
        assert name in CUSTOM_MEGAS_DATA
        assert CUSTOM_MEGAS_DATA[name]["ability"]
