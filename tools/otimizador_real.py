"""Otimizadores clássicos no funil real 5 → 10 → 37, para comparar com o agente.

Experimento separado, autorizado só no branch `claude/otimizador-real`: aqui um script,
e não o agente, propõe as configurações e escreve `workspace/candidate.json` (o arquivo
original é restaurado no fim). Avaliador, `agent/score.py`, `configs/`, checkpoints e
baseline fixo não são tocados.

Métodos, com o mesmo orçamento em casos gerados:
- `gp`: GP-BO com restrições (Optuna `GPSampler` + `constraints_func`).
- `nm`: Nelder-Mead determinístico (scipy, com bounds e simplex inicial fixo).

Subcomandos:
    otimizar   roda um método (backend `simulado` por padrão; `real` exige --confirmo-gpu)
    orcamento  conta os casos gerados pela busca M4–M12 a partir de runs/real
    agente     converte os relatórios M4–M12 para o mesmo formato de log
    curva      junta logs numa curva melhor melhora (37 casos) × casos gerados

Veja OTIMIZADOR_REAL.md para as decisões de desenho e como rodar no real.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import subprocess
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "generator", ROOT / "tools"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from agent.config import load_json, validate_candidate  # noqa: E402
from reporting import load_report  # noqa: E402

SPACE_PATH = ROOT / "configs" / "real_search_space.json"
BASELINE_PATH = ROOT / "configs" / "baseline.json"
CANDIDATE_PATH = ROOT / "workspace" / "candidate.json"
SCOPES = ("screen", "quick", "full")
SCOPE_SIZE = {"screen": 5, "quick": 10, "full": 37}
# Busca M do agente no CADERNO = candidate-04 … candidate-12 em runs/real.
AGENT_CANDIDATES = range(4, 13)
DEFAULT_BUDGET = 269  # ver `orcamento`: 7 × (5 + 5 + 27) + 2 × 5


class BudgetExhausted(Exception):
    pass


# --- espaço -------------------------------------------------------------------


class Space:
    """Cubo unitário [0, 1]^5 sobre os cinco parâmetros livres de real_search_space.json.

    `noise_level` usa escala log1p (0 → 0, 349 → 1), porque o intervalo inteiro é
    0–349 e um passo linear de 10% pularia 35 níveis. Os demais são lineares. `steps` e
    `noise_level` são arredondados para inteiro; os contínuos, para 3 casas.
    `sampler`, `scale_factor` e `seed` ficam congelados (uma opção só no espaço).
    """

    LOG1P = {"noise_level"}

    def __init__(self, rules: dict):
        self.rules = rules
        self.frozen = {name: rule["choices"][0] for name, rule in rules.items()
                       if "choices" in rule and len(rule["choices"]) == 1}
        self.free = [name for name in rules if name not in self.frozen]

    def _bounds(self, name):
        low, high = float(self.rules[name]["min"]), float(self.rules[name]["max"])
        if name in self.LOG1P:
            return math.log1p(low), math.log1p(high)
        return low, high

    def decode(self, u) -> dict:
        candidate = dict(self.frozen)
        for name, value in zip(self.free, u):
            low, high = self._bounds(name)
            raw = low + min(max(float(value), 0.0), 1.0) * (high - low)
            if name in self.LOG1P:
                raw = math.expm1(raw)
            if self.rules[name]["type"] == "integer":
                raw = int(round(raw))
                raw = min(max(raw, self.rules[name]["min"]), self.rules[name]["max"])
            else:
                raw = round(raw, 3)
            candidate[name] = raw
        return validate_candidate({name: candidate[name] for name in self.rules}, self.rules)

    def encode(self, candidate: dict) -> list:
        u = []
        for name in self.free:
            low, high = self._bounds(name)
            value = float(candidate[name])
            if name in self.LOG1P:
                value = math.log1p(value)
            u.append((value - low) / (high - low))
        return u


def key_of(candidate: dict) -> str:
    return json.dumps(candidate, sort_keys=True)


# --- backends -----------------------------------------------------------------


class SimulatedBackend:
    name = "simulado"

    def __init__(self, out_dir: Path, baseline: dict):
        import otimizador_simulado

        self.module = otimizador_simulado
        self.baseline_paths = otimizador_simulado.ensure_baselines(out_dir / "_baseline", baseline)

    def run_stage(self, candidate, scope, run_dir, reuse, baseline_report, compare_to) -> dict:
        return self.module.run_stage(candidate, scope, run_dir, reuse, baseline_report, compare_to)


class RealBackend:
    """Chama generator/run_batch.py exatamente como o AGENT_PROMPT.md manda o agente chamar."""

    name = "real"

    def __init__(self, python: Path, baseline_dir: Path, dry_run: bool = False):
        self.python = python
        self.dry_run = dry_run
        self.baseline_paths = {scope: baseline_dir / f"baseline-{scope}" / "report.json" for scope in SCOPES}
        missing = [str(path) for path in self.baseline_paths.values() if not path.exists()]
        if missing:
            raise SystemExit(f"relatórios de baseline ausentes (não são regenerados): {missing}")

    def run_stage(self, candidate, scope, run_dir, reuse, baseline_report, compare_to) -> dict:
        command = [
            str(self.python), str(ROOT / "generator" / "run_batch.py"),
            "--scope", scope, "--config", str(CANDIDATE_PATH),
            "--baseline", str(baseline_report), "--compare-to", str(compare_to),
            "--output-dir", str(run_dir),
        ]
        if reuse is not None:
            command += ["--reuse-report", str(reuse)]
        print("$", " ".join(f'"{part}"' if " " in part else part for part in command), flush=True)
        if self.dry_run:
            print("candidate.json seria:", json.dumps(candidate, ensure_ascii=False))
            raise SystemExit("dry-run: nada foi gerado nem escrito")
        CANDIDATE_PATH.write_text(json.dumps(candidate, indent=2) + "\n", encoding="utf-8")
        subprocess.run(command, check=True, cwd=ROOT)
        return load_report(run_dir / "report.json")


# --- funil --------------------------------------------------------------------


def report_facts(report: dict) -> dict:
    summary = report["summary"]
    rejected = int(summary["final_counts"].get("rejeitar", 0))
    pair_issues = int(summary["case_count"]) - int(summary["pair_counts"].get("ok", 0))
    generated = sum("reused_from" not in case for case in report["cases"])
    return {"rejected": rejected, "pair_issues": pair_issues, "generated": generated}


class Funnel:
    """Funil 5 → 10 → 37 com a regra `melhor`, orçamento em casos gerados e log JSONL.

    Cada etapa só começa se os casos novos dela cabem no orçamento restante; se não
    cabem, a configuração fica no último escopo concluído e o método termina.
    """

    def __init__(self, backend, space: Space, baseline: dict, out_dir: Path, budget: int, method: str):
        self.backend = backend
        self.space = space
        self.out_dir = out_dir
        self.budget = budget
        self.method = method
        self.used = 0
        self.index = 0
        self.cache = {}
        self.baseline_paths = backend.baseline_paths
        self.best = {"candidate": baseline, "paths": dict(self.baseline_paths), "improvement": 0.0}
        self.log_path = out_dir / "log.jsonl"
        out_dir.mkdir(parents=True, exist_ok=True)
        if self.log_path.exists():
            raise SystemExit(f"{self.log_path} já existe; use outra --tag (nada é sobrescrito)")
        # O baseline é a régua fixa: entra como ponto conhecido, sem custo.
        self.cache[key_of(baseline)] = {
            "candidate": baseline, "scope": "full", "value": 0.0, "full": True,
            "feasible": True, "rejected": 0, "pair_issues": 0, "verdict": "baseline",
        }
        self._log({"event": "baseline", "candidate": baseline, "scope": "full", "cases_generated": 0,
                   "mean_improvement_pct": 0.0, "verdict": "baseline"})

    def _log(self, row: dict) -> None:
        row = {"method": self.method, "config_index": self.index, "cases_cumulative": self.used,
               "best_full_improvement_pct": self.best["improvement"], **row}
        with self.log_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")

    def evaluate(self, candidate: dict) -> dict:
        key = key_of(candidate)
        if key in self.cache:
            result = self.cache[key]
            self._log({"event": "cache", "candidate": candidate, "scope": result["scope"],
                       "cases_generated": 0, "mean_improvement_pct": result["value"],
                       "verdict": result["verdict"]})
            return result
        if self.used + SCOPE_SIZE["screen"] > self.budget:
            raise BudgetExhausted
        self.index += 1
        previous = None
        result = None
        for scope in SCOPES:
            new_cases = SCOPE_SIZE[scope] - (SCOPE_SIZE[SCOPES[SCOPES.index(scope) - 1]] if previous else 0)
            if self.used + new_cases > self.budget:
                self.cache[key] = result
                self._log({"event": "orcamento_esgotado", "candidate": candidate, "scope": result["scope"],
                           "cases_generated": 0, "mean_improvement_pct": result["value"],
                           "verdict": "parada por orçamento"})
                raise BudgetExhausted
            run_dir = self.out_dir / f"c{self.index:02d}-{scope}"
            report = self.backend.run_stage(candidate, scope, run_dir, previous,
                                            self.baseline_paths[scope], self.best["paths"][scope])
            facts = report_facts(report)
            self.used += facts["generated"]
            comparison = report["comparison"]
            result = {
                "candidate": candidate, "scope": scope, "value": comparison["mean_improvement_pct"],
                "full": scope == "full", "feasible": facts["rejected"] == 0 and facts["pair_issues"] == 0,
                "rejected": facts["rejected"], "pair_issues": facts["pair_issues"],
                "verdict": comparison["verdict"],
            }
            promoted = scope == "full" and comparison["verdict"] == "melhor"
            if promoted:
                self.best = {
                    "candidate": candidate,
                    "paths": {s: self.out_dir / f"c{self.index:02d}-{s}" / "report.json" for s in SCOPES},
                    "improvement": comparison["mean_improvement_pct"],
                }
            self._log({
                "event": "etapa", "candidate": candidate, "scope": scope,
                "cases_generated": facts["generated"],
                "mean_improvement_pct": comparison["mean_improvement_pct"],
                "metric_improvement_pct": comparison["metric_improvement_pct"],
                "verdict": comparison["verdict"], "reason": comparison["reason"],
                "case_wins": comparison["case_distance_wins"], "case_losses": comparison["case_distance_losses"],
                "rejected": facts["rejected"], "pair_issues": facts["pair_issues"],
                "new_best": promoted, "report": str(run_dir / "report.json"),
            })
            if comparison["verdict"] != "melhor":
                break
            previous = run_dir / "report.json"
        self.cache[key] = result
        return result


# --- métodos ------------------------------------------------------------------

N_SOBOL_INITIAL = 4
NM_INITIAL_STEP = 0.10
MAX_PROPOSALS = 400


def sobol_points(dim: int, seed: int, count: int):
    from scipy.stats import qmc

    sampler = qmc.Sobol(d=dim, scramble=True, seed=seed)
    return sampler.random(count).tolist()


def run_gp(funnel: Funnel, space: Space, baseline: dict, seed: int, stopped_mode: str) -> dict:
    """GP-BO com restrições.

    Pontos iniciais: baseline (custo 0) + 4 pontos Sobol (semente fixa). Depois, o
    GPSampler propõe. Restrições: rejeições ≤ 0 e pares fora de ok ≤ 0, via
    `constraints_func` (modelo de viabilidade separado, não penalidade no objetivo).

    `stopped_mode` decide o que o GP vê de uma configuração parada em 5 ou 10 casos:
    - `podar` (padrão): nada; o trial é PRUNED e só resultados de 37 alimentam o GP.
    - `escopo`: a melhora no escopo em que parou, como no Nelder-Mead.
    Se o GP repropõe uma configuração já medida, o resultado conhecido é repetido (sem
    custo) e a próxima proposta vem da sequência Sobol, para não girar em falso.
    """
    import optuna

    optuna.logging.set_verbosity(optuna.logging.WARNING)
    sampler = optuna.samplers.GPSampler(
        seed=seed, n_startup_trials=1,
        constraints_func=lambda trial: trial.user_attrs["constraints"],
    )
    study = optuna.create_study(direction="maximize", sampler=sampler)
    names = [f"u_{name}" for name in space.free]
    sobol = sobol_points(len(names), seed, 64)
    initial = [space.encode(baseline)] + sobol[:N_SOBOL_INITIAL]
    fallback = iter(sobol[N_SOBOL_INITIAL:])
    for u in initial:
        study.enqueue_trial(dict(zip(names, u)))
    stats = {"proposals": 0, "repeated": 0, "sobol_fallback": 0}

    while stats["proposals"] < MAX_PROPOSALS:
        trial = study.ask()
        stats["proposals"] += 1
        candidate = space.decode([trial.suggest_float(name, 0.0, 1.0) for name in names])
        repeated = key_of(candidate) in funnel.cache and stats["proposals"] > 1
        try:
            result = funnel.evaluate(candidate)
        except BudgetExhausted:
            study.tell(trial, state=optuna.trial.TrialState.FAIL)
            break
        trial.set_user_attr("constraints", [float(result["rejected"]), float(result["pair_issues"])])
        trial.set_user_attr("scope", result["scope"])
        if result["full"] or stopped_mode == "escopo":
            study.tell(trial, result["value"])
        else:
            study.tell(trial, state=optuna.trial.TrialState.PRUNED)
        if repeated:
            stats["repeated"] += 1
            point = next(fallback, None)
            if point is not None:
                stats["sobol_fallback"] += 1
                study.enqueue_trial(dict(zip(names, point)))
    return stats


def run_nm(funnel: Funnel, space: Space, baseline: dict, seed: int, stopped_mode: str) -> dict:
    """Nelder-Mead determinístico partindo do baseline.

    Simplex inicial fixo: baseline + um vértice por parâmetro, deslocado +10% da faixa no
    cubo (−10% se passar do limite). Regra neutra, igual para todos os parâmetros.
    Valor de cada ponto: melhora média contra o baseline no escopo em que parou (5, 10
    ou 37). Ponto parado ficou, por construção, abaixo da melhor atual naquele escopo.
    Ponto inviável (rejeição ou par fora de ok) vale +inf na minimização: barreira, não
    penalidade graduada. Sem reinício: se convergir antes, o orçamento restante sobra.
    """
    import numpy as np
    from scipy.optimize import minimize

    x0 = space.encode(baseline)
    simplex = [x0]
    for i in range(len(x0)):
        vertex = list(x0)
        vertex[i] = vertex[i] + NM_INITIAL_STEP if vertex[i] + NM_INITIAL_STEP <= 1.0 else vertex[i] - NM_INITIAL_STEP
        simplex.append(vertex)
    stats = {"calls": 0, "converged": False}

    def objective(u):
        stats["calls"] += 1
        if stats["calls"] > MAX_PROPOSALS:
            raise BudgetExhausted
        result = funnel.evaluate(space.decode(u))
        return math.inf if not result["feasible"] else -result["value"]

    try:
        outcome = minimize(objective, np.array(x0), method="Nelder-Mead", bounds=[(0.0, 1.0)] * len(x0),
                           options={"initial_simplex": np.array(simplex), "maxfev": MAX_PROPOSALS,
                                    "xatol": 1e-3, "fatol": 1e-3})
        stats["converged"] = bool(outcome.success)
        stats["message"] = str(outcome.message)
    except BudgetExhausted:
        stats["message"] = "orçamento esgotado"
    return stats


METHODS = {"gp": run_gp, "nm": run_nm}


# --- subcomandos --------------------------------------------------------------


def git_branch() -> str:
    try:
        return subprocess.run(["git", "branch", "--show-current"], cwd=ROOT, capture_output=True,
                              text=True, check=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return ""


def cmd_otimizar(args) -> None:
    rules = load_json(SPACE_PATH)
    space = Space(rules)
    baseline = validate_candidate(load_json(BASELINE_PATH), rules)
    tag = args.tag or datetime.now().strftime("%Y%m%d-%H%M%S")
    if args.backend == "real":
        if not args.confirmo_gpu and not args.dry_run:
            raise SystemExit("backend real gera imagens na GPU: só rode com --confirmo-gpu, após autorização humana")
        if git_branch() in ("main", "master"):
            raise SystemExit("a exceção ao protocolo vale só no branch do experimento, não no main")
        out_dir = args.out or ROOT / "runs" / "real" / f"otim-{args.method}-{tag}"
        if args.dry_run:
            out_dir = ROOT / "runs" / "otimizador-dry-run" / f"{args.method}-{tag}"
        backend = RealBackend(args.python, args.baseline_dir.resolve(), args.dry_run)
    else:
        out_dir = args.out or ROOT / "runs" / "otimizador-simulado" / f"{args.method}-{tag}"
        backend = SimulatedBackend(out_dir, baseline)
    funnel = Funnel(backend, space, baseline, out_dir, args.budget, args.method)
    original_candidate = CANDIDATE_PATH.read_text(encoding="utf-8") if CANDIDATE_PATH.exists() else None
    try:
        stats = METHODS[args.method](funnel, space, baseline, args.seed, args.gp_parados)
    finally:
        if original_candidate is not None and args.backend == "real":
            CANDIDATE_PATH.write_text(original_candidate, encoding="utf-8")
    summary = {
        "method": args.method, "backend": backend.name, "budget": args.budget, "cases_used": funnel.used,
        "configs_measured": funnel.index, "best": funnel.best["candidate"],
        "best_full_improvement_pct": funnel.best["improvement"],
        "best_reports": {scope: str(path) for scope, path in funnel.best["paths"].items()},
        "seed": args.seed, "gp_parados": args.gp_parados if args.method == "gp" else None,
        "nm_initial_step": NM_INITIAL_STEP if args.method == "nm" else None,
        "stats": stats,
    }
    (out_dir / "resumo.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    print(f"Log: {funnel.log_path}")


def agent_reports(runs_real: Path):
    for number in AGENT_CANDIDATES:
        for scope in SCOPES:
            path = runs_real / f"candidate-{number:02d}-{scope}" / "report.json"
            if path.exists():
                yield number, scope, path


def cmd_orcamento(args) -> None:
    total = 0
    print(f"{'config':<14} {'escopo':<7} {'gerados':>8} {'reusados':>9}  veredito")
    for number, scope, path in agent_reports(args.runs_real):
        report = load_report(path)
        facts = report_facts(report)
        total += facts["generated"]
        reused = len(report["cases"]) - facts["generated"]
        print(f"candidate-{number:02d}  {scope:<7} {facts['generated']:>8} {reused:>9}  "
              f"{report.get('comparison', {}).get('verdict')}")
    print(f"Total de casos gerados pela busca M4–M12: {total}")


def cmd_agente(args) -> None:
    best = 0.0
    used = 0
    rows = [{"method": "agente", "event": "baseline", "config_index": 0, "cases_cumulative": 0,
             "cases_generated": 0, "scope": "full", "mean_improvement_pct": 0.0,
             "best_full_improvement_pct": 0.0, "verdict": "baseline"}]
    for number, scope, path in agent_reports(args.runs_real):
        report = load_report(path)
        facts = report_facts(report)
        comparison = report["comparison"]
        used += facts["generated"]
        promoted = scope == "full" and comparison["verdict"] == "melhor"
        if promoted:
            best = comparison["mean_improvement_pct"]
        rows.append({
            "method": "agente", "event": "etapa", "config_index": number, "cases_cumulative": used,
            "best_full_improvement_pct": best, "candidate": report["candidate"], "scope": scope,
            "cases_generated": facts["generated"], "mean_improvement_pct": comparison["mean_improvement_pct"],
            "metric_improvement_pct": comparison["metric_improvement_pct"], "verdict": comparison["verdict"],
            "reason": comparison["reason"], "case_wins": comparison.get("case_distance_wins"),
            "case_losses": comparison.get("case_distance_losses"), "rejected": facts["rejected"],
            "pair_issues": facts["pair_issues"], "new_best": promoted, "report": str(path),
        })
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows), encoding="utf-8")
    print(f"{len(rows) - 1} etapas, {used} casos gerados, melhor em 37 casos: {best:+.2f}%  → {args.out}")


def cmd_curva(args) -> None:
    curves = {}
    for path in args.logs:
        for line in path.read_text(encoding="utf-8").splitlines():
            row = json.loads(line)
            label = f"{row['method']}:{path.parent.name}"
            points = curves.setdefault(label, [])
            point = (row["cases_cumulative"], row["best_full_improvement_pct"])
            if not points or points[-1] != point:
                points.append(point)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["curva", "casos_gerados", "melhor_melhora_37_pct"])
        for label, points in curves.items():
            writer.writerows([label, cases, value] for cases, value in points)
    for label, points in curves.items():
        print(f"{label}: {' → '.join(f'{c}:{v:+.2f}%' for c, v in points)}")
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        fig, ax = plt.subplots(figsize=(8, 5))
        for label, points in curves.items():
            xs, ys = zip(*points)
            ax.step(xs, ys, where="post", marker="o", label=label)
        ax.set_xlabel("casos gerados")
        ax.set_ylabel("melhor melhora média em 37 casos (%)")
        ax.grid(alpha=0.3)
        ax.legend()
        fig.tight_layout()
        fig.savefig(args.out.with_suffix(".png"), dpi=120)
    except ImportError:
        pass
    print(f"Curva: {args.out}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = parser.add_subparsers(dest="command", required=True)

    opt = sub.add_parser("otimizar")
    opt.add_argument("--method", choices=sorted(METHODS), required=True)
    opt.add_argument("--backend", choices=("simulado", "real"), default="simulado")
    opt.add_argument("--confirmo-gpu", action="store_true", help="obrigatório para --backend real")
    opt.add_argument("--dry-run", action="store_true",
                     help="com --backend real: mostra o primeiro comando de geração e para, sem gerar nada")
    opt.add_argument("--budget", type=int, default=DEFAULT_BUDGET, help="casos gerados (não configurações)")
    opt.add_argument("--seed", type=int, default=0, help="semente do otimizador (Sobol e GP), não da geração")
    opt.add_argument("--gp-parados", choices=("podar", "escopo"), default="podar")
    opt.add_argument("--tag")
    opt.add_argument("--out", type=Path)
    opt.add_argument("--python", type=Path, default=ROOT / ".venv" / "bin" / "python")
    opt.add_argument("--baseline-dir", type=Path, default=ROOT / "runs" / "real")
    opt.set_defaults(func=cmd_otimizar)

    budget = sub.add_parser("orcamento")
    budget.add_argument("--runs-real", type=Path, default=ROOT / "runs" / "real")
    budget.set_defaults(func=cmd_orcamento)

    agent = sub.add_parser("agente")
    agent.add_argument("--runs-real", type=Path, default=ROOT / "runs" / "real")
    agent.add_argument("--out", type=Path, default=ROOT / "runs" / "otimizador-curvas" / "agente" / "log.jsonl")
    agent.set_defaults(func=cmd_agente)

    curve = sub.add_parser("curva")
    curve.add_argument("logs", type=Path, nargs="+")
    curve.add_argument("--out", type=Path, default=ROOT / "runs" / "otimizador-curvas" / "curva.csv")
    curve.set_defaults(func=cmd_curva)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
