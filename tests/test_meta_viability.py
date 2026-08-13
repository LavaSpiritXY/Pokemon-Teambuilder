import unittest

from champions.meta_viability import calculate_meta_viability


class MetaViabilityTests(unittest.TestCase):
    def test_missing_external_signal_does_not_zero_score(self):
        result = calculate_meta_viability(
            {
                "name": "Examplemon",
                "abilities": [],
                "moves": [],
                "default_score": 70,
            },
            external_stats={"meta_usage_tier": None},
        )
        self.assertEqual(result["viability_index"], 70)

    def test_tournament_signal_dominates_external_signal(self):
        result = calculate_meta_viability(
            {
                "name": "Examplemon",
                "abilities": [],
                "moves": [],
                "default_score": 50,
            },
            tournament_metrics={"tournament_score": 1.0},
            external_stats={"meta_usage_tier": 0.0},
        )
        self.assertEqual(result["viability_index"], 80)


if __name__ == "__main__":
    unittest.main()
