import unittest

from champions.team_analyzer import TeamAnalyzer, build_team_analyzer_input


class TeamAnalyzerTests(unittest.TestCase):
    def test_defensive_and_offensive_coverage_are_team_wide(self):
        team = [
            {
                "name": "Rotom Wash",
                "types": ["Electric", "Water"],
                "stats": {"attack": 65, "special-attack": 105, "speed": 86},
                "moves": ["Hydro Pump", "Thunderbolt", "Protect", "Volt Switch"],
                "abilities": ["Levitate"],
            },
            {
                "name": "Garchomp",
                "types": ["Dragon", "Ground"],
                "stats": {"attack": 130, "special-attack": 80, "speed": 102},
                "moves": ["Earthquake", "Dragon Claw", "Protect", "Swords Dance"],
                "abilities": ["Rough Skin"],
            },
            {
                "name": "Ferrothorn",
                "types": ["Grass", "Steel"],
                "stats": {"attack": 94, "special-attack": 54, "speed": 20},
                "moves": ["Gyro Ball", "Leech Seed", "Protect", "Spikes"],
                "abilities": ["Iron Barbs"],
            },
        ]
        result = TeamAnalyzer(team).analyze()
        self.assertEqual(result["team_size"], 3)
        self.assertIn("Water", result["defensive"]["covered_types"])
        self.assertIn("Ground", result["defensive"]["covered_types"])
        self.assertIn("Fire", result["offensive"]["covered_types"])
        self.assertGreater(result["overall_score"], 0)

    def test_speed_control_and_priority_are_detected(self):
        team = [
            {
                "name": "Whimsicott",
                "types": ["Grass", "Fairy"],
                "stats": {"attack": 67, "special-attack": 77, "speed": 116},
                "moves": ["Tailwind", "Encore", "Moonblast", "Helping Hand"],
                "abilities": ["Prankster"],
            },
            {
                "name": "Dragonite",
                "types": ["Dragon", "Flying"],
                "stats": {"attack": 134, "special-attack": 100, "speed": 80},
                "moves": ["Extreme Speed", "Dragon Claw", "Protect", "Dragon Dance"],
                "abilities": ["Multiscale"],
            },
        ]
        result = TeamAnalyzer(team).analyze()
        self.assertIn("Tailwind", result["functions"]["speed_control"])
        self.assertIn("extreme speed", result["functions"]["priority_moves"])
        self.assertIn("Encore", result["functions"]["disruption"])
        self.assertGreaterEqual(result["functions"]["signals"]["speed_control"], 75)

    def test_redundancy_detects_repeated_type(self):
        team = [
            {"name": "A", "types": ["Water"], "moves": ["Surf"], "abilities": [], "stats": {}},
            {"name": "B", "types": ["Water"], "moves": ["Hydro Pump"], "abilities": [], "stats": {}},
            {"name": "C", "types": ["Water"], "moves": ["Muddy Water"], "abilities": [], "stats": {}},
        ]
        result = TeamAnalyzer(team).analyze()
        self.assertEqual(result["redundancy"]["duplicate_types"]["Water"], 3)
        self.assertLess(result["redundancy"]["score"], 100)

    def test_build_team_analyzer_input_uses_slot_state(self):
        slots = [
            (0, {"name": "Whimsicott", "moves": ["Tailwind"], "ability": "Prankster", "item": "Focus Sash"}),
        ]
        details = {
            "Whimsicott": {
                "types": ["Grass", "Fairy"],
                "stats": {"speed": 116},
                "abilities": ["Prankster"],
            }
        }
        team = build_team_analyzer_input(slots, details)
        self.assertEqual(team[0]["name"], "Whimsicott")
        self.assertEqual(team[0]["types"], ["Grass", "Fairy"])
        self.assertEqual(team[0]["moves"], ["Tailwind"])


if __name__ == "__main__":
    unittest.main()
