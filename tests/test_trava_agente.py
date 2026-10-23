import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


SPEC = importlib.util.spec_from_file_location("trava_agente", Path(__file__).resolve().parents[1] / "tools" / "trava_agente.py")
trava = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(trava)

CANDIDATE = {"steps": 25, "noise_level": 1, "sampler": "ddim", "scale_factor": 1.0, "seed": 42,
             "eta": 0.0, "latent_noise_scale": 1.0, "conditioning_noise_scale": 1.0}
SCREEN = ".venv/bin/python generator/run_batch.py --scope screen --config workspace/candidate.json --output-dir runs/real/{name}"
QUICK = (".venv/bin/python generator/run_batch.py --scope quick --config workspace/candidate.json "
         "--output-dir runs/real/{name} --reuse-report runs/real/{screen}/report.json")
FULL = (".venv/bin/python generator/run_batch.py --scope full --config workspace/candidate.json "
        "--output-dir runs/real/{name} --reuse-report runs/real/{quick}/report.json")


class TravaTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        base = Path(self.tmp.name).resolve()
        self.root = base / "lung-agent-lab"
        self.evaluator = base / "synthetic-lung-ct-evaluation"
        (self.root / "workspace").mkdir(parents=True)
        self.evaluator.mkdir()
        self.write_candidate(CANDIDATE)
        self.guard = trava.Guard(self.root, self.evaluator, max_configurations=3)

    def tearDown(self):
        self.tmp.cleanup()

    def write_candidate(self, candidate):
        (self.root / "workspace" / "candidate.json").write_text(json.dumps(candidate), encoding="utf-8")

    def write_stage(self, name, scope, candidate, verdict=None, baseline=None, reference=None):
        path = self.root / "runs" / "real" / name / "report.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        report = {"scope": scope, "completed": True, "candidate": candidate}
        if verdict:
            baseline = baseline or f"baseline-{scope}"
            report["comparison"] = {
                "verdict": verdict,
                "baseline": str(self.root / "runs" / "real" / baseline / "report.json"),
                "reference": str(reference) if reference else None,
            }
        path.write_text(json.dumps(report), encoding="utf-8")
        return path

    def write_state(self, best):
        baseline = {}
        current = {"candidate": best}
        for scope in ("screen", "quick", "full"):
            baseline[scope] = str(self.write_stage(f"baseline-{scope}", scope, CANDIDATE).relative_to(self.root))
            current[scope] = str(self.write_stage(f"best-{scope}", scope, best, "melhor").relative_to(self.root))
        state = {"baseline": baseline, "current_best": current}
        (self.root / "workspace" / "search_state.json").write_text(json.dumps(state), encoding="utf-8")

    def bash(self, command):
        return self.guard.check("Bash", {"command": command}, str(self.root))

    def test_writes_only_candidate_and_runs(self):
        self.assertIsNone(self.guard.check("Write", {"file_path": str(self.root / "workspace" / "candidate.json")}))
        self.assertIsNone(self.guard.check("Write", {"file_path": str(self.root / "runs" / "note.md")}))
        self.assertIsNotNone(self.guard.check("Edit", {"file_path": str(self.root / "agent" / "score.py")}))
        self.assertIsNotNone(self.guard.check("Edit", {"file_path": str(self.evaluator / "decision.py")}))

    def test_notebook_only_grows(self):
        notebook = self.root / "CADERNO.md"
        notebook.write_text("# Caderno\n", encoding="utf-8")
        self.assertIsNone(self.guard.check("Write", {"file_path": str(notebook), "content": "# Caderno\n\n## 001\n"}))
        self.assertIsNotNone(self.guard.check("Write", {"file_path": str(notebook), "content": "apagado"}))

    def test_evaluator_is_unreadable(self):
        self.assertIsNotNone(self.guard.check("Read", {"file_path": str(self.evaluator / "resultados" / "x.md")}))
        self.assertIsNotNone(self.bash("cat ../synthetic-lung-ct-evaluation/README.md"))

    def test_python_only_through_approved_commands(self):
        self.assertIsNotNone(self.bash("python3 -c 'print(1)'"))
        self.assertIsNotNone(self.bash(SCREEN.format(name="a") + " && rm x"))
        self.assertIsNone(self.bash(".venv/bin/python -m unittest discover -s tests -v"))
        self.assertIsNone(self.bash("jq .summary runs/real/a/report.json"))

    def test_budget_counts_at_screen_stage(self):
        self.guard = trava.Guard(self.root, self.evaluator, max_configurations=2)
        self.assertIsNone(self.bash(SCREEN.format(name="baseline-screen")))
        self.write_candidate({**CANDIDATE, "steps": 40})
        self.assertIsNone(self.bash(SCREEN.format(name="c1-screen")))
        self.write_candidate({**CANDIDATE, "steps": 50})
        self.assertIn("orçamento esgotado", self.bash(SCREEN.format(name="c2-screen")))

    def test_funnel_requires_better_previous_stage(self):
        self.write_stage("baseline-screen", "screen", CANDIDATE)
        self.assertIsNone(self.bash(QUICK.format(name="baseline-quick", screen="baseline-screen")))
        self.write_stage("baseline-quick", "quick", CANDIDATE)
        self.assertIsNone(self.bash(FULL.format(name="baseline-full", quick="baseline-quick")))
        candidate = {**CANDIDATE, "eta": 0.2}
        self.write_candidate(candidate)
        self.write_stage("c1-screen", "screen", candidate, "pior")
        self.assertIn("'pior'", self.bash(QUICK.format(name="c1-quick", screen="c1-screen")))
        self.write_stage("c2-screen", "screen", candidate, "melhor")
        self.assertIsNone(self.bash(QUICK.format(name="c2-quick", screen="c2-screen")))
        self.write_stage("c2-quick", "quick", candidate, "pior")
        self.assertIn("'pior'", self.bash(FULL.format(name="c2-full", quick="c2-quick")))

    def test_continuation_uses_fixed_baselines_and_current_best(self):
        best = {**CANDIDATE, "steps": 35}
        self.write_state(best)
        candidate = {**best, "conditioning_noise_scale": 1.1}
        self.write_candidate(candidate)
        screen = SCREEN.format(name="next-screen") + " --baseline runs/real/baseline-screen/report.json"
        self.assertIsNone(self.bash(screen))
        self.write_stage("next-screen", "screen", candidate, "melhor")
        quick = (QUICK.format(name="next-quick", screen="next-screen")
                 + " --baseline runs/real/baseline-quick/report.json")
        self.assertIsNone(self.bash(quick))
        self.write_stage("next-quick", "quick", candidate, "melhor")
        full = (FULL.format(name="next-full", quick="next-quick")
                + " --baseline runs/real/baseline-full/report.json"
                + " --compare-to runs/real/best-full/report.json")
        self.assertIsNone(self.bash(full))
        wrong = SCREEN.format(name="wrong") + " --baseline runs/real/best-screen/report.json"
        self.assertIn("régua fixa", self.bash(wrong))

    def test_settings_lock_sandbox(self):
        settings = self.guard.settings()
        self.assertFalse(settings["sandbox"]["allowUnsandboxedCommands"])
        self.assertIn(str(self.root / "workspace" / "search_state.json"), settings["sandbox"]["filesystem"]["denyWrite"])
        self.assertEqual(settings["hooks"]["PreToolUse"][0]["hooks"][0]["onFailure"], "block")


if __name__ == "__main__":
    unittest.main()
