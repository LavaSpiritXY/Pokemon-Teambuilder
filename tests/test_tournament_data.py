import unittest

from champions.constants import CURRENT_REGULATION
from champions.tournament_data import (
    CHAMPIONS_META_DB,
    calculate_tournament_metrics,
    get_tournament_partners,
    import_champions_tournament,
)


class TournamentDataTests(unittest.TestCase):
    def setUp(self):
        CHAMPIONS_META_DB.clear()

    def tearDown(self):
        CHAMPIONS_META_DB.clear()

    def test_missing_match_record_keeps_win_rate_unknown(self):
        import_champions_tournament({
            "regulation": CURRENT_REGULATION,
            "players": [
                {"team": ["Whimsicott", "Farigiraf"], "placing": 1}
            ],
        })

        metrics = calculate_tournament_metrics("Whimsicott")

        self.assertIsNone(metrics["win_rate"])
        self.assertFalse(metrics["win_rate_available"])
        self.assertEqual(metrics["top_cut_rate"], 1.0)

    def test_explicit_match_record_is_preserved(self):
        import_champions_tournament({
            "regulation": CURRENT_REGULATION,
            "players": [{
                "team": ["Whimsicott", "Farigiraf"],
                "placing": 9,
                "wins": 3,
                "losses": 1,
            }],
        })

        metrics = calculate_tournament_metrics("Whimsicott")

        self.assertEqual(metrics["win_rate"], 0.75)
        self.assertTrue(metrics["win_rate_available"])
        self.assertEqual(metrics["top_cut_rate"], 0.0)

    def test_wrong_regulation_is_ignored(self):
        import_champions_tournament({
            "regulation": "definitely-not-the-current-regulation",
            "players": [
                {"team": ["Whimsicott"], "placing": 1, "wins": 9}
            ],
        })

        self.assertEqual(CHAMPIONS_META_DB, {})

    def test_partners_are_counted_without_self_pairs(self):
        import_champions_tournament({
            "regulation": CURRENT_REGULATION,
            "players": [{
                "team": ["Whimsicott", "Farigiraf", "Whimsicott"],
                "placing": 4,
            }],
        })

        record = CHAMPIONS_META_DB["whimsicott"]

        self.assertNotIn("whimsicott", record["partners"])
        self.assertEqual(record["partners"]["farigiraf"], 1)

        partners = get_tournament_partners("Whimsicott")
        self.assertEqual(partners[0], ("farigiraf", 1))


if __name__ == "__main__":
    unittest.main()
