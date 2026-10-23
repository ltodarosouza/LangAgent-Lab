import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from prepare_dsr_dataset import CALIBRATION, prepare  # noqa: E402


class PrepareDsrDatasetTest(unittest.TestCase):
    def test_screen_is_a_fixed_five_case_subset_of_quick(self):
        screen = json.loads((ROOT / "configs" / "screen_cases.json").read_text(encoding="utf-8"))["cases"]
        quick = json.loads((ROOT / "configs" / "quick_cases.json").read_text(encoding="utf-8"))["cases"]
        self.assertEqual(len(screen), 5)
        self.assertEqual(len(set(screen)), 5)
        self.assertTrue(set(screen).issubset(quick))

    def test_cases_come_from_calibration_originals(self):
        with tempfile.TemporaryDirectory() as tmp:
            evaluator, target = Path(tmp) / "evaluator", Path(tmp) / "target"
            (evaluator / "dados" / "Dsr").mkdir(parents=True)
            (evaluator / "dados" / "Dgen").mkdir(parents=True)
            for case_id in ("b", "a", "rejected"):
                (evaluator / "dados" / "Dsr" / f"{case_id}.tiff").write_bytes(b"x")
                (evaluator / "dados" / "Dgen" / f"{case_id}_mask.tiff").write_bytes(b"x")
            (evaluator / CALIBRATION).parent.mkdir(parents=True)
            (evaluator / CALIBRATION).write_text(
                json.dumps({"calibration": {}, "originals": {"b": "hash-b", "a": "hash-a"}}), encoding="utf-8"
            )

            manifest = prepare(evaluator, target)

            self.assertEqual([case["case_id"] for case in manifest["cases"]], ["a", "b"])
            self.assertEqual(manifest["cases"][0]["pixel_sha1"], "hash-a")
            self.assertFalse((evaluator / "outputs").exists())
            self.assertTrue((target / "originals" / "a.tiff").is_symlink())
            self.assertFalse((target / "originals" / "rejected.tiff").exists())


if __name__ == "__main__":
    unittest.main()
