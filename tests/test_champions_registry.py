from champions.registry import (
    REGISTRY_SCHEMA_VERSION,
    get_base_species_for_name,
    get_species_family_key,
    load_registry,
    validate_registry,
)
from tools.sync_champions_registry import (
    _api_slug,
    _canonical_key,
    _display_name,
    _learnset_move_ids,
    _nonstandard_value,
    _object_string_map,
    _parse_top_level_entries,
)


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






def test_modern_mega_sprite_metadata_is_generated():
    registry = load_registry()
    for name in (
        "Mega Absol Z",
        "Mega Garchomp Z",
        "Mega Lucario Z",
        "Mega Golisopod",
        "Mega Salamence",
        "Mega Baxcalibur",
    ):
        entry = next(
            value
            for value in registry["species"].values()
            if value.get("display_name") == name
        )
        assert entry["sprite_id"]
        assert entry["showdown_sprite_url"].endswith(
            f"/{entry['sprite_id']}.png"
        )
        if name.endswith(" Z"):
            assert entry["generation"] == 9

def test_generated_mega_family_resolution():
    assert get_base_species_for_name("Mega Charizard Y")["display_name"] == "Charizard"
    assert get_base_species_for_name("Mega Absol Z")["display_name"] == "Absol"
    assert get_base_species_for_name("Mega Meowstic F")["display_name"] == "Meowstic"
    assert get_species_family_key("Mega Charizard Y") == "charizard"
    assert get_species_family_key("Arcanine Hisui") == "arcanine-hisui"

def test_mega_display_name_normalisation():
    assert _display_name(
        "Absol-Mega-Z",
        "Absol",
        "Mega-Z",
        True,
    ) == "Mega Absol Z"

    assert _display_name(
        "Arcanine-Hisui",
        "Arcanine",
        "Hisui",
        False,
    ) == "Arcanine Hisui"

    assert _display_name(
        "Indeedee-F",
        "Indeedee",
        "F",
        False,
    ) == "Indeedee Female"

    assert _display_name(
        "Futuremon-Zeta",
        "Futuremon",
        "Zeta",
        False,
    ) == "Futuremon Zeta"

    assert _canonical_key("Mega Charizard Y", "charizard") == "charizard-y"
    assert _canonical_key("Tauros Paldea Aqua", "tauros") == "tauros-paldea-aqua"
    assert _api_slug("Arcanine-Hisui", "arcaninehisui", "Arcanine", "Hisui", False) == "arcanine-hisui"
    assert _api_slug("Basculegion-F", "basculegion", "Basculegion", "F", False) == "basculegion-female"


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


def test_learnset_parser_extracts_move_ids():
    block = '''charizard: {
        learnset: {
            protect: ["9M"],
            thunderpunch: ["9M"],
            weatherball: ["9M"],
        },
    },'''
    assert _learnset_move_ids(block) == ["protect", "thunderpunch", "weatherball"]


def test_item_nonstandard_parser_distinguishes_null():
    assert _nonstandard_value('isNonstandard: null,') == (None, True)
    assert _nonstandard_value('isNonstandard: "Past",') == ("Past", True)
    assert _nonstandard_value('inherit: true,') == (None, False)


def test_mega_stone_parser_extracts_target():
    block = 'megaStone: { "Absol": "Absol-Mega-Z" },'
    assert _object_string_map(block, "megaStone") == {
        "Absol": "Absol-Mega-Z"
    }
