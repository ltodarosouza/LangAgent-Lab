import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


SPEC = importlib.util.spec_from_file_location(
    "select_starting_point", Path(__file__).resolve().parents[1] / "tools" / "select_starting_point.py"
)
module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(module)


class StartingPointTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = (Path(self.tmp.name) / "lab").resolve()
        (self.root / "workspace").mkdir(parents=True)
        (self.root / "runs" / "real").mkdir(parents=True)
        (self.root / ".agente").mkdir()
        self.old_values = (module.ROOT, module.RUNS, module.STATE, module.CANDIDATE, module.LEDGER,
                           module.DEFAULT_BASELINE_QUICK, module.DEFAULT_BASELINE_FULL)
        module.ROOT = self.root
        module.RUNS = self.root / "runs" / "real"
        module.STATE = self.root / "workspace" / "search_state.json"
        module.CANDIDATE = self.root / "workspace" / "candidate.json"
        module.LEDGER = self.root / ".agente" / "orcamento.jsonl"
        module.DEFAULT_BASELINE_QUICK = module.RUNS / "baseline-quick" / "report.json"
        module.DEFAULT_BASELINE_FULL = module.RUNS / "baseline-full" / "report.json"

    def tearDown(self):
        (module.ROOT, module.RUNS, module.STATE, module.CANDIDATE, module.LEDGER,
         module.DEFAULT_BASELINE_QUICK, module.DEFAULT_BASELINE_FULL) = self.old_values
        self.tmp.cleanup()

    def report(self, name, scope, candidate, cases):
        path = module.RUNS / name / "report.json"
        path.parent.mkdir()
        payload = {"scope": scope, "completed": True, "candidate": candidate,
                   "cases": [{"case_id": case} for case in cases]}
        path.write_text(json.dumps(payload), encoding="utf-8")
        return path

    def test_selects_best_and_archives_previous_budget(self):
        baseline = {"steps": 25}
        best = {"steps": 35}
        bq = self.report("baseline-quick", "quick", baseline, ["a", "b"])
        bf = self.report("baseline-full", "full", baseline, ["a", "b", "c"])
        self.report("candidate-01-quick", "quick", best, ["a", "b"])
        full = self.report("candidate-01-full", "full", best, ["a", "b", "c"])
        module.LEDGER.write_text("old\n", encoding="utf-8")

        state = module.select_starting_point(full.parent, bq, bf)

        self.assertEqual(json.loads(module.CANDIDATE.read_text()), best)
        self.assertEqual(state["current_best"]["full"], "runs/real/candidate-01-full/report.json")
        self.assertTrue(module.STATE.is_file())
        self.assertFalse(module.LEDGER.exists())
        self.assertEqual(len(list((module.LEDGER.parent / "historico").glob("*.jsonl"))), 1)

    def test_rejects_different_cases(self):
        baseline = {"steps": 25}
        best = {"steps": 35}
        bq = self.report("baseline-quick", "quick", baseline, ["a"])
        bf = self.report("baseline-full", "full", baseline, ["a", "b"])
        self.report("candidate-01-quick", "quick", best, ["x"])
        full = self.report("candidate-01-full", "full", best, ["a", "b"])
        with self.assertRaisesRegex(ValueError, "mesmos casos"):
            module.select_starting_point(full, bq, bf)


if __name__ == "__main__":
    unittest.main()
