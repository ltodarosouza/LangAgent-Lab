import sys
import unittest
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "generator"))

from reporting import DISTANCE_METRICS, case_score, compare_reports, enrich_measurements, summarize  # noqa: E402


def evaluation(case_id: str, fine: float = 100.0, final: str = "aprovada") -> dict:
    return {
        "verdicts": {
            "final": final,
            "pair_status": "ok",
            "brightness": "aprovada",
            "texture": "aprovada",
        },
        "measurements": {
            "case_id": case_id,
            "wavelet_fine_pct": fine,
            "wavelet_coarse_pct": 100.0,
            "glcm_contrast_pct": 100.0,
            "glcm_energy_real": 0.5,
            "glcm_energy_synthetic": 0.5,
            "wavelet_ratio": 1.0,
            "delta_mu": 0.0,
            "wavelet_ll_real": 0.4,
            "wavelet_ll_synthetic": 0.4,
            "density_status": "ok",
            "nex_status": "ok",
            "pair_correlation": 0.99,
        },
    }


def batch(distance: float, overrides: dict | None = None, final: str = "aprovada", pair: str = "ok",
          cases: tuple = ("case-1", "case-2")) -> dict:
    records = []
    for case_id in cases:
        item = evaluation(case_id, final=final)
        item["verdicts"]["pair_status"] = pair
        item["measurements"].update({key: distance for key in DISTANCE_METRICS}, **(overrides or {}))
        records.append({"case_id": case_id, "evaluation": item})
    return {"cases": records, "summary": summarize(records)}


class RealReportingTest(unittest.TestCase):
    def test_perfect_case_scores_100(self):
        self.assertEqual(case_score(evaluation("case-1")), 100.0)

    def test_summary_keeps_all_numeric_measurements(self):
        records = [{"evaluation": evaluation("case-1")}, {"evaluation": evaluation("case-2", 80.0)}]
        result = summarize(records)
        self.assertEqual(result["case_count"], 2)
        self.assertEqual(result["numeric_statistics"]["wavelet_fine_pct"]["median"], 90.0)
        self.assertEqual(enrich_measurements(records[0]["evaluation"]["measurements"])["glcm_energy_pct"], 100.0)

    def test_promotes_only_with_15_percent_mean_improvement(self):
        baseline = batch(1.0)
        self.assertEqual(compare_reports(batch(0.8), baseline)["verdict"], "melhor")
        result = compare_reports(batch(0.9), baseline)
        self.assertEqual(result["verdict"], "insuficiente")
        self.assertAlmostEqual(result["mean_improvement_pct"], 10.0)

    def test_overshooting_the_original_counts_as_distance(self):
        self.assertEqual(compare_reports(batch(-1.0), batch(1.0))["mean_improvement_pct"], 0.0)

    def test_single_metric_is_capped(self):
        current = batch(1.0, overrides={"nex_delta": 0.0})
        result = compare_reports(current, batch(1.0))
        self.assertEqual(result["metric_improvement_pct"]["nex_delta"], 50.0)
        self.assertEqual(result["verdict"], "insuficiente")

    def test_full_batch_must_beat_current_best(self):
        baseline = batch(1.0)
        self.assertEqual(compare_reports(batch(0.75), baseline, best=batch(0.7))["verdict"], "insuficiente")
        self.assertEqual(compare_reports(batch(0.6), baseline, best=batch(0.7))["verdict"], "melhor")

    def test_validity_blocks_promotion(self):
        self.assertEqual(compare_reports(batch(0.5, final="rejeitar"), batch(1.0))["verdict"], "pior")
        self.assertEqual(compare_reports(batch(0.5, pair="suspeito"), batch(1.0))["verdict"], "pior")

    def test_requires_the_same_cases(self):
        with self.assertRaises(ValueError):
            compare_reports(batch(0.8, cases=("case-1", "case-3")), batch(1.0))

if __name__ == "__main__":
    unittest.main()
