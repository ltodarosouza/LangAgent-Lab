import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


SPEC = importlib.util.spec_from_file_location("trava_agente", Path(__file__).resolve().parents[1] / "tools" / "trava_agente.py")
trava = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(trava)

CANDIDATE = {"steps": 25, "noise_level": 200, "sampler": "ddim", "scale_factor": 1.0, "seed": 42}
QUICK = ".venv/bin/python generator/run_batch.py --scope quick --config workspace/candidate.json --output-dir runs/real/{name}"
FULL = QUICK.replace("quick", "full", 1) + " --reuse-report runs/real/{quick}/report.json"


class TravaTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        base = Path(self.tmp.name).resolve()
        self.root = base / "lung-agent-lab"
        self.evaluator = base / "synthetic-lung-ct-evaluation"
        (self.root / "workspace").mkdir(parents=True)
        self.evaluator.mkdir()
        self.write_candidate(CANDIDATE)
        self.guard = trava.Guard(self.root, self.evaluator, max_configurations=2)

    def tearDown(self):
        self.tmp.cleanup()

    def write_candidate(self, candidate):
        (self.root / "workspace" / "candidate.json").write_text(json.dumps(candidate), encoding="utf-8")

    def write_quick(self, name, candidate, verdict=None):
        folder = self.root / "runs" / "real" / name
        folder.mkdir(parents=True)
        report = {"scope": "quick", "completed": True, "candidate": candidate}
        if verdict:
            report["comparison"] = {"verdict": verdict}
        (folder / "report.json").write_text(json.dumps(report), encoding="utf-8")

    def bash(self, command):
        return self.guard.check("Bash", {"command": command}, str(self.root))

    def test_writes_only_candidate_and_runs(self):
        allowed = [self.root / "workspace" / "candidate.json", self.root / "runs" / "notas.md"]
        blocked = [self.root / "agent" / "score.py", self.root / "configs" / "real_search_space.json",
                   self.root / "workspace" / "outro.json", self.root / "runs", self.evaluator / "frameworks" / "decision.py",
                   self.root / "runs" / ".." / "AGENTS.md"]
        for path in allowed:
            self.assertIsNone(self.guard.check("Write", {"file_path": str(path)}), path)
        for path in blocked:
            self.assertIsNotNone(self.guard.check("Edit", {"file_path": str(path)}), path)

    def test_evaluator_is_unreadable_through_tools_and_bash(self):
        self.assertIsNotNone(self.guard.check("Read", {"file_path": str(self.evaluator / "resultados" / "resumo.md")}))
        self.assertIsNotNone(self.guard.check("Grep", {"pattern": "AEKL", "path": str(self.root.parent)}))
        self.assertIsNotNone(self.bash("cat ../synthetic-lung-ct-evaluation/README.md"))
        self.assertIsNone(self.guard.check("Read", {"file_path": str(self.root / "runs" / "x" / "report.json")}))

    def test_python_only_through_approved_commands(self):
        self.assertIsNotNone(self.bash("python3 -c 'open(\"agent/score.py\", \"w\")'"))
        self.assertIsNotNone(self.bash(".venv/bin/python generator/generate_one.py x.tiff"))
        self.assertIsNotNone(self.bash("bash -c 'echo oi'"))
        self.assertIsNotNone(self.bash("runs/script.sh"))
        self.assertIsNotNone(self.bash(QUICK.format(name="a") + " && rm x"))
        self.assertIsNone(self.bash(".venv/bin/python -m agent.run_experiment --backend mock --config workspace/candidate.json"))
        self.assertIsNone(self.bash(".venv/bin/python -m unittest discover -s tests -v"))
        self.assertIsNone(self.bash("jq .summary runs/real/a/report.json"))

    def test_budget_counts_distinct_configurations(self):
        self.assertIsNone(self.bash(QUICK.format(name="baseline-quick") + " 2>&1 | tail -n 20"))
        self.assertIsNone(self.bash(QUICK.format(name="baseline-quick")))  # retomar não gasta
        self.write_candidate({**CANDIDATE, "steps": 50})
        self.assertIsNone(self.bash(QUICK.format(name="candidate-01-quick")))
        self.write_candidate({**CANDIDATE, "steps": 75})
        self.assertIn("orçamento esgotado", self.bash(QUICK.format(name="candidate-02-quick")))
        self.assertIsNotNone(self.bash(QUICK.format(name="../fora")))

    def test_full_scope_needs_a_better_quick_report(self):
        self.write_quick("baseline-quick", CANDIDATE)
        self.assertIsNone(self.bash(FULL.format(name="baseline-full", quick="baseline-quick")))
        self.write_candidate({**CANDIDATE, "steps": 50})
        self.write_quick("c1-quick", {**CANDIDATE, "steps": 50}, verdict="pior")
        self.assertIn("'pior'", self.bash(FULL.format(name="c1-full", quick="c1-quick")))
        self.write_candidate({**CANDIDATE, "steps": 60})
        self.write_quick("c2-quick", {**CANDIDATE, "steps": 60}, verdict="melhor")
        self.assertIsNone(self.bash(FULL.format(name="c2-full", quick="c2-quick")))
        self.assertIsNotNone(self.bash(QUICK.replace("quick", "full", 1).format(name="sem-reuso")))

    def test_settings_lock_sandbox_and_fail_closed(self):
        settings = self.guard.settings()
        self.assertFalse(settings["sandbox"]["allowUnsandboxedCommands"])
        self.assertIn(str(self.root / "agent"), settings["sandbox"]["filesystem"]["denyWrite"])
        self.assertIn(f"Edit(/{self.root}/models/**)", settings["permissions"]["deny"])
        hook = settings["hooks"]["PreToolUse"][0]["hooks"][0]
        self.assertEqual(hook["onFailure"], "block")
        self.assertIn("--max 2", hook["command"])


if __name__ == "__main__":
    unittest.main()
