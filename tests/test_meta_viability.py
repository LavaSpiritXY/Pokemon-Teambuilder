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

    def test_current_regulation_metrics_are_used_when_score_is_absent(self):
        result = calculate_meta_viability(
            {
                "name": "Examplemon",
                "abilities": [],
                "moves": [],
                "default_score": 50,
            },
            tournament_metrics={
                "current": {
                    "regulation": "M-B",
                    "appearances": 100,
                    "win_rate": 0.60,
                    "top_cut_rate": 0.125,
                }
            },
            external_stats={"meta_usage_tier": None},
        )
        # 60% win rate + 12.5% top-cut rate produce a 60% tournament
        # signal, so the result must not silently fall back to the 50 baseline.
        self.assertEqual(result["viability_index"], 58)


if __name__ == "__main__":
    unittest.main()
