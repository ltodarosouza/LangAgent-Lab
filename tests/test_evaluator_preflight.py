import json
import sys
import tempfile
import unittest
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "generator"))

from settings import ensure_evaluator_ready  # noqa: E402


class EvaluatorPreflightTest(unittest.TestCase):
    def test_missing_calibration_fails_before_generation(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with self.assertRaisesRegex(RuntimeError, "bootstrap"):
                ensure_evaluator_ready(root / "missing.json", root / "python", root)

    def test_complete_evaluator_passes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            history = root / "dsr-v1.json"
            python = root / "python"
            entrypoint = root / "frameworks" / "texture_evaluator" / "evaluate_one.py"
            entrypoint.parent.mkdir(parents=True)
            history.write_text(json.dumps({"calibration": {"scale": 1}, "originals": {"case": "hash"}}))
            python.write_text("")
            entrypoint.write_text("")
            ensure_evaluator_ready(history, python, root)


if __name__ == "__main__":
    unittest.main()
