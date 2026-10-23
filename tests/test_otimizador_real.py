import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

HAS_DEPS = all(importlib.util.find_spec(name) for name in ("scipy", "optuna"))


class SpaceTest(unittest.TestCase):
    def setUp(self):
        import otimizador_real as runner

        self.runner = runner
        self.space = runner.Space(json.loads(runner.SPACE_PATH.read_text(encoding="utf-8")))
        self.baseline = json.loads(runner.BASELINE_PATH.read_text(encoding="utf-8"))

    def test_free_dimensions_and_frozen_values(self):
        self.assertEqual(
            self.space.free,
            ["steps", "noise_level", "eta", "latent_noise_scale", "conditioning_noise_scale"],
        )
        self.assertEqual(self.space.frozen, {"sampler": "ddim", "scale_factor": 1.0, "seed": 42})

    def test_baseline_round_trip(self):
        self.assertEqual(self.space.decode(self.space.encode(self.baseline)), self.baseline)

    def test_corners_stay_inside_the_space(self):
        low = self.space.decode([0.0] * 5)
        high = self.space.decode([1.0] * 5)
        self.assertEqual((low["steps"], low["noise_level"]), (10, 0))
        self.assertEqual((high["steps"], high["noise_level"]), (100, 349))


@unittest.skipUnless(HAS_DEPS, "scipy e optuna são opcionais")
class FunnelSimulatedTest(unittest.TestCase):
    def run_method(self, method, budget, out=None, crash_after=None):
        import otimizador_real as runner

        if out is None:
            tmp = tempfile.TemporaryDirectory()
            self.addCleanup(tmp.cleanup)
            out = Path(tmp.name)
        rules = json.loads(runner.SPACE_PATH.read_text(encoding="utf-8"))
        space = runner.Space(rules)
        baseline = json.loads(runner.BASELINE_PATH.read_text(encoding="utf-8"))
        backend = runner.SimulatedBackend(out, baseline)
        header = {"backend": "simulado", "budget": budget, "seed": 0}
        funnel = runner.Funnel(backend, space, baseline, out, runner.METHOD_PREFIX[method], budget, method, header)
        funnel.crash_after = crash_after
        try:
            runner.METHODS[method](funnel, space, baseline, 0, "podar")
        except SystemExit:
            pass
        rows = [json.loads(line) for line in funnel.log_path.read_text(encoding="utf-8").splitlines()]
        return funnel, rows

    def stage_trace(self, rows):
        return [(row["config_index"], row["scope"], json.dumps(row["candidate"], sort_keys=True))
                for row in rows if row["event"] == "etapa"]

    def check_budget_and_log(self, funnel, rows, budget):
        self.assertLessEqual(funnel.used, budget)
        stages = [row for row in rows if row["event"] == "etapa"]
        self.assertEqual(sum(row["cases_generated"] for row in stages), funnel.used)
        for row in stages:
            self.assertIn(row["scope"], ("screen", "quick", "full"))
            self.assertEqual(row["cases_generated"], {"screen": 5, "quick": 5, "full": 27}[row["scope"]])
        # Só um lote completo `melhor` muda a melhor atual.
        for row in stages:
            if row["new_best"]:
                self.assertEqual((row["scope"], row["verdict"]), ("full", "melhor"))

    def test_nelder_mead_respects_budget(self):
        funnel, rows = self.run_method("nm", 80)
        self.check_budget_and_log(funnel, rows, 80)

    def test_nelder_mead_resumes_exactly_after_a_crash(self):
        _, uninterrupted = self.run_method("nm", 120)
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            self.run_method("nm", 120, out=out, crash_after=4)
            funnel, resumed = self.run_method("nm", 120, out=out)
        self.assertEqual(self.stage_trace(resumed), self.stage_trace(uninterrupted))
        self.assertEqual(funnel.used, uninterrupted[-1]["cases_cumulative"])
        self.assertFalse(any(row["event"] == "divergencia" for row in resumed))

    def test_gp_resumes_within_budget_after_a_crash(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            _, first = self.run_method("gp", 80, out=out, crash_after=5)
            funnel, resumed = self.run_method("gp", 80, out=out)
        self.assertEqual(self.stage_trace(resumed)[: len(self.stage_trace(first))], self.stage_trace(first))
        self.check_budget_and_log(funnel, resumed, 80)

    def test_gp_respects_budget(self):
        funnel, rows = self.run_method("gp", 80)
        self.check_budget_and_log(funnel, rows, 80)


if __name__ == "__main__":
    unittest.main()
