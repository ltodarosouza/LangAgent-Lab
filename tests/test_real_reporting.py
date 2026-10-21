import sys
import unittest
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "generator"))

from reporting import case_score, compare_summaries, enrich_measurements, summarize  # noqa: E402


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


class RealReportingTest(unittest.TestCase):
    def test_perfect_case_scores_100(self):
        self.assertEqual(case_score(evaluation("case-1")), 100.0)

    def test_summary_keeps_all_numeric_measurements(self):
        records = [{"evaluation": evaluation("case-1")}, {"evaluation": evaluation("case-2", 80.0)}]
        result = summarize(records)
        self.assertEqual(result["case_count"], 2)
        self.assertEqual(result["numeric_statistics"]["wavelet_fine_pct"]["median"], 90.0)
        self.assertEqual(enrich_measurements(records[0]["evaluation"]["measurements"])["glcm_energy_pct"], 100.0)

    def test_comparison_rejects_regression(self):
        reference = {"score": 80.0, "final_counts": {"rejeitar": 0}}
        current = {"score": 90.0, "final_counts": {"rejeitar": 1}}
        self.assertEqual(compare_summaries(current, reference)["verdict"], "pior")


if __name__ == "__main__":
    unittest.main()
