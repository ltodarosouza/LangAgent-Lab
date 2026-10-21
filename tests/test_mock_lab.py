import unittest

from agent.config import ROOT, load_json, validate_candidate
from agent.mock_backend import run_mock
from agent.score import score_cases


class MockLabTest(unittest.TestCase):
    def test_baseline_is_deterministic_and_valid(self):
        candidate = validate_candidate(load_json(ROOT / "configs" / "baseline.json"))
        first = run_mock(candidate)
        second = run_mock(candidate)
        self.assertEqual(first, second)
        summary = score_cases(first)
        self.assertTrue(summary["valid"])
        self.assertEqual(summary["case_count"], 5)
        self.assertGreater(summary["score"], 0)
        self.assertLessEqual(summary["score"], 100)

    def test_candidate_outside_search_space_is_rejected(self):
        candidate = load_json(ROOT / "configs" / "baseline.json")
        candidate["steps"] = 999
        with self.assertRaises(ValueError):
            validate_candidate(candidate)

    def test_candidate_with_wrong_type_is_rejected(self):
        candidate = load_json(ROOT / "configs" / "baseline.json")
        candidate["steps"] = "25"
        with self.assertRaises(ValueError):
            validate_candidate(candidate)


if __name__ == "__main__":
    unittest.main()
