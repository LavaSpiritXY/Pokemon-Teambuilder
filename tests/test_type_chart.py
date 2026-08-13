import unittest

from champions.constants import TYPE_CHART_DATA
from champions.type_chart import (
    get_offensive_type_summary,
    get_type_defense_summary,
    get_type_relationships,
)


class TypeChartTests(unittest.TestCase):
    def test_fire_relationships(self):
        relations = get_type_relationships("Fire")

        self.assertIn(
            {"name": "grass"},
            relations["double_damage_to"],
        )
        self.assertIn(
            {"name": "water"},
            relations["half_damage_to"],
        )

    def test_ground_immunity(self):
        relations = get_type_relationships("Electric")

        self.assertIn(
            {"name": "ground"},
            relations["no_damage_to"],
        )

    def test_reverse_relationships(self):
        defense = get_type_defense_summary("Water")

        self.assertIn("electric", defense["double_damage_from"])
        self.assertIn("fire", defense["half_damage_from"])

    def test_offensive_summary_matches_chart(self):
        for attacking_type, matchups in TYPE_CHART_DATA.items():
            summary = get_offensive_type_summary(attacking_type)

            for defending_type, multiplier in matchups.items():
                normalized = defending_type.lower()

                if multiplier == 2.0:
                    self.assertIn(normalized, summary["double"])
                elif multiplier == 0.5:
                    self.assertIn(normalized, summary["half"])
                elif multiplier == 0.0:
                    self.assertIn(normalized, summary["immune"])


if __name__ == "__main__":
    unittest.main()
